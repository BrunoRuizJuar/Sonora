"""Read-only validation of an already complete E5 lexical cache."""
import json
from pathlib import Path

from sonora.nlp import semantics
from sonora.nlp.semantics import config_hash, signature
from sonora.storage.runs import file_sha256


def validate_cache(cache: Path):
    config = json.loads((cache / 'config.json').read_text(encoding='utf-8'))
    prepared = json.loads((cache / 'prepared.json').read_text(encoding='utf-8'))
    if not prepared.get('complete') or prepared['config_hash'] != config_hash(config):
        raise RuntimeError('Incomplete or incompatible lexical cache')
    if config['code_sha256'] != file_sha256(Path(semantics.__file__)):
        raise RuntimeError('Preparation code differs from cache provenance')
    for item in config['inputs']:
        if signature(Path(item['path'])) != item:
            raise RuntimeError(f"Changed source {item['path']}")
    markers = sorted((cache / 'checkpoints').glob('*.json'))
    if len(markers) != prepared['shards'] or len(list((cache / 'documents').glob('*.parquet'))) != prepared['shards']:
        raise RuntimeError('Missing/extra cached shards')
    for marker in markers:
        checkpoint = json.loads(marker.read_text(encoding='utf-8'))
        for name in ('documents', 'counts'):
            expected = checkpoint[name]
            if signature(Path(expected['path'])) != expected:
                raise RuntimeError(f'Corrupt cache: {marker}')
    return prepared
