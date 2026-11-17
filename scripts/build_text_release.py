"""Build serving artifacts without training/exporting E5 again."""
import argparse
from pathlib import Path
from sonora.recommendation.catalog import build_release

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=Path('data/processed/nlp/lyrics_full_v1/semantics/e5-surface-v2/representations'))
    parser.add_argument('--target', type=Path, default=Path('artifacts/releases/lyrics-serving-v1'))
    args = parser.parse_args()
    build_release(args.source, args.target)
