"""Exact, streaming item-to-item recommendations in the frozen E5 space."""
import heapq
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from sonora.storage.runs import config_hash


def recommend_lyrics(representations, lyrics_id, k=10, candidate_splits=('train',)):
    """Return cosine neighbors; all-split browsing must be explicitly requested.

    This is a lyrics experiment, not an audio-verified playable catalog. No fitting,
    topic scoring, or relevance evaluation occurs here. Memory is bounded by batches.
    """
    root = Path(representations)
    if not 1 <= k <= 50:
        raise ValueError('k must be between 1 and 50')
    splits = tuple(candidate_splits)
    if not splits or not set(splits) <= {'train', 'validation', 'test'}:
        raise ValueError('Specify valid candidate splits')
    complete = json.loads((root / 'complete.json').read_text(encoding='utf-8'))
    spec = json.loads((root / 'config.json').read_text(encoding='utf-8'))
    if config_hash(spec) != complete['space_id']:
        raise ValueError('Representation space does not match completion manifest')
    files = sorted(root.glob('*.parquet'))
    keys = ['lyrics_id', 'split', 'title', 'artist', 'tag', 'year']
    columns = keys + ['embedding', 'embedding_available']
    query = None
    counts = {}
    for source in files:
        for batch in pq.ParquetFile(source).iter_batches(batch_size=4096, columns=columns):
            for split, count in zip(*np.unique(batch.column('split').to_numpy(zero_copy_only=False), return_counts=True)):
                counts[str(split)] = counts.get(str(split), 0) + int(count)
            found = batch.filter(pc.equal(batch.column('lyrics_id'), lyrics_id)).to_pylist()
            if found:
                if query is not None or len(found) != 1:
                    raise ValueError('Query ID is not unique')
                query = found[0]
    expected = {s: complete['counts'].get(f'docs_{s}', 0) for s in ('train', 'validation', 'test')}
    if any(counts.get(s, 0) != n for s, n in expected.items()):
        raise ValueError('Incomplete representation coverage')
    if query is None:
        raise ValueError(f'Unknown lyrics_id: {lyrics_id}')
    vector = np.asarray(query['embedding'], dtype=np.float32)
    if not query['embedding_available'] or not np.isfinite(vector).all() or np.linalg.norm(vector) == 0:
        raise ValueError('Query embedding is unavailable')
    vector = vector / np.linalg.norm(vector)
    heap = []
    scanned = 0
    for source in files:
        for batch in pq.ParquetFile(source).iter_batches(batch_size=4096, columns=columns):
            batch = batch.filter(pc.and_(pc.is_in(batch.column('split'), value_set=pa.array(splits)),
                                        pc.and_(batch.column('embedding_available'), pc.not_equal(batch.column('lyrics_id'), lyrics_id))))
            if not batch.num_rows:
                continue
            matrix = batch.column('embedding').flatten().to_numpy().reshape(batch.num_rows, len(vector))
            norms = np.linalg.norm(matrix, axis=1)
            if not np.isfinite(matrix).all() or np.any(norms == 0):
                raise ValueError('Invalid available candidate embedding')
            scores = (matrix @ vector) / norms
            scanned += batch.num_rows
            meta = batch.select(keys).to_pylist()
            # Stable tie policy: larger lyrics_id first, matching E5 retrieval.
            count = min(k, len(scores))
            threshold = np.partition(scores, -count)[-count]
            for i in np.flatnonzero(scores >= threshold):
                item = (float(np.clip(scores[i], -1, 1)), meta[i]['lyrics_id'], meta[i])
                if len(heap) < k:
                    heapq.heappush(heap, item)
                elif item[:2] > heap[0][:2]:
                    heapq.heapreplace(heap, item)
    return {'query': {key: query[key] for key in keys}, 'space_id': complete['space_id'],
            'candidate_splits': list(splits), 'available_candidates_excluding_query': scanned,
            'mode': 'lyrics', 'metric': 'embedding cosine',
            'scope': 'exploratory browsing; no relevance evaluation or verified audio availability',
            'neighbors': [meta | {'cosine': score} for score, _, meta in sorted(heap, reverse=True)]}
