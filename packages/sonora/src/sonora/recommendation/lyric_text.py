"""Indexed access to original canonical lyrics, without scanning per request."""
import json
import os
from pathlib import Path, PureWindowsPath
import sqlite3

import pyarrow.parquet as pq

from sonora.nlp.semantics import signature


def build_lyric_index(corpus, target, space_id, expected_rows, expected_sources=None):
    corpus, target = Path(corpus), Path(target)
    target.mkdir(parents=True, exist_ok=True)
    lock = target / '.writer.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    temp = target / 'lyrics.building.sqlite'
    try:
        os.write(fd, str(os.getpid()).encode())
        if expected_sources is not None:
            expected_sources = {PureWindowsPath(item['path']).name: item for item in expected_sources}
        temp.unlink(missing_ok=True)
        db = sqlite3.connect(temp)
        try:
            db.execute('CREATE TABLE locations (lyrics_id TEXT PRIMARY KEY, source INTEGER, row_group INTEGER, position INTEGER) WITHOUT ROWID')
            db.execute('CREATE TABLE metadata (manifest TEXT)')
            sources, total = [], 0
            for path in sorted(corpus.glob('*.parquet')):
                sig = signature(path)
                if expected_sources is not None:
                    expected = expected_sources.get(path.name)
                    if expected is None or sig != expected | {'path': sig['path']}:
                        raise ValueError(f'Corpus differs from frozen E5 inputs: {path.name}')
                source_id = len(sources)
                sources.append(sig | {'mtime_ns': path.stat().st_mtime_ns})
                reader = pq.ParquetFile(path)
                for group in range(reader.num_row_groups):
                    identifiers = reader.read_row_group(group, columns=['lyrics_id'])['lyrics_id'].to_pylist()
                    db.executemany('INSERT INTO locations VALUES (?,?,?,?)', ((identifier, source_id, group, i) for i, identifier in enumerate(identifiers)))
                    total += len(identifiers)
                db.commit()
                print(f'Indexed lyrics: {path.name}', flush=True)
            if total != expected_rows:
                raise ValueError('Incomplete lyrics coverage')
            manifest = {'space_id': space_id, 'rows': total, 'sources': sources, 'view': 'lyrics_original'}
            db.execute('INSERT INTO metadata VALUES (?)', (json.dumps(manifest),))
            db.commit()
        finally:
            db.close()
        temp.replace(target / 'lyrics.sqlite')
        return manifest
    finally:
        os.close(fd)
        lock.unlink()


class LyricTextStore:
    def __init__(self, root, space_id, rows):
        path = Path(root) / 'lyrics.sqlite'
        self.db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, check_same_thread=False)
        try:
            self.manifest = json.loads(self.db.execute('SELECT manifest FROM metadata').fetchone()[0])
            if self.manifest['space_id'] != space_id or self.manifest['rows'] != rows:
                raise ValueError('Lyrics index belongs to another catalog')
            self.sources = []
            for item in self.manifest['sources']:
                source = Path(item['path'])
                stat = source.stat()
                if stat.st_size != item['bytes'] or stat.st_mtime_ns != item['mtime_ns']:
                    raise ValueError('Original lyrics changed; rebuild the index')
                self.sources.append(source)
        except BaseException:
            self.db.close()
            raise

    def get(self, identifier):
        row = self.db.execute('SELECT source,row_group,position FROM locations WHERE lyrics_id=?', (identifier,)).fetchone()
        if row is None:
            raise KeyError(identifier)
        source, group, position = row
        stat = self.sources[source].stat()
        expected = self.manifest['sources'][source]
        if stat.st_size != expected['bytes'] or stat.st_mtime_ns != expected['mtime_ns']:
            raise ValueError('Original lyrics changed')
        record = pq.ParquetFile(self.sources[source]).read_row_group(group, columns=['lyrics_id', 'lyrics_original']).slice(position, 1).to_pylist()[0]
        if record['lyrics_id'] != identifier:
            raise ValueError('Lyrics identity mismatch')
        if not record['lyrics_original'] or not record['lyrics_original'].strip():
            raise ValueError('Original lyrics unavailable')
        return {'lyrics_id': identifier, 'text': record['lyrics_original'], 'view': 'original', 'space_id': self.manifest['space_id']}

    def close(self):
        self.db.close()
