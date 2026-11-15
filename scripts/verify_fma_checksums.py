#!/usr/bin/env python3
"""Verifica los MP3 de una variante FMA contra su archivo ``checksums`` (sha1sum).

Uso: python scripts/verify_fma_checksums.py data/raw/fma/fma_medium
Escribe ``manifests/sources/<variante>_checksums_verification.json``. No modifica el audio.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys


def sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with open(path, "rb") as handle:
        while block := handle.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def main(argv: list[str]) -> int:
    base = Path(argv[1]).resolve()
    root = Path(__file__).resolve().parents[1]
    expected = {}
    for line in (base / "checksums").read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            expected[name.lstrip("*").strip()] = digest
    present = {str(p.relative_to(base)).replace("\\", "/") for p in base.rglob("*.mp3")}
    missing = sorted(set(expected) - present)
    extra = sorted(present - set(expected))
    names = sorted(set(expected) & present)
    with ThreadPoolExecutor(8) as pool:
        got = dict(zip(names, pool.map(lambda n: sha1(base / n), names)))
    bad = sorted(n for n in names if got[n] != expected[n])
    result = {
        "variant_dir": str(base.relative_to(root)).replace("\\", "/"),
        "verified_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "expected_files": len(expected), "present_mp3": len(present),
        "verified_ok": len(names) - len(bad), "checksum_mismatch": bad,
        "missing": missing, "extra_not_in_checksums": extra,
        "zero_byte_files": sorted(n for n in present if (base / n).stat().st_size == 0),
        "total_bytes": sum((base / n).stat().st_size for n in present),
    }
    out = root / "manifests" / "sources" / f"{base.name}_checksums_verification.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in result.items()}, indent=2))
    return 0 if not (bad or missing) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
