"""Inspect, safely restore and byte-verify the continuation archive."""
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'SONORA_datos_continuacion.zip'
EXPECTED = '5d6ffb0bb8cf40e5659b4ab1c93c0cf9af699114cbe2081093eeaaa93a0144e6'

def digest(stream):
    h = hashlib.sha256()
    while block := stream.read(8 * 1024 * 1024):
        h.update(block)
    return h.hexdigest()

with zipfile.ZipFile(ARCHIVE) as z:
    entries = [e for e in z.infolist() if not e.is_dir()]
    names = [e.filename for e in entries]
    if len(set(names)) != len(names):
        raise RuntimeError('Duplicate ZIP paths')
    for e in entries:
        target = (ROOT / e.filename).resolve()
        if not target.is_relative_to(ROOT) or not e.filename.startswith('data/processed/'):
            raise RuntimeError(f'Unexpected ZIP path: {e.filename}')
    print(json.dumps({'files': len(entries), 'bytes': sum(e.file_size for e in entries),
                      'groups': dict(Counter('/'.join(n.split('/')[:4]) for n in names))}), flush=True)
    print('Checking archive SHA256...', flush=True)
    with ARCHIVE.open('rb') as f:
        actual = digest(f)
    if actual != EXPECTED:
        raise RuntimeError(f'Archive SHA256 mismatch: {actual}')
    print('Archive SHA256 OK. Checking existing files before extraction...', flush=True)
    for e in entries:
        target = ROOT / e.filename
        if target.exists():
            with target.open('rb') as f, z.open(e) as source:
                if target.stat().st_size != e.file_size or digest(f) != digest(source):
                    raise RuntimeError(f'Existing file differs; no extraction performed: {e.filename}')
    restored = 0
    for i, e in enumerate(entries, 1):
        target = ROOT / e.filename
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + '.migration-tmp')
            if temporary.exists():
                raise RuntimeError(f'Investigate existing temporary: {temporary}')
            with z.open(e) as source, temporary.open('xb') as out:
                while block := source.read(8 * 1024 * 1024):
                    out.write(block)
            temporary.rename(target)
            restored += 1
        if i % 1000 == 0:
            print(f'Restored/retained {i}/{len(entries)}', flush=True)
    print('Checking every extracted file against ZIP (SHA256 and CRC)...', flush=True)
    for i, e in enumerate(entries, 1):
        with (ROOT / e.filename).open('rb') as f, z.open(e) as source:
            if digest(f) != digest(source):
                raise RuntimeError(f'Extracted file mismatch: {e.filename}')
        if i % 1000 == 0:
            print(f'Verified {i}/{len(entries)}', flush=True)
    result = {'archive_sha256': actual, 'files': len(entries), 'restored': restored,
              'uncompressed_bytes': sum(e.file_size for e in entries),
              'all_files_sha256_match': True, 'zip_crc_checked': True, 'archive_retained': ARCHIVE.exists()}
    (ROOT / 'runtime/migration_verification.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)
