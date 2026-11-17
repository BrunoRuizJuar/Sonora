"""Read-only, bounded-memory serving release of frozen E5 representations."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sqlite3
import time

import numpy as np
import pyarrow.parquet as pq
from scipy.sparse import csr_matrix

from sonora.nlp.semantics import config_hash, signature, tfidf, words


def build_release(source: Path, target: Path):
    """One writer; committed shards survive interruption, staging shards restart."""
    source, target = Path(source), Path(target)
    complete = json.loads((source / 'complete.json').read_text('utf-8'))
    spec = json.loads((source / 'config.json').read_text('utf-8'))
    if config_hash(spec) != complete['space_id']:
        raise ValueError('Incompatible E5 space')
    target.mkdir(parents=True, exist_ok=True)
    lock = target / '.writer.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, str(os.getpid()).encode())
        shards = []
        for path in sorted(source.glob('*.parquet')):
            fingerprint = signature(path)
            final = target / path.stem
            if final.exists():
                item = json.loads((final / 'manifest.json').read_text('utf-8'))
                if item['source'] != fingerprint or item['space_id'] != complete['space_id']:
                    raise ValueError('Existing shard belongs to another source/space')
                shards.append(item)
                continue
            stage = target / (path.stem + '.building')
            if stage.exists():
                shutil.rmtree(stage)
            stage.mkdir()
            db = sqlite3.connect(stage / 'catalog.sqlite')
            db.execute('CREATE TABLE tracks (rowid INTEGER PRIMARY KEY, lyrics_id TEXT UNIQUE, title TEXT, artist TEXT, split TEXT, tag TEXT, year INTEGER, available INTEGER)')
            db.execute("CREATE VIRTUAL TABLE search USING fts5(title,artist,tokenize='unicode61 remove_diacritics 2')")
            streams = {name: (stage / (name + '.bin')).open('wb') for name in ('vectors', 'indices', 'weights', 'indptr')}
            count, nnz, dim = 0, 0, None
            counts = {}
            np.array([0], dtype='<i8').tofile(streams['indptr'])
            try:
                for batch in pq.ParquetFile(path).iter_batches(batch_size=2048):
                    rows = batch.to_pylist()
                    vectors = np.asarray([r['embedding'] for r in rows], dtype='<f4')
                    dim = vectors.shape[1]
                    norms = np.linalg.norm(vectors, axis=1)
                    if not np.isfinite(vectors).all() or any(r['embedding_available'] and n == 0 for r, n in zip(rows, norms)):
                        raise ValueError('Invalid embedding')
                    vectors /= np.where(norms == 0, 1, norms)[:, None]
                    vectors.tofile(streams['vectors'])
                    metadata, search = [], []
                    for r in rows:
                        idx = np.asarray(r['tfidf_indices'], dtype='<i4')
                        weight = np.asarray(r['tfidf_weights'], dtype='<f4')
                        if len(idx) != len(weight) or not np.isfinite(weight).all():
                            raise ValueError('Invalid TF-IDF')
                        idx.tofile(streams['indices']); weight.tofile(streams['weights'])
                        nnz += len(idx)
                        np.array([nnz], dtype='<i8').tofile(streams['indptr'])
                        metadata.append((count, r['lyrics_id'], r['title'], r['artist'], r['split'], r['tag'], r['year'], int(r['embedding_available'])))
                        search.append((count, r['title'], r['artist']))
                        counts[r['split']] = counts.get(r['split'], 0) + 1
                        count += 1
                    db.executemany('INSERT INTO tracks VALUES (?,?,?,?,?,?,?,?)', metadata)
                    db.executemany('INSERT INTO search(rowid,title,artist) VALUES (?,?,?)', search)
                db.commit()
            finally:
                db.close()
                for stream in streams.values():
                    stream.close()
            item = dict(name=path.stem, source=fingerprint, space_id=complete['space_id'], rows=count, nnz=nnz, dimensions=dim, splits=counts)
            item['files'] = {p.name: signature(p) for p in stage.iterdir()}
            (stage / 'manifest.json').write_text(json.dumps(item), 'utf-8')
            stage.rename(final)
            shards.append(item)
            print(f'Ready {path.stem}: {count} lyrics', flush=True)
        if sum(s['rows'] for s in shards) != complete['counts']['docs']:
            raise ValueError('Incomplete corpus')
        for split in ('train', 'validation', 'test'):
            if sum(s['splits'].get(split, 0) for s in shards) != complete['counts']['docs_' + split]:
                raise ValueError('Incomplete split')
        vocabulary = source.parent / 'baseline/vocabulary.parquet'
        if signature(vocabulary) != spec['vocabulary']:
            raise ValueError('Vocabulary differs from E5 export')
        shutil.copyfile(vocabulary, target / 'vocabulary.parquet')
        from sonora.nlp.semantic_models import load_model
        model_path = Path(spec['sgns']['path'])
        if signature(model_path) != spec['sgns']:
            raise ValueError('Selected SGNS differs from E5 export')
        if (target / 'release.json').exists():
            previous = json.loads((target / 'release.json').read_text('utf-8'))
            if previous['space_id'] != complete['space_id'] or signature(target / 'word_vectors.npy') != previous['word_vectors']:
                raise ValueError('Existing word vectors differ; use a new target')
        else:
            model = load_model(model_path)
            vocab = sorted(pq.read_table(vocabulary).to_pylist(), key=lambda r: r['index'])
            vectors = np.asarray([model.wv[r['word']] for r in vocab], dtype=np.float32)
            with (target / 'word_vectors.tmp').open('wb') as stream:
                np.save(stream, vectors)
            (target / 'word_vectors.tmp').replace(target / 'word_vectors.npy')
        manifest = dict(version='lyrics-serving-v1', space_id=complete['space_id'], space_config=spec, rows=complete['counts']['docs'], dimensions=shards[0]['dimensions'], shards=shards, vocabulary=signature(vocabulary), sgns=spec['sgns'])
        manifest['word_vectors'] = signature(target / 'word_vectors.npy')
        manifest['release_id'] = config_hash(manifest)
        temp = target / 'release.tmp'
        temp.write_text(json.dumps(manifest, indent=2), 'utf-8')
        temp.replace(target / 'release.json')
        return manifest
    finally:
        os.close(fd)
        lock.unlink()


class Catalog:
    def __init__(self, root):
        self.root = Path(root)
        self.manifest = json.loads((self.root / 'release.json').read_text('utf-8'))
        self.shards = []
        self.word_vectors = None
        unsigned = {k: v for k, v in self.manifest.items() if k != 'release_id'}
        if config_hash(unsigned) != self.manifest['release_id'] or config_hash(self.manifest['space_config']) != self.manifest['space_id']:
            raise ValueError('Incompatible release/space identity')
        if sum(s['rows'] for s in self.manifest['shards']) != self.manifest['rows']:
            raise ValueError('Incomplete release coverage')
        if any(s['space_id'] != self.manifest['space_id'] or s['dimensions'] != self.manifest['dimensions'] for s in self.manifest['shards']):
            raise ValueError('Incompatible shard space')
        vocab_signature = signature(self.root / 'vocabulary.parquet')
        if any(vocab_signature[k] != self.manifest['vocabulary'][k] for k in ('bytes', 'sha256')):
            raise ValueError('Incompatible release vocabulary')
        vocab = pq.read_table(self.root / 'vocabulary.parquet').to_pylist()
        self.lookup = {r['word']: (r['index'], r['idf']) for r in vocab}
        self.terms = {r['index']: r['word'] for r in vocab}
        self.vocab_size = len(vocab)
        vector_signature = signature(self.root / 'word_vectors.npy')
        if any(vector_signature[k] != self.manifest['word_vectors'][k] for k in ('bytes', 'sha256')):
            raise ValueError('Incompatible word vectors')
        self.word_vectors = np.load(self.root / 'word_vectors.npy', mmap_mode='r')
        if self.word_vectors.shape != (self.vocab_size, self.manifest['dimensions']):
            raise ValueError('Incompatible word vector dimensions')
        try:
            for item in self.manifest['shards']:
                folder = self.root / item['name']
                if json.loads((folder / 'manifest.json').read_text('utf-8')) != item:
                    raise ValueError('Incompatible shard manifest')
                for name, sig in item['files'].items():
                    if (folder / name).stat().st_size != sig['bytes']:
                        raise ValueError('Incomplete release file: ' + name)
                db = sqlite3.connect((folder / 'catalog.sqlite').resolve().as_uri() + '?mode=ro', uri=True, check_same_thread=False)
                db.row_factory = sqlite3.Row
                self.shards.append(dict(db=db, rows=item['rows'], vectors=np.memmap(folder / 'vectors.bin', mode='r', dtype='<f4', shape=(item['rows'], item['dimensions'])), indices=np.memmap(folder / 'indices.bin', mode='r', dtype='<i4'), weights=np.memmap(folder / 'weights.bin', mode='r', dtype='<f4'), indptr=np.memmap(folder / 'indptr.bin', mode='r', dtype='<i8')))
        except BaseException:
            self.close()
            raise

    def close(self):
        for shard in self.shards:
            shard['db'].close()
            for name in ('vectors', 'indices', 'weights', 'indptr'):
                shard[name]._mmap.close()
        self.shards = []
        if self.word_vectors is not None:
            self.word_vectors._mmap.close()
            self.word_vectors = None

    def public(self, row):
        return {k: row[k] for k in ('lyrics_id', 'title', 'artist', 'split', 'tag', 'year')} | {'id': row['lyrics_id'], 'track_id': row['lyrics_id'], 'capabilities': {'lyrics': bool(row['available']), 'audio': False, 'mixed': False}}

    def locate(self, identifier):
        for shard in self.shards:
            row = shard['db'].execute('SELECT * FROM tracks WHERE lyrics_id=?', (identifier,)).fetchone()
            if row:
                return shard, row
        raise KeyError(identifier)

    def search(self, query, limit=20):
        tokens = words(query)
        if not tokens:
            return []
        match = ' AND '.join('"' + t.replace('"', '""') + '"*' for t in tokens[:20])
        found = []
        for shard in self.shards:
            found.extend(self.public(r) for r in shard['db'].execute('SELECT t.* FROM search JOIN tracks t ON t.rowid=search.rowid WHERE search MATCH ? ORDER BY search.rank LIMIT ?', (match, limit)))
        return sorted(found, key=lambda r: (r['title'].casefold(), r['artist'].casefold(), r['id']))[:limit]

    def query_text(self, text):
        tokens = words(text)
        idx, weight = tfidf(tokens, self.lookup)
        if not len(idx):
            raise ValueError('El texto no contiene vocabulario conocido del modelo inglés.')
        vector = weight @ self.word_vectors[idx]
        norm = np.linalg.norm(vector)
        if not norm or not np.isfinite(vector).all():
            raise ValueError('El texto no tiene un vector utilizable.')
        return vector / norm, idx, weight, {'tokens': len(tokens), 'covered_tokens': sum(t in self.lookup for t in tokens)}

    def recommend(self, *, identifier=None, text=None, strategy='sgns', top_k=10, splits=('train', 'validation', 'test'), max_per_artist=None):
        started = time.perf_counter()
        if not 1 <= top_k <= 50 or strategy not in ('sgns', 'tfidf') or not splits or not set(splits) <= {'train', 'validation', 'test'}:
            raise ValueError('Invalid retrieval parameters')
        if (identifier is None) == (text is None):
            raise ValueError('Specify exactly one input')
        if text is not None:
            if not text.strip() or len(text) > 10000:
                raise ValueError('Texto vacío o mayor a 10000 caracteres')
            vector, idx, weight, coverage = self.query_text(text)
            query = {'text': text, 'coverage': coverage}
        else:
            shard, row = self.locate(identifier)
            if not row['available']:
                raise ValueError('La semilla no tiene embedding disponible')
            i = row['rowid']; a, b = shard['indptr'][i:i+2]
            vector, idx, weight = shard['vectors'][i], shard['indices'][a:b], shard['weights'][a:b]
            query = self.public(row)
        lexical = np.zeros(self.vocab_size, dtype=np.float32)
        lexical[idx] = weight
        # Keep only K per artist globally: a discarded candidate already has K
        # better candidates from its artist and can never enter the final top K.
        best = []
        artist_best = {}
        for shard in self.shards:
            for start in range(0, shard['rows'], 32768):
                stop = min(start + 32768, shard['rows'])
                if strategy == 'sgns':
                    scores = shard['vectors'][start:stop] @ vector
                else:
                    a, b = shard['indptr'][start], shard['indptr'][stop]
                    matrix = csr_matrix((shard['weights'][a:b], shard['indices'][a:b], shard['indptr'][start:stop+1] - a), shape=(stop-start, self.vocab_size))
                    scores = matrix @ lexical
                eligible = np.flatnonzero(scores >= best[-1][0]) if len(best) >= top_k else np.arange(len(scores))
                order = eligible[np.argsort(-scores[eligible], kind='stable')]
                for offset in range(0, len(order), 128):
                    selected = order[offset:offset+128]
                    if len(best) >= top_k and float(scores[selected[0]]) < best[-1][0]:
                        break
                    positions = [int(i + start) for i in selected]
                    placeholders = ','.join('?' for _ in positions)
                    found = {r['rowid']: r for r in shard['db'].execute('SELECT * FROM tracks WHERE available=1 AND rowid IN (' + placeholders + ')', positions)}
                    for local in selected:
                        row = found.get(int(local + start))
                        if row is None:
                            continue
                        if row['split'] not in splits or row['lyrics_id'] == identifier:
                            continue
                        score = float(np.clip(scores[row['rowid'] - start], -1, 1))
                        if strategy == 'tfidf' and score <= 0:
                            continue
                        key = (score, row['lyrics_id'])
                        if len(best) >= top_k and key <= best[-1][:2]:
                            continue
                        item = (score, row['lyrics_id'], self.public(row), shard, row['rowid'])
                        if max_per_artist:
                            artist = row['artist'].casefold().strip() if row['artist'] else row['lyrics_id']
                            group = artist_best.get(artist, []) + [item]
                            group.sort(key=lambda x: x[:2], reverse=True)
                            artist_best[artist] = group[:max_per_artist]
                            # Only retain groups represented in the global top K.
                            best = sorted([x for g in artist_best.values() for x in g], key=lambda x: x[:2], reverse=True)[:top_k]
                            active = {x[1] for x in best}
                            artist_best = {a: [x for x in g if x[1] in active] for a, g in artist_best.items() if any(x[1] in active for x in g)}
                        else:
                            best = sorted(best + [item], key=lambda x: x[:2], reverse=True)[:top_k]
        items = []
        for score, _, meta, shard, i in best:
            a, b = shard['indptr'][i:i+2]
            shared = [(float(w * lexical[j]), self.terms[int(j)]) for j, w in zip(shard['indices'][a:b], shard['weights'][a:b]) if lexical[j] > 0]
            shared.sort(reverse=True)
            items.append(meta | {'score': score, 'shared_terms': [t for _, t in shared[:8]]})
        return dict(query=query, mode='lyrics', strategy=strategy, metric='cosine', space_id=self.manifest['space_id'], catalog_version=self.manifest['version'], release_id=self.manifest['release_id'], candidate_splits=list(splits), scope='exploratory catalog; no relevance evaluation or verified recording mapping', items=items, total_returned=len(items), elapsed_seconds=time.perf_counter()-started, warnings=['La afinidad no garantiza el mismo tema. No hay audio ni detección verificada de covers.'])
