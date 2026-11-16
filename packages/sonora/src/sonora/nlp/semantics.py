"""E5: streamed surface-word cache and train-only lexical baseline.

No spaCy inference, no corpus sampling, and no dense document similarity matrix.
The cache retains the original split and metadata; fitting never reads held-out words.
"""
from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import unicodedata

from sonora.nlp.lexicon import WORD
from sonora.storage.runs import (
    ParquetStreamWriter, config_hash, file_sha256, peak_rss_bytes,
    write_json_atomic, write_parquet_atomic,
)

VERSION = 'e5-surface-v2'


def words(text: str) -> list[str]:
    """Unicode letters/internal apostrophes; preserve negation and stopwords.

    Use the E1/E2 regex definition, NFC and typographic-apostrophe normalization.
    No lemma substitution, inferred g-dropping, stemming, or POS-based exclusion.
    """
    text = unicodedata.normalize('NFC', text).replace('\u2019', "'").lower()
    return WORD.findall(text)


def signature(path: Path) -> dict:
    return {'path': str(path.resolve()), 'bytes': path.stat().st_size,
            'sha256': file_sha256(path)}


def require_same(path: Path, expected: dict) -> None:
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8')) != expected:
            raise RuntimeError(f'Incompatible checkpoint: {path}; use a new run-id')
    else:
        write_json_atomic(path, expected)


def prepare(root: Path, run_id: str = VERSION) -> Path:
    """Cache ALL canonical lyrics, checkpointing each shard atomically.

    Memory: split ID lookup + one 512-document batch + one shard's train counters.
    Input and code SHA-256 prevent accidental reuse with changed data or policy.
    """
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    corpus = root / 'data/processed/lyrics/lyrics_full_v1/corpus'
    split_file = root / 'data/processed/splits/lyrics_full_v1/lyrics_splits.parquet'
    out = root / 'data/processed/nlp/lyrics_full_v1/semantics' / run_id
    files = sorted(corpus.glob('*.parquet'))
    if not files:
        raise FileNotFoundError(corpus)
    spec = {'version': VERSION, 'code_sha256': file_sha256(Path(__file__)),
            'inputs': [signature(p) for p in [split_file, *files]],
            'token_policy': 'NFC, curly apostrophe to ASCII, lower, E1 WORD regex; keep stopwords',
            'fit_split': 'train', 'test_policy': 'reserved; preparation only'}
    require_same(out / 'config.json', spec)
    splits = pq.read_table(split_file, columns=['lyrics_id', 'split'])
    ids = splits['lyrics_id'].combine_chunks()
    if len(pc.unique(ids)) != len(ids):
        raise ValueError('Duplicate split IDs')
    if set(splits['split'].to_pylist()) != {'train', 'test', 'validation'}:
        raise ValueError('Unexpected split names')
    schema = pa.schema([
        ('lyrics_id', pa.string()), ('split', pa.string()), ('tag', pa.string()),
        ('year', pa.int64()), ('title', pa.string()), ('artist', pa.string()),
        ('words', pa.list_(pa.string())),
    ])
    summaries = []
    for source in files:
        checkpoint = out / 'checkpoints' / (source.stem + '.json')
        target = out / 'documents' / source.name
        counts_path = out / 'counts' / source.name
        if checkpoint.exists():
            done = json.loads(checkpoint.read_text(encoding='utf-8'))
            if signature(target) != done['documents'] or signature(counts_path) != done['counts']:
                raise RuntimeError(f'Corrupt checkpoint {checkpoint}')
            summaries.append(done)
            print(f'reuse {source.name}', flush=True)
            continue
        tf, df = Counter(), Counter()
        docs, tokens = Counter(), Counter()
        # Align once per shard, not once per batch: Arrow rebuilds the entire
        # value_set hash table in every index_in call (3.15 million split IDs).
        source_ids = pq.read_table(source, columns=['lyrics_id'])['lyrics_id']
        pos = pc.index_in(source_ids, value_set=ids)
        if pc.any(pc.is_null(pos)).as_py():
            raise ValueError(f'Lyrics missing from split: {source}')
        source_splits = splits['split'].take(pos)
        offset = 0
        writer = ParquetStreamWriter(target, schema)
        try:
            for batch in pq.ParquetFile(source).iter_batches(batch_size=512, columns=[
                'lyrics_id', 'tag', 'year', 'title', 'artist', 'lyrics_analysis',
            ]):
                names = source_splits.slice(offset, batch.num_rows).to_pylist()
                offset += batch.num_rows
                rows = []
                for row, split in zip(batch.to_pylist(), names):
                    terms = words(row.pop('lyrics_analysis'))
                    docs[split] += 1
                    tokens[split] += len(terms)
                    if split == 'train':
                        tf.update(terms)
                        df.update(set(terms))
                    rows.append(row | {'split': split, 'words': terms})
                writer.write(pa.Table.from_pylist(rows, schema=schema))
            writer.close()
        except BaseException:
            writer.abort()
            raise
        terms = sorted(tf)
        write_parquet_atomic(pa.table({'word': terms, 'tf': [tf[w] for w in terms],
                                       'df': [df[w] for w in terms]}), counts_path)
        done = {'source': source.name, 'docs': dict(docs), 'tokens': dict(tokens),
                'documents': signature(target), 'counts': signature(counts_path)}
        write_json_atomic(checkpoint, done)
        summaries.append(done)
        print(f'prepared {source.name}: {dict(docs)}', flush=True)
    total_docs, total_tokens = Counter(), Counter()
    for done in summaries:
        total_docs.update(done['docs'])
        total_tokens.update(done['tokens'])
    if sum(total_docs.values()) != len(ids):
        raise ValueError('Corpus/split row count mismatch')
    # Validate full ID coverage independently of source order; duplicates are disallowed.
    seen = set()
    for p in sorted((out / 'documents').glob('*.parquet')):
        for b in pq.ParquetFile(p).iter_batches(columns=['lyrics_id']):
            for lid in b.column(0).to_pylist():
                if lid in seen:
                    raise ValueError(f'Duplicate corpus ID {lid}')
                seen.add(lid)
    if len(seen) != len(ids):
        raise ValueError('Corpus ID coverage mismatch')
    write_json_atomic(out / 'prepared.json', {'complete': True, 'docs': dict(total_docs),
                      'tokens': dict(total_tokens), 'shards': len(files),
                      'peak_rss_bytes': peak_rss_bytes(), 'config_hash': config_hash(spec)})
    return out


