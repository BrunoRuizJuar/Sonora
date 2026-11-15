#!/usr/bin/env python3
"""Estadísticas por letra del corpus canónico completo (E1/E2): cambios de limpieza,
repetición de versos y riqueza léxica.

  .venv\\Scripts\\python.exe pipelines\\nlp\\corpus_stats.py [--workers 4]
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "sonora" / "src"))

from sonora.nlp.doc_stats import build_doc_stats  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="lyrics_full_v1")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    corpus = sorted((ROOT / "data/processed/lyrics" / args.run_id / "corpus").glob("*.parquet"))
    out = ROOT / "data/processed/nlp" / args.run_id / "doc_stats"
    t0 = time.time()
    n = build_doc_stats(corpus, out, args.workers)
    print(f"{n} letras -> {out} en {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
