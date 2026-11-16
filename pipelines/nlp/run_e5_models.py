"""Run real E5 stages serially with one shared lock and durable status/logs."""
import argparse
import logging
import os
from pathlib import Path
import sys
import traceback

for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'packages/sonora/src'))
from sonora.nlp.semantic_models import train
from sonora.nlp.semantic_parallel import train_parallel
from sonora.nlp.semantic_export import export
from sonora.nlp.semantic_analysis import analyze
from sonora.nlp.semantic_retrieval import retrieve_embeddings
from sonora.storage.runs import run_lock, utc_now, write_json_atomic

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--parallel', action='store_true', help='Two SGNS candidates and LDA in three independent writer subruns')
    args = parser.parse_args()
    if args.workers < 1:
        parser.error('workers must be positive')
    cache = ROOT / 'data/processed/nlp/lyrics_full_v1/semantics/e5-surface-v2'
    models = ROOT / 'artifacts/models/lyrics_full_v1/e5-surface-v2'
    reports = ROOT / 'reports/nlp/lyrics_full_v1'
    figures = ROOT / 'reports/figures/E5'
    runtime = ROOT / 'runtime'
    runtime.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
                        filename=runtime / 'e5_training.log', encoding='utf-8')
    status = {'started_utc': utc_now(), 'pid': os.getpid(), 'workers': args.workers,
              'run_id': 'e5-surface-v2', 'parallel': args.parallel, 'complete': False, 'completed_stages': []}
    with run_lock(runtime / 'locks/e5-surface-v2.lock'):
        stages = [
            ('train', lambda: train_parallel(cache, models, runtime, args.workers)
             if args.parallel else train(cache, models, args.workers)),
            ('export', lambda: export(cache, models)),
            ('analysis', lambda: analyze(cache, models, reports, figures)),
            ('embedding_retrieval', lambda: retrieve_embeddings(cache, models, reports)),
        ]
        try:
            for name, operation in stages:
                status['stage'] = name
                status['updated_utc'] = utc_now()
                write_json_atomic(runtime / 'e5_status.json', status)
                print(f'{utc_now()} start {name}', flush=True)
                operation()
                status['completed_stages'].append(name)
            status['complete'] = True
            status['stage'] = 'done'
        except BaseException:
            status['error'] = traceback.format_exc()
            raise
        finally:
            status['updated_utc'] = utc_now()
            write_json_atomic(runtime / 'e5_status.json', status)