def fit_baseline(cache: Path, min_df: int = 5, max_features: int = 100_000) -> Path:
    """Smooth IDF=log((1+n_train)/(1+df))+1; sublinear TF=1+log(count)."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    prepared = json.loads((cache / 'prepared.json').read_text(encoding='utf-8'))
    spec = {'prepared_hash': config_hash(prepared), 'min_df': min_df,
            'max_features': max_features, 'max_df_fraction': 0.8,
            'tf': '1+ln(count)', 'idf': 'ln((1+n_train)/(1+df))+1',
            'normalize': 'l2', 'fit_split': 'train'}
    dest = cache / 'baseline'
    require_same(dest / 'config.json', spec)
    tf, df = Counter(), Counter()
    for path in sorted((cache / 'counts').glob('*.parquet')):
        for row in pq.read_table(path).to_pylist():
            tf[row['word']] += row['tf']
            df[row['word']] += row['df']
    n = prepared['docs']['train']
    terms = sorted((w for w in tf if min_df <= df[w] <= 0.8*n),
                   key=lambda w: (-tf[w], w))[:max_features]
    terms.sort()
    rows = [{'index': i, 'word': w, 'train_tf': tf[w], 'train_df': df[w],
             'idf': math.log((1+n)/(1+df[w]))+1} for i, w in enumerate(terms)]
    write_parquet_atomic(pa.Table.from_pylist(rows), dest / 'vocabulary.parquet')
    write_json_atomic(dest / 'fit.json', spec | {'train_docs': n, 'vocabulary': len(terms),
                      'vocabulary_sha256': file_sha256(dest / 'vocabulary.parquet')})
    return dest


class Documents:
    """Re-iterable stream with explicit split; no hidden fit on held-out documents."""
    def __init__(self, cache: Path, split: str):
        if split not in {'train', 'validation', 'test'}:
            raise ValueError(split)
        self.cache, self.split = cache, split

    def rows(self):
        import pyarrow.parquet as pq
        for p in sorted((self.cache / 'documents').glob('*.parquet')):
            for batch in pq.ParquetFile(p).iter_batches(batch_size=256):
                for row in batch.to_pylist():
                    if row['split'] == self.split:
                        yield row

    def __iter__(self):
        for row in self.rows():
            yield row['words']


def tfidf(terms, vocabulary):
    """Return distinct term IDs/weights, so pooling never multiplies TF twice."""
    import numpy as np
    pairs = [(vocabulary[w][0], (1+math.log(c))*vocabulary[w][1])
             for w, c in Counter(terms).items() if w in vocabulary]
    pairs.sort()
    idx = np.array([i for i, _ in pairs], dtype=np.int32)
    weight = np.array([v for _, v in pairs], dtype=np.float32)
    norm = np.linalg.norm(weight)
    if norm:
        weight /= norm
    return idx, weight


def pool(terms, vocabulary, vectors):
    import numpy as np
    idx, weights = tfidf(terms, vocabulary)
    vector = weights @ vectors[idx] if len(idx) else np.zeros(vectors.shape[1], dtype=np.float32)
    norm = np.linalg.norm(vector)
    return (vector / norm if norm else vector), bool(norm)
