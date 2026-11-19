"""Read-only audit of completed real E5 artifacts; writes a separate report."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path, PureWindowsPath
import sys

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/sonora/src'))
from sonora.storage.runs import config_hash, file_sha256, write_json_atomic, utc_now
from sonora.nlp.semantics import signature


def verify_signature(path, expected):
    assert path.name == PureWindowsPath(expected['path']).name, path
    actual = signature(path)
    assert actual == expected | {'path': actual['path']}, path


def main():
    cache = ROOT / 'data/processed/nlp/lyrics_full_v1/semantics/e5-surface-v2'
    models = ROOT / 'artifacts/models/lyrics_full_v1/e5-surface-v2'
    reports = ROOT / 'reports/nlp/lyrics_full_v1'
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=reports / 'e5_verification.json')
    args = parser.parse_args()
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    complete = read(cache / 'representations/complete.json')
    spec = read(cache / 'representations/config.json')
    assert config_hash(spec) == complete['space_id']
    counts, seen, topic_sums, split_sizes = Counter(), set(), {}, Counter()
    norm_error = topic_error = 0.
    coverage = defaultdict(lambda: [0, 0])
    files = sorted((cache / 'representations').glob('*.parquet'))
    assert len(files) == 10
    for path in files:
        marker = read(path.with_suffix('.json'))
        verify_signature(path, marker['output'])
        local = Counter()
        for batch in pq.ParquetFile(path).iter_batches(batch_size=4096):
            ids = batch.column('lyrics_id').to_pylist()
            assert len(set(ids)) == len(ids) and not seen.intersection(ids)
            seen.update(ids)
            vectors = batch.column('embedding').flatten().to_numpy().reshape(batch.num_rows, -1)
            topics = batch.column('topics').flatten().to_numpy().reshape(batch.num_rows, -1)
            available = batch.column('embedding_available').to_numpy(zero_copy_only=False)
            topic_available = batch.column('topics_available').to_numpy(zero_copy_only=False)
            assert vectors.shape[1] == 128 and topics.shape[1] == 20
            assert np.isfinite(vectors).all() and np.isfinite(topics).all()
            assert (topics >= 0).all()
            norm_error = max(norm_error, float(np.max(np.abs(np.linalg.norm(vectors[available], axis=1)-1))))
            topic_error = max(topic_error, float(np.max(np.abs(topics[topic_available].sum(axis=1)-1))))
            local['docs'] += batch.num_rows
            local['embedding_unavailable'] += int((~available).sum())
            local['topics_unavailable'] += int((~topic_available).sum())
            words = batch.column('n_words').to_numpy()
            covered = batch.column('n_covered').to_numpy()
            assert ((covered >= 0) & (covered <= words)).all()
            local['tokens'] += int(words.sum())
            local['covered_tokens'] += int(covered.sum())
            splits = np.array(batch.column('split').to_pylist())
            for split in set(splits):
                mask = splits == split
                local[f'docs_{split}'] += int(mask.sum())
                split_sizes[split] += int(mask.sum())
                topic_sums.setdefault(split, np.zeros(topics.shape[1], dtype=np.float64))
                topic_sums[split] += topics[mask].sum(axis=0, dtype=np.float64)
                coverage[split][0] += int(covered[mask].sum())
                coverage[split][1] += int(words[mask].sum())
        assert dict(local) == marker['counts'], path
        counts.update(local)
        print(f'verified {path.name}', flush=True)
    assert dict(counts) == complete['counts']
    assert norm_error < 1e-5 and topic_error < 1e-5
    prepared = read(cache / 'prepared.json')
    assert all(counts[f'docs_{s}'] == n for s, n in prepared['docs'].items())
    verify_signature(cache / 'baseline/vocabulary.parquet', spec['vocabulary'])
    trained = read(models / 'trained.json')
    for family in ('sgns', 'lda'):
        archived = PureWindowsPath(trained[family]['path'])
        relative = archived.parts[archived.parts.index(models.name) + 1:]
        verify_signature(models.joinpath(*relative), spec[family])
    checkpoint_counts = {}
    for subdir, pattern, expected in [
        ('sgns5/sgns-window5', 'epoch-*.json', 4),
        ('sgns10/sgns-window10', 'epoch-*.json', 4),
        ('lda/lda-k20-seed42', 'shard-*.json', 10),
        ('lda/lda-k40-seed42', 'shard-*.json', 10),
        ('lda/lda-k20-seed43', 'shard-*.json', 10),
    ]:
        checkpoints = sorted((models / subdir).glob(pattern))
        assert len(checkpoints) == expected
        for marker in checkpoints:
            verify_signature(marker.with_suffix('.model'), read(marker)['model'])
        checkpoint_counts[subdir] = len(checkpoints)
    analysis = read(reports / 'e5_analysis.json')
    sample = read(cache / 'samples/validation-2000.json')['rows']
    assert len(analysis['sample_ids']) == len(set(analysis['sample_ids'])) == 2000
    assert set(analysis['sample_ids']) == {r['lyrics_id'] for r in sample}
    assert all(r['split'] == 'validation' for r in sample)
    semantic = read(reports / 'e5_embedding_retrieval.json')
    lexical = read(reports / 'e5_tfidf_retrieval.json')
    assert semantic['space_id'] == complete['space_id']
    assert semantic['available_candidates'] == counts['docs_train']
    assert [q['query']['lyrics_id'] for q in semantic['queries']] == [q['query']['lyrics_id'] for q in lexical['queries']]
    selected_ids = set()
    for q in semantic['queries']:
        selected_ids.add(q['query']['lyrics_id'])
        selected_ids.update(r['lyrics_id'] for r in q['neighbors'][:2])
        assert len(q['neighbors']) == 10
        assert all(r['split'] == 'train' and np.isfinite(r['cosine']) for r in q['neighbors'])
    examples = []
    for source in sorted((cache / 'documents').glob('*.parquet')):
        marker = read(cache / 'checkpoints' / source.with_suffix('.json').name)
        verify_signature(source, marker['documents'])
        verify_signature(cache / 'counts' / source.name, marker['counts'])
        for batch in pq.ParquetFile(source).iter_batches(batch_size=4096):
            found = batch.filter(pc.is_in(batch.column('lyrics_id'), value_set=pa.array(sorted(selected_ids))))
            for row in found.to_pylist():
                examples.append({k: v for k, v in row.items() if k != 'words'} |
                                {'words': row['words'][:180], 'excerpt_scope': 'first <=180 surface words, not whole lyric'})
    result = {'verified_utc': utc_now(), 'scope': 'real full-corpus outputs; no fitting or test relevance evaluation',
              'space_id': complete['space_id'], 'counts': dict(counts), 'unique_ids': len(seen),
              'checkpoint_counts': checkpoint_counts, 'max_embedding_norm_error': norm_error,
              'max_topic_sum_error': topic_error,
              'token_coverage_by_split': {s: c/n for s, (c, n) in coverage.items()},
              'topic_mean_by_split': {s: (sums/split_sizes[s]).tolist() for s, sums in topic_sums.items()},
              'validation_sample_size': 2000, 'retrieval_queries': len(semantic['queries']),
              'retrieval_excerpt_review_material': examples,
              'report_sha256': {p.name: file_sha256(p) for p in [reports/'e5_analysis.json', reports/'e5_embedding_retrieval.json', reports/'e5_tfidf_retrieval.json']}}
    write_json_atomic(args.output, result)


if __name__ == '__main__':
    main()
