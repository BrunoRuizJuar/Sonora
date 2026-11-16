"""Aggregate full E4 sentence metrics, then audit a declared example selection."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/sonora/src'))
from sonora.nlp.syntax import aggregate, examples

if __name__=='__main__':
    from sonora.storage.runs import run_lock
    with run_lock(ROOT/'runtime/locks/e4_syntax.lock'):
        aggregate(ROOT)
        examples(ROOT)
