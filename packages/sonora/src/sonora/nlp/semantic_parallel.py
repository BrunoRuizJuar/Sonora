"""User-authorized concurrent E5 families with separate writer directories/locks."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import logging
import multiprocessing
from pathlib import Path

from sonora.storage.runs import file_sha256, run_lock, write_json_atomic


def _family_task(family, cache, out, sample, workers, runtime):
    from threadpoolctl import threadpool_limits
    from sonora.nlp.semantic_models import train_sgns, train_lda

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
                        filename=runtime / f'e5_{family}.log', encoding='utf-8', force=True)
    # Distinct subrun directories: no two processes write one model/checkpoint.
    with run_lock(runtime / 'locks' / f'e5-surface-v2-{family}.lock'):
        with threadpool_limits(1):
            if family.startswith('sgns'):
                return train_sgns(cache, out / family, sample, workers=workers, windows=(int(family[4:]),))
            return train_lda(cache, out / family, sample)


def train_parallel(cache: Path, out: Path, runtime: Path, workers=4):
    from sonora.nlp.semantic_models import validation_sample
    from sonora.nlp.semantic_validation import validate_cache
    from sonora.nlp.semantics import require_same
    from sonora.nlp import semantic_models

    validate_cache(cache)
    runtime.mkdir(parents=True, exist_ok=True)
    sample = validation_sample(cache)  # single writer publishes sample before children
    spec = {'workers_per_sgns_candidate': workers, 'processes': 3, 'blas_threads_per_process': 1,
            'prepared_sha256': file_sha256(cache / 'prepared.json'),
            'model_code_sha256': file_sha256(Path(semantic_models.__file__))}
    require_same(out / 'parallel_config.json', spec)
    write_json_atomic(out / 'validation_sample.json', {
        'method': 'bottom SHA256(lyrics_id), validation only', 'requested': 2000,
        'lyrics_ids': [r['lyrics_id'] for r in sample], 'full_corpus_fit': True})
    selected = {}
    with ProcessPoolExecutor(max_workers=3, mp_context=multiprocessing.get_context('spawn')) as pool:
        futures = {pool.submit(_family_task, family, cache, out, sample, workers, runtime): family
                   for family in ('sgns5', 'sgns10', 'lda')}
        for future in as_completed(futures):
            family = futures[future]
            selected[family] = future.result()
            write_json_atomic(runtime / 'e5_families.json', {'completed': list(selected), 'parallel': True})
            print(f'completed real model family: {family}', flush=True)
    candidates = [selected['sgns5'], selected['sgns10']]
    chosen = max(candidates, key=lambda r: r['mean_log_objective'])
    write_json_atomic(out / 'sgns_selection.json', {'candidates': candidates, 'selected': chosen,
                      'criterion': 'largest validation mean SGNS log objective; same pairs/negatives',
                      'recommendation_quality': 'not evaluated'})
    write_json_atomic(out / 'trained.json', {'sgns': chosen, 'lda': selected['lda'],
                      'test_consumed': False, 'parallel': True})
