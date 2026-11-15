#!/usr/bin/env python3
"""Conteo de uni/bi/trigramas por split sobre el corpus canónico COMPLETO (E2).

  .venv\\Scripts\\python.exe pipelines\\nlp\\count_ngrams.py [--workers 2] [--spill-entries 2000000]

Reanudable: los shards ya contados y las particiones ya reducidas se conservan.
Salida: data/processed/nlp/<run>/ngrams/{counts,summary.json} (fuera de Git).
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "sonora" / "src"))

from sonora.nlp.ngrams import count_corpus  # noqa: E402
from sonora.storage import runs  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="lyrics_full_v1")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--spill-entries", type=int, default=2_000_000)
    parser.add_argument("--force-unlock", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout),
                                  logging.FileHandler(ROOT / "runtime/logs" / f"ngrams_{args.run_id}.log", encoding="utf-8")])
    corpus = sorted((ROOT / "data/processed/lyrics" / args.run_id / "corpus").glob("*.parquet"))
    splits = ROOT / "data/processed/splits" / args.run_id / "lyrics_splits.parquet"
    work = ROOT / "data/processed/nlp" / args.run_id / "ngrams"
    with runs.run_lock(ROOT / "runtime/locks" / f"ngrams_{args.run_id}.lock", force=args.force_unlock):
        summary = count_corpus(corpus, splits, work, workers=args.workers, spill_entries=args.spill_entries)
    logging.info("n-gramas: %s", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
