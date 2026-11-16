"""Train E5 candidates serially. Test stays reserved. Re-run to resume."""
import argparse
import logging
import os
from pathlib import Path
import sys

for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'packages/sonora/src'))
from sonora.nlp.semantic_models import train
from sonora.storage.runs import run_lock

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', default='e5-surface-v2')
    parser.add_argument('--workers', type=int, default=1)
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id or args.run_id in {'.', '..'} or args.workers < 1:
        parser.error('Invalid run-id/workers')
    (ROOT / 'runtime').mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
                        filename=ROOT / 'runtime/e5_training.log', encoding='utf-8')
    with run_lock(ROOT / 'runtime/locks' / f'{args.run_id}.lock'):
        train(ROOT / 'data/processed/nlp/lyrics_full_v1/semantics' / args.run_id,
              ROOT / 'artifacts/models/lyrics_full_v1' / args.run_id, args.workers)
