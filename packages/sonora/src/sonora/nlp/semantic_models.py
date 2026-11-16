"""E5 train-only SGNS/LDA experiments; atomic epoch/shard checkpoints.

This module does not consume test. Validation scores are intrinsic diagnostics,
never recommendation relevance. Models and vectors stay under data/ or artifacts/.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import heapq
import importlib.metadata
import json
import os
import pickle
from pathlib import Path
import time
import sys

import numpy as np

from sonora.nlp.semantics import Documents, config_hash, require_same, signature
from sonora.storage.runs import file_sha256, write_json_atomic


class SplitDocuments(Documents):
    """Filter in Arrow before creating Python strings for a held-out sample."""
    def rows(self):
        import pyarrow.compute as pc
        import pyarrow.parquet as pq
        for path in sorted((self.cache / 'documents').glob('*.parquet')):
            for batch in pq.ParquetFile(path).iter_batches(batch_size=256):
                for row in batch.filter(pc.equal(batch.column('split'), self.split)).to_pylist():
                    yield row


def stable_hash(word):
    return int.from_bytes(hashlib.sha256(word.encode('utf-8')).digest()[:8], 'little')


def save_model(model, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    # LdaModel.save forces sidecar files even with separately=[]; a rename of
    # only its main file is not atomic. Keep the complete trusted local object
    # in one pickle, including state, matrices and RNG.
    with tmp.open('wb') as handle:
        pickle.dump(model, handle, protocol=5)
    os.replace(tmp, path)


def load_model(path):
    """Load only SONORA's own local checkpoints (pickle is not an interchange format)."""
    with Path(path).open('rb') as handle:
        return pickle.load(handle)


def load_vocab(cache):
    import pyarrow.parquet as pq
    fit = json.loads((cache / 'baseline/fit.json').read_text(encoding='utf-8'))
    if fit['fit_split'] != 'train' or file_sha256(cache / 'baseline/vocabulary.parquet') != fit['vocabulary_sha256']:
        raise RuntimeError('Corrupt or incompatible train vocabulary')
    return pq.read_table(cache / 'baseline/vocabulary.parquet').to_pylist()


class Sentences:
    def __init__(self, cache):
        self.cache = cache

    def __iter__(self):
        for terms in SplitDocuments(self.cache, 'train'):
            # Gensim's sentence limit must never silently truncate a long lyric.
            for start in range(0, len(terms), 1000):
                yield terms[start:start+1000]


def validation_sample(cache, size=2000):
    """Bottom SHA256 IDs: deterministic visualization/diagnostic sample only."""
    saved = cache / 'samples' / f'validation-{size}.json'
    prepared_hash = file_sha256(cache / 'prepared.json')
    if saved.exists():
        cached = json.loads(saved.read_text(encoding='utf-8'))
        if cached['prepared_sha256'] != prepared_hash:
            raise RuntimeError('Incompatible validation sample cache')
        return cached['rows']
    heap = []
    for row in SplitDocuments(cache, 'validation').rows():
        key = int.from_bytes(hashlib.sha256(row['lyrics_id'].encode()).digest(), 'big')
        entry = (-key, row['lyrics_id'], row)
        if len(heap) < size:
            heapq.heappush(heap, entry)
        elif key < -heap[0][0]:
            heapq.heapreplace(heap, entry)
    rows = [entry[2] for entry in sorted(heap, reverse=True)]
    write_json_atomic(saved, {'method': 'bottom SHA256 lyrics_id', 'prepared_sha256': prepared_hash, 'rows': rows})
    return rows


def sgns_diagnostic(model, sample, max_pairs=100_000):
    """Fixed +/-5 context, five train-unigram^.75 negatives, seed 42.

    Average binary log likelihood of observed and sampled negative pairs. A proxy
    for the training objective, not normalized language perplexity or relevance.
    Same pairs and negatives for both window candidates.
    """
    rng = np.random.default_rng(42)
    frequency = np.array([model.wv.get_vecattr(w, 'count') for w in model.wv.index_to_key], dtype=float)
    probability = frequency**.75
    probability /= probability.sum()
    negative_draws = rng.choice(len(probability), (max_pairs, 5), p=probability)
    score = pairs = 0
    for row in sample:
        terms = row['words']
        for center, word in enumerate(terms):
            if word not in model.wv:
                continue
            target = model.wv[word]
            for j in range(max(0, center-5), min(len(terms), center+6)):
                if j == center or terms[j] not in model.wv:
                    continue
                positive = model.wv.key_to_index[terms[j]]
                negatives = negative_draws[pairs]
                # Negative sampling can collide with positive; omit that term,
                # matching Gensim's skip behaviour (no resampling).
                negatives = negatives[negatives != positive]
                score += float(-np.logaddexp(0., -target @ model.syn1neg[positive]))
                score += float(-np.logaddexp(0., model.syn1neg[negatives] @ target).sum())
                pairs += 1
                if pairs >= max_pairs:
                    return {'mean_log_objective': score/pairs, 'positive_pairs': pairs}
    return {'mean_log_objective': score/pairs if pairs else None, 'positive_pairs': pairs}


