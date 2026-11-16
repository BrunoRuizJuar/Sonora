"""Create validation-sample PCA and concept/context comparisons."""
import os
from pathlib import Path
import sys

for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'packages/sonora/src'))
from sonora.nlp.semantic_analysis import analyze
from sonora.storage.runs import run_lock

if __name__ == '__main__':
    with run_lock(ROOT / 'runtime/locks/e5-surface-v2.lock'):
        analyze(ROOT / 'data/processed/nlp/lyrics_full_v1/semantics/e5-surface-v2',
                ROOT / 'artifacts/models/lyrics_full_v1/e5-surface-v2',
                ROOT / 'reports/nlp/lyrics_full_v1', ROOT / 'reports/figures/E5')
