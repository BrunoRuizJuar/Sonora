"""Bounded-memory access to the Genius Parquet shards with GLOBAL row locators.

A locator is ``<file name>#row=<zero-based row inside the whole shard>``; it never
depends on batch size or row-group layout (same format as the matching run).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

REQUIRED_COLUMNS = ("title", "artist", "tag", "year", "lyrics")


def locator(file_name: str, row: int) -> str:
    return f"{file_name}#row={row}"


@dataclass(frozen=True, slots=True)
class Chunk:
    shard: str          # file name, e.g. train-00000-of-00010.parquet
    index: int          # chunk number inside the shard
    start: int          # first global row (inclusive)
    end: int            # last global row (exclusive)

    @property
    def part_name(self) -> str:
        return f"part-{self.index:05d}.parquet"

    @property
    def shard_stem(self) -> str:
        return self.shard.removesuffix(".parquet")


def list_shards(directory: Path, pattern: str) -> list[Path]:
    return sorted(directory.glob(pattern))


def inspect_shard(path: Path) -> dict:
    import pyarrow.parquet as pq

    parquet = pq.ParquetFile(path)
    meta = parquet.metadata
    schema = parquet.schema_arrow
    return {
        "name": path.name,
        "bytes": path.stat().st_size,
        "mtime_ns": path.stat().st_mtime_ns,
        "num_rows": meta.num_rows,
        "num_row_groups": meta.num_row_groups,
        "columns": {field.name: str(field.type) for field in schema},
        "created_by": meta.created_by,
    }


def plan_chunks(shard: str, num_rows: int, chunk_rows: int, row_limit: int | None = None) -> list[Chunk]:
    total = min(num_rows, row_limit) if row_limit else num_rows
    return [
        Chunk(shard, i, start, min(start + chunk_rows, total))
        for i, start in enumerate(range(0, total, chunk_rows))
    ]


def iter_rows(path: Path, start: int, end: int, batch_size: int, columns: list[str]) -> Iterator[tuple[int, object]]:
    """Yield ``(first_global_row, RecordBatch)`` covering exactly ``[start, end)``."""
    import pyarrow.parquet as pq

    parquet = pq.ParquetFile(path)
    meta = parquet.metadata
    offsets = [0]
    for i in range(meta.num_row_groups):
        offsets.append(offsets[-1] + meta.row_group(i).num_rows)
    groups = [i for i in range(meta.num_row_groups) if offsets[i] < end and offsets[i + 1] > start]
    if not groups:
        return
    position = offsets[groups[0]]
    emitted = 0
    for batch in parquet.iter_batches(batch_size=batch_size, row_groups=groups, columns=columns):
        b_start, b_end = position, position + batch.num_rows
        position = b_end
        lo, hi = max(start, b_start), min(end, b_end)
        if lo < hi:
            emitted += hi - lo
            yield lo, batch.slice(lo - b_start, hi - lo)
        if position >= end:
            break
    if emitted != end - start:
        raise ValueError(f"{path.name}: se esperaban {end - start} filas en [{start},{end}) y se leyeron {emitted}")


def read_rows_at(path: Path, rows: list[int], columns: list[str]) -> dict[int, dict]:
    """Random access to a few global rows (audits, locator verification)."""
    import pyarrow.parquet as pq

    parquet = pq.ParquetFile(path)
    meta = parquet.metadata
    offsets = [0]
    for i in range(meta.num_row_groups):
        offsets.append(offsets[-1] + meta.row_group(i).num_rows)
    wanted: dict[int, list[int]] = {}
    import bisect

    for row in rows:
        if not 0 <= row < meta.num_rows:
            continue
        group = bisect.bisect_right(offsets, row) - 1
        wanted.setdefault(group, []).append(row)
    out: dict[int, dict] = {}
    for group, group_rows in wanted.items():
        table = parquet.read_row_group(group, columns=columns)
        for row in group_rows:
            out[row] = table.slice(row - offsets[group], 1).to_pylist()[0]
    return out