def train_sgns(cache, out, sample, epochs=3, workers=1, windows=(5, 10)):
    from gensim.models import Word2Vec
    import gensim

    vocab = load_vocab(cache)
    freq = {r['word']: r['train_tf'] for r in vocab}
    results = []
    for window in windows:
        dest = out / f'sgns-window{window}'
        spec = {'family': 'SGNS', 'vector_size': 128, 'window': window, 'negative': 5,
                'ns_exponent': .75, 'sample': .001, 'epochs': epochs, 'workers': workers,
                'seed': 42, 'hs': 0, 'alpha': .025, 'min_alpha': .0001,
                'vocabulary': signature(cache / 'baseline/vocabulary.parquet'),
                'source': config_hash(json.loads((cache / 'config.json').read_text(encoding='utf-8'))),
                'gensim': gensim.__version__, 'python': sys.version, 'numpy': np.__version__,
                'scipy': importlib.metadata.version('scipy'), 'code': file_sha256(Path(__file__)),
                'sentence_policy': 'document stream, chunks <=1000 words, no cross-document windows',
                'reproducibility': 'stable SHA256 hash; bitwise training requires workers=1 and same environment'}
        require_same(dest / 'config.json', spec)
        checkpoints = sorted(p for p in dest.glob('epoch-*.model') if p.with_suffix('.json').exists())
        if checkpoints:
            expected = json.loads(checkpoints[-1].with_suffix('.json').read_text(encoding='utf-8'))['model']
            if signature(checkpoints[-1]) != expected:
                raise RuntimeError('Corrupt SGNS checkpoint')
            model = load_model(checkpoints[-1])
            start = int(checkpoints[-1].stem.split('-')[-1])
        else:
            model = Word2Vec(vector_size=128, window=window, sg=1, negative=5,
                             ns_exponent=.75, sample=.001, seed=42, workers=workers,
                             min_count=1, sorted_vocab=1, hashfxn=stable_hash)
            model.build_vocab_from_freq(freq)
            start = 0
            save_model(model, dest / 'epoch-000.model')
            write_json_atomic(dest / 'epoch-000.json', {'model': signature(dest / 'epoch-000.model')})
        for epoch in range(start, epochs):
            t0 = time.monotonic()
            alpha_start = .025 + (.0001-.025)*epoch/epochs
            alpha_end = .025 + (.0001-.025)*(epoch+1)/epochs
            train_words = json.loads((cache / 'prepared.json').read_text(encoding='utf-8'))['tokens']['train']
            trained = model.train(Sentences(cache), total_words=train_words, epochs=1,
                                  start_alpha=alpha_start, end_alpha=alpha_end)
            target = dest / f'epoch-{epoch+1:03d}.model'
            save_model(model, target)
            write_json_atomic(dest / f'epoch-{epoch+1:03d}.json', {
                'epoch': epoch+1, 'trained_effective_and_raw_words': list(trained),
                'seconds': time.monotonic()-t0, 'model': signature(target)})
            print(f'SGNS window={window} epoch={epoch+1} words={trained}', flush=True)
        diagnostic = sgns_diagnostic(model, sample)
        write_json_atomic(dest / 'validation.json', diagnostic)
        results.append({'path': str(dest / f'epoch-{epochs:03d}.model'), 'window': window, **diagnostic})
        del model
    if not all(r['positive_pairs'] for r in results):
        raise RuntimeError('No validation context pairs')
    chosen = max(results, key=lambda r: r['mean_log_objective'])
    write_json_atomic(out / 'sgns_selection.json', {'candidates': results, 'selected': chosen,
                      'criterion': 'largest validation mean SGNS log objective; same pairs/negative RNG',
                      'recommendation_quality': 'not evaluated'})
    return chosen


def bow(terms, ids):
    return sorted(Counter(ids[w] for w in terms if w in ids).items())


