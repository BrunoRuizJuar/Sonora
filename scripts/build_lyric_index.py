"""Prepare original-lyrics lookup without rebuilding E5 or recommendation release."""
import json
from pathlib import Path
from sonora.recommendation.lyric_text import build_lyric_index

if __name__ == '__main__':
    release = json.loads(Path('artifacts/releases/lyrics-serving-v1/release.json').read_text('utf-8'))
    prepared = json.loads(Path('data/processed/nlp/lyrics_full_v1/semantics/e5-surface-v2/config.json').read_text('utf-8'))
    build_lyric_index('data/processed/lyrics/lyrics_full_v1/corpus', 'artifacts/releases/lyrics-original-v1', release['space_id'], release['rows'], prepared['inputs'])
