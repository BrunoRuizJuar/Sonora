"""E5 lexical preparation; one writer, all canonical lyrics, original splits."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'packages/sonora/src'))
from sonora.nlp.semantics import VERSION, fit_baseline, prepare
from sonora.nlp.semantic_validation import validate_cache
from sonora.storage.runs import run_lock

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', default=VERSION)
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id or args.run_id in {'.', '..'}:
        parser.error('run-id must be a directory name')
    with run_lock(ROOT / 'runtime/locks' / f'{args.run_id}.lock'):
        cache = ROOT / 'data/processed/nlp/lyrics_full_v1/semantics' / args.run_id
        if (cache / 'prepared.json').exists():
            # Keep the completed manifest immutable, including the original RSS.
            # Rewriting it on resume would change the baseline's provenance hash.
            validate_cache(cache)
        else:
            cache = prepare(ROOT, args.run_id)
        print(fit_baseline(cache), flush=True)