def train_lda(cache, out, sample):
    from gensim.models import LdaModel, CoherenceModel
    from gensim.corpora import Dictionary
    import pyarrow.parquet as pq

    vocab = load_vocab(cache)
    ids = {r['word']: r['index'] for r in vocab}
    dictionary = Dictionary()
    dictionary.token2id = ids
    dictionary.id2token = {v: k for k, v in ids.items()}
    dictionary.dfs = {r['index']: r['train_df'] for r in vocab}
    dictionary.num_docs = json.loads((cache / 'prepared.json').read_text(encoding='utf-8'))['docs']['train']
    validation = [bow(r['words'], ids) for r in sample]
    validation = [x for x in validation if x]
    results = []
    files = sorted((cache / 'documents').glob('*.parquet'))
    experiments = [(20, 42), (40, 42)]
    for topics, seed in experiments:
        dest = out / f'lda-k{topics}-seed{seed}'
        spec = {'k': topics, 'alpha': 'symmetric', 'eta': 'symmetric', 'iterations': 30,
                'chunksize': 1024, 'passes': 1, 'decay': .5, 'offset': 1., 'seed': seed,
                'fit_split': 'train', 'vocabulary': signature(cache / 'baseline/vocabulary.parquet'),
                'prepared_sha256': file_sha256(cache / 'prepared.json'),
                'gensim': importlib.metadata.version('gensim'), 'python': sys.version, 'numpy': np.__version__,
                'scipy': importlib.metadata.version('scipy'),
                'code': file_sha256(Path(__file__))}
        require_same(dest / 'config.json', spec)
        checkpoints = sorted(p for p in dest.glob('shard-*.model') if p.with_suffix('.json').exists())
        if checkpoints:
            expected = json.loads(checkpoints[-1].with_suffix('.json').read_text(encoding='utf-8'))['model']
            if signature(checkpoints[-1]) != expected:
                raise RuntimeError('Corrupt LDA checkpoint')
            model = load_model(checkpoints[-1])
            start = int(checkpoints[-1].stem.split('-')[-1])
        else:
            model = LdaModel(id2word=dictionary, num_topics=topics, alpha='symmetric',
                             eta='symmetric', random_state=seed, iterations=30, chunksize=1024,
                             passes=1, eval_every=None, minimum_probability=0.)
            start = 0
        for i, source in enumerate(files):
            if i < start:
                continue
            chunk = []
            for batch in pq.ParquetFile(source).iter_batches(batch_size=256, columns=['split', 'words']):
                for row in batch.to_pylist():
                    if row['split'] == 'train':
                        document = bow(row['words'], ids)
                        if document:
                            chunk.append(document)
                        if len(chunk) >= 1024:
                            model.update(chunk)
                            chunk.clear()
            if chunk:
                model.update(chunk)
            target = dest / f'shard-{i+1:03d}.model'
            save_model(model, target)
            write_json_atomic(target.with_suffix('.json'), {'model': signature(target), 'shards_done': i+1})
            print(f'LDA k={topics} shard={i+1}/{len(files)}', flush=True)
        bound = float(model.log_perplexity(validation))
        coherence = float(CoherenceModel(model=model, corpus=validation, dictionary=dictionary,
                                         coherence='u_mass', topn=10).get_coherence())
        top = [[w for w, p in model.show_topic(k, 10)] for k in range(topics)]
        diagnostic = {'validation_gensim_bound_per_word': bound, 'validation_u_mass': coherence,
                      'topic_diversity_top10': len(set(sum(top, [])))/(10*topics), 'top_words': top}
        write_json_atomic(dest / 'validation.json', diagnostic)
        results.append({'path': str(dest / f'shard-{len(files):03d}.model'), 'k': topics, 'seed': seed, **diagnostic})
        del model
        if len(results) == 2:
            provisional = max(results, key=lambda r: r['validation_gensim_bound_per_word'])
            experiments.append((provisional['k'], 43))  # repeat chosen K for seed stability
    chosen = max((r for r in results if r['seed'] == 42), key=lambda r: r['validation_gensim_bound_per_word'])
    repeated, = (r for r in results if r['seed'] == 43)
    from scipy.optimize import linear_sum_assignment
    a, b = chosen['top_words'], repeated['top_words']
    overlap = np.array([[len(set(left) & set(right))/len(set(left) | set(right))
                         for right in b] for left in a])
    ix, iy = linear_sum_assignment(overlap, maximize=True)
    stability = {'method': 'Hungarian maximum top10-term Jaccard, seed42 vs seed43 at selected K',
                 'mean_jaccard': float(overlap[ix, iy].mean()),
                 'min_jaccard': float(overlap[ix, iy].min()),
                 'matches': [{'seed42_topic': int(i), 'seed43_topic': int(j), 'jaccard': float(overlap[i, j])}
                             for i, j in zip(ix, iy)]}
    write_json_atomic(out / 'lda_selection.json', {'candidates': results, 'selected': chosen,
                      'seed_stability': stability, 'interpretation_review': 'pending; selection is an intrinsic baseline',
                      'criterion': 'largest validation per-word variational bound returned by Gensim',
                      'limits': 'coherence/diversity supplementary; no recommendation judgments; labels unreviewed'})
    return chosen


def train(cache: Path, out: Path, workers=1):
    from sonora.nlp.semantic_validation import validate_cache
    validate_cache(cache)
    sample = validation_sample(cache)
    write_json_atomic(out / 'validation_sample.json', {
        'method': 'bottom SHA256(lyrics_id), validation only', 'requested': 2000,
        'lyrics_ids': [r['lyrics_id'] for r in sample], 'full_corpus_fit': True})
    sgns = train_sgns(cache, out, sample, workers=workers)
    lda = train_lda(cache, out, sample)
    write_json_atomic(out / 'trained.json', {'sgns': sgns, 'lda': lda, 'test_consumed': False})
