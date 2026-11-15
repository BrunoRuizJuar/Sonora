"""Run bookkeeping: config hashing, atomic writes, single-writer lock, provenance."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
from typing import Any, Iterator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def config_hash(config: dict) -> str:
    return hashlib.sha256(canonical_json(config).encode("utf-8")).hexdigest()


def file_sha256(path: Path, chunk: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while block := handle.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def code_fingerprint(paths: list[Path]) -> str:
    """Hash of the source files that define this pipeline (repo has no commits yet)."""
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.name.encode())
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def git_revision(root: Path) -> str | None:
    head = root / ".git" / "HEAD"
    try:
        ref = head.read_text().strip()
        if ref.startswith("ref: "):
            target = root / ".git" / ref[5:]
            return target.read_text().strip() if target.exists() else None
        return ref
    except OSError:
        return None


def environment_info() -> dict:
    versions = {}
    for package in ("pyarrow", "lingua-language-detector", "pyyaml", "psutil"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    info = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "packages": versions,
    }
    try:
        import psutil

        info["ram_total_bytes"] = psutil.virtual_memory().total
    except ImportError:
        pass
    return info


def peak_rss_bytes() -> int | None:
    try:
        import psutil

        mem = psutil.Process().memory_info()
        return int(getattr(mem, "peak_wset", 0) or mem.rss)
    except ImportError:
        return None


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_parquet_atomic(table, path: Path, compression: str = "zstd") -> None:
    import pyarrow.parquet as pq

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    pq.write_table(table, tmp, compression=compression)
    os.replace(tmp, path)


class ParquetStreamWriter:
    """Streams batches into ``<path>.tmp`` and publishes with an atomic rename on close."""

    def __init__(self, path: Path, schema, compression: str = "zstd") -> None:
        import pyarrow.parquet as pq

        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.tmp = path.with_name(path.name + ".tmp")
        self.rows = 0
        self._writer = pq.ParquetWriter(self.tmp, schema, compression=compression)

    def write(self, table) -> None:
        if table.num_rows:
            self._writer.write_table(table)
            self.rows += table.num_rows

    def close(self) -> None:
        self._writer.close()
        os.replace(self.tmp, self.path)

    def abort(self) -> None:
        try:
            self._writer.close()
        finally:
            self.tmp.unlink(missing_ok=True)


class LockError(RuntimeError):
    pass


@contextmanager
def run_lock(lock_path: Path, force: bool = False) -> Iterator[None]:
    """Exclusive single-writer lock for one output directory."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if force:
        lock_path.unlink(missing_ok=True)
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        owner = lock_path.read_text(errors="replace") if lock_path.exists() else "?"
        raise LockError(
            f"Otro proceso escribe esta ejecución ({lock_path}): {owner}. "
            "Si ese proceso ya terminó, repite con --force-unlock."
        ) from exc
    try:
        os.write(fd, canonical_json({"pid": os.getpid(), "started_utc": utc_now()}).encode())
        os.close(fd)
        yield
    finally:
        lock_path.unlink(missing_ok=True)
