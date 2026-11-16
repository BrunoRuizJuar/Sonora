"""Transform every lyric in the selected common space, streaming per shard.

No fitting or selection here. Test may be transformed but is never evaluated.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import numpy as np

from sonora.nlp.semantics import (
    ParquetStreamWriter, config_hash, pool, require_same, signature, tfidf,
)
from sonora.nlp.semantic_models import bow, load_model, load_vocab, stable_hash
from sonora.storage.runs import file_sha256, write_json_atomic


def export(cache: Path, models: Path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from gensim.models import Word2Vec, LdaModel

    selected = json.loads((models / 'trained.json').read_text(encoding='utf-8'))
    word_model = Path(selected['sgns']['path'])
    topic_model = Path(selected['lda']['path'])
    model = load_model(word_model)
    lda = load_model(topic_model)
    vocab = load_vocab(cache)
    lookup = {r['word']: (r['index'], r['idf']) for r in vocab}
    ids = {w: v[0] for w, v in lookup.items()}
    vectors = np.array([model.wv[r['word']] for r in vocab], dtype=np.float32)
    out = cache / 'representations'
    spec = {'sgns': signature(word_model), 'lda': signature(topic_model),
            'vocabulary': signature(cache / 'baseline/vocabulary.parquet'),
            'code': file_sha256(Path(__file__)), 'pooling': 'distinct terms weighted by sublinear TF-IDF, then L2',
            'oov': 'omit unknown words; zero weight/norm => embedding unavailable',
            'empty_bow': 'topic vector unavailable (zeros); never substitute the prior',
            'test': 'transform only; no evaluation or model selection'}
    require_same(out / 'config.json', spec)
    schema = pa.schema([
        ('lyrics_id', pa.string()), ('split', pa.string()), ('tag', pa.string()),
        ('year', pa.int64()), ('title', pa.string()), ('artist', pa.string()),
        ('tfidf_indices', pa.list_(pa.int32())), ('tfidf_weights', pa.list_(pa.float32())),
        ('embedding', pa.list_(pa.float32(), vectors.shape[1])),
        ('topics', pa.list_(pa.float32(), lda.num_topics)),
        ('embedding_available', pa.bool_()), ('topics_available', pa.bool_()),
        ('n_words', pa.int32()), ('n_covered', pa.int32()),
    ])
    summaries = []
    for source in sorted((cache / 'documents').glob('*.parquet')):
        target = out / source.name
        marker = out / (source.stem + '.json')
        if marker.exists():
            done = json.loads(marker.read_text(encoding='utf-8'))
            if signature(target) != done['output']:
                raise RuntimeError('Corrupt representation checkpoint')
            summaries.append(done)
            continue
        writer = ParquetStreamWriter(target, schema)
        counts = Counter()
        try:
            for batch in pq.ParquetFile(source).iter_batches(batch_size=256):
                rows = []
                for row in batch.to_pylist():
                    terms = row.pop('words')
                    index, weight = tfidf(terms, lookup)
                    vector, available = pool(terms, lookup, vectors)
                    document = bow(terms, ids)
                    topics = np.zeros(lda.num_topics, dtype=np.float32)
                    if document:
                        # Identical inference after a resumed shard, independent
                        # of how many preceding shards were skipped.
                        lda.random_state = np.random.RandomState(stable_hash(row['lyrics_id']) % 2**32)
                        for k, p in lda.get_document_topics(document, minimum_probability=0.):
                            topics[k] = p
                    covered = sum(w in ids for w in terms)
                    rows.append(row | {'tfidf_indices': index.tolist(), 'tfidf_weights': weight.tolist(),
                                       'embedding': vector.tolist(), 'topics': topics.tolist(),
                                       'embedding_available': available, 'topics_available': bool(document),
                                       'n_words': len(terms), 'n_covered': covered})
                    counts['docs'] += 1
                    counts[f"docs_{row['split']}"] += 1
                    counts['embedding_unavailable'] += not available
                    counts['topics_unavailable'] += not document
                    counts['tokens'] += len(terms)
                    counts['covered_tokens'] += covered
                writer.write(pa.Table.from_pylist(rows, schema=schema))
            writer.close()
        except BaseException:
            writer.abort()
            raise
        done = {'source': source.name, 'counts': dict(counts), 'output': signature(target)}
        write_json_atomic(marker, done)
        summaries.append(done)
        print(f'exported {source.name}', flush=True)
    total = Counter()
    for item in summaries:
        total.update(item['counts'])
    expected = json.loads((cache / 'prepared.json').read_text(encoding='utf-8'))['docs']
    if any(total[f'docs_{s}'] != n for s, n in expected.items()):
        raise RuntimeError('Representation coverage differs from corpus split counts')
    write_json_atomic(out / 'complete.json', {'counts': dict(total), 'space_id': config_hash(spec),
                      'lyrics_id_policy': 'canonical lyrics; track mapping belongs to verified catalog'})
    return out
