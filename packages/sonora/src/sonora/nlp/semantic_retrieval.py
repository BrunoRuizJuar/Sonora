"""Exact TF-IDF baseline retrieval: validation queries, all train candidates.

Only batch-by-query score blocks are materialized. No test retrieval/evaluation.
"""
from collections import Counter
import heapq
import json
from pathlib import Path

import numpy as np

from sonora.nlp.semantic_models import load_vocab, validation_sample
from sonora.nlp.semantics import tfidf
from sonora.storage.runs import write_json_atomic


def retrieve_baseline(cache: Path, reports: Path, k=10, min_covered=20):
    import pyarrow.parquet as pq
    import pyarrow.compute as pc
    from scipy.sparse import csr_matrix

    vocab = load_vocab(cache)
    lookup = {r['word']: (r['index'], r['idf']) for r in vocab}
    queries = []
    tags = set()
    for row in validation_sample(cache):
        if row['tag'] not in tags and sum(w in lookup for w in row['words']) >= min_covered:
            queries.append(row)
            tags.add(row['tag'])
    if not queries:
        raise ValueError('No eligible validation seeds')

    def sparse(documents):
        indices, weights, indptr = [], [], [0]
        for terms in documents:
            index, weight = tfidf(terms, lookup)
            indices.extend(index)
            weights.extend(weight)
            indptr.append(len(indices))
        return csr_matrix((np.array(weights, dtype=np.float32), np.array(indices, dtype=np.int32),
                           np.array(indptr, dtype=np.int64)), shape=(len(documents), len(vocab)))

    qmatrix = sparse([r['words'] for r in queries])
    heaps = [[] for _ in queries]
    n_train = 0
    for source in sorted((cache / 'documents').glob('*.parquet')):
        for batch in pq.ParquetFile(source).iter_batches(batch_size=512):
            candidates = batch.filter(pc.equal(batch.column('split'), 'train')).to_pylist()
            if not candidates:
                continue
            scores = (sparse([r['words'] for r in candidates]) @ qmatrix.T).toarray()
            n_train += len(candidates)
            for qi, heap in enumerate(heaps):
                count = min(k, len(candidates))
                threshold = np.partition(scores[:, qi], -count)[-count]
                best = np.flatnonzero(scores[:, qi] >= threshold)
                for i in best:
                    score = float(scores[i, qi])
                    if score <= 0:
                        continue
                    row = candidates[i]
                    entry = (score, row['lyrics_id'], {key: row[key] for key in
                             ('lyrics_id', 'title', 'artist', 'tag', 'year')},
                             sorted(set(row['words']) & set(queries[qi]['words']) & lookup.keys()))
                    if len(heap) < k:
                        heapq.heappush(heap, entry)
                    elif entry[:2] > heap[0][:2]:
                        heapq.heapreplace(heap, entry)
        print(f'TF-IDF retrieval scanned {n_train} train lyrics', flush=True)
    expected = json.loads((cache / 'prepared.json').read_text(encoding='utf-8'))['docs']['train']
    if expected != n_train:
        raise RuntimeError('Train candidate count mismatch')
    result = []
    for query, heap in zip(queries, heaps):
        result.append({'query': {key: query[key] for key in ('lyrics_id', 'title', 'artist', 'tag', 'year')},
                       'neighbors': [meta | {'cosine': score, 'shared_terms': terms}
                                     for score, _, meta, terms in sorted(heap, reverse=True)]})
    write_json_atomic(reports / 'e5_tfidf_retrieval.json', {
        'queries': result, 'train_candidates': n_train, 'k': k,
        'selection': f'one seed per observed tag, first eligible in bottom-SHA256 validation sample; >={min_covered} covered tokens',
        'scope': 'exact full-train retrieval for a small qualitative set of validation queries',
        'metric': 'cosine over L2-normalized sublinear TF-IDF',
        'limits': 'unjudged neighbors; no accuracy/relevance claims; no test evaluation',
    })


def retrieve_embeddings(cache: Path, models: Path, reports: Path, k=10):
    """Compare SGNS neighbors for exactly the baseline seeds, all train candidates."""
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    from sonora.nlp.semantic_models import load_model
    from sonora.nlp.semantics import pool

    baseline = json.loads((reports / 'e5_tfidf_retrieval.json').read_text(encoding='utf-8'))
    selected = json.loads((models / 'trained.json').read_text(encoding='utf-8'))
    space = json.loads((cache / 'representations/complete.json').read_text(encoding='utf-8'))
    model = load_model(selected['sgns']['path'])
    vocab = load_vocab(cache)
    lookup = {r['word']: (r['index'], r['idf']) for r in vocab}
    vectors = np.array([model.wv[r['word']] for r in vocab], dtype=np.float32)
    sample = {r['lyrics_id']: r for r in validation_sample(cache)}
    query_vectors = []
    for entry in baseline['queries']:
        query = sample[entry['query']['lyrics_id']]
        vector, available = pool(query['words'], lookup, vectors)
        if not available:
            raise ValueError(f"Unavailable query embedding: {query['lyrics_id']}")
        query_vectors.append(vector)
    queries = np.array(query_vectors)
    heaps = [[] for _ in query_vectors]
    n_train = n_available = 0
    keys = ['lyrics_id', 'split', 'tag', 'year', 'title', 'artist']
    for source in sorted((cache / 'representations').glob('*.parquet')):
        for batch in pq.ParquetFile(source).iter_batches(batch_size=1024, columns=keys+['embedding', 'embedding_available']):
            batch = batch.filter(pc.equal(batch.column('split'), 'train'))
            n_train += batch.num_rows
            batch = batch.filter(batch.column('embedding_available'))
            if not batch.num_rows:
                continue
            n_available += batch.num_rows
            matrix = batch.column('embedding').flatten().to_numpy().reshape(batch.num_rows, -1)
            score_block = matrix @ queries.T
            meta = batch.select(keys).to_pylist()
            for qi, heap in enumerate(heaps):
                count = min(k, batch.num_rows)
                threshold = np.partition(score_block[:, qi], -count)[-count]
                for i in np.flatnonzero(score_block[:, qi] >= threshold):
                    entry = (float(score_block[i, qi]), meta[i]['lyrics_id'], meta[i])
                    if len(heap) < k:
                        heapq.heappush(heap, entry)
                    elif entry[:2] > heap[0][:2]:
                        heapq.heapreplace(heap, entry)
    if n_train != baseline['train_candidates']:
        raise RuntimeError('Candidate coverage differs from baseline')
    result = []
    for item, heap in zip(baseline['queries'], heaps):
        neighbors = [row | {'cosine': score} for score, _, row in sorted(heap, reverse=True)]
        lexical_ids = {r['lyrics_id'] for r in item['neighbors']}
        semantic_ids = {r['lyrics_id'] for r in neighbors}
        result.append({'query': item['query'], 'neighbors': neighbors,
                       'shared_neighbor_ids_with_tfidf': sorted(lexical_ids & semantic_ids)})
    write_json_atomic(reports / 'e5_embedding_retrieval.json', {
        'queries': result, 'train_candidates': n_train, 'available_candidates': n_available,
        'space_id': space['space_id'], 'k': k,
        'scope': 'same validation seeds as baseline; all available train embeddings',
        'limits': 'cosines and neighbor overlap describe rankings, not recommendation relevance',
    })
