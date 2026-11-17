"""Browse song neighbors using our own frozen E5 embeddings; no retraining."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'packages/sonora/src'))
from sonora.recommendation.lyrics import recommend_lyrics


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('lyrics_id')
    parser.add_argument('--k', type=int, default=10)
    parser.add_argument('--all-splits', action='store_true', help='Exploratory browsing only; includes validation/test candidates')
    args = parser.parse_args()
    root = ROOT / 'data/processed/nlp/lyrics_full_v1/semantics/e5-surface-v2/representations'
    result = recommend_lyrics(root, args.lyrics_id, args.k,
                              ('train', 'validation', 'test') if args.all_splits else ('train',))
    print(json.dumps(result, ensure_ascii=True, indent=2))
