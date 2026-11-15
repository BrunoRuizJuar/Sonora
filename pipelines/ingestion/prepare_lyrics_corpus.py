#!/usr/bin/env python3
"""SONORA - preparación del corpus completo de letras en inglés y vínculos de la demo.

Ejemplos (desde la raíz del repo, Windows):

  .venv\\Scripts\\python.exe pipelines\\ingestion\\prepare_lyrics_corpus.py inspect
  .venv\\Scripts\\python.exe pipelines\\ingestion\\prepare_lyrics_corpus.py all --run-id lyrics_full_v1
  # smoke test sobre un subconjunto (NO es el corpus completo):
  .venv\\Scripts\\python.exe pipelines\\ingestion\\prepare_lyrics_corpus.py all --shards train-00000-of-00010 --row-limit 20000

Reanudar = repetir el mismo comando con el mismo --run-id y la misma configuración.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys

ROOT_DEFAULT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DEFAULT / "packages" / "sonora" / "src"))

from sonora.ingestion import genius, lyrics_corpus as lc  # noqa: E402
from sonora.storage import runs  # noqa: E402

STAGES = ("ingest", "consolidate", "split", "demo", "report")


def make_detector_factory(kind: str):
    def factory():
        from sonora.nlp.language import LangidDetector, LinguaDetector

        logging.getLogger("sonora.lyrics_corpus").info("Cargando lingua (%s) + py3langid...", kind)
        return LinguaDetector(low_accuracy=(kind == "lingua-low")), LangidDetector()
    return factory


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("inspect", "sources", *STAGES, "all", "status"))
    parser.add_argument("--root", type=Path, default=ROOT_DEFAULT)
    parser.add_argument("--config", type=Path, default=None, help="por defecto config/lyrics_corpus.yaml")
    parser.add_argument("--run-id", default=None, help="por defecto lyrics_<full|subset>_<hash de config>")
    parser.add_argument("--shards", nargs="*", default=None, help="subconjunto de shards (smoke test)")
    parser.add_argument("--row-limit", type=int, default=None, help="filas por shard (smoke test)")
    parser.add_argument("--batch-size", type=int, default=2000, help="filas por batch de lectura; no cambia resultados")
    parser.add_argument("--max-chunks", type=int, default=None, help="detener la ingesta tras N partes (reanudable)")
    parser.add_argument("--detector", choices=("lingua", "lingua-low"), default="lingua")
    parser.add_argument("--no-input-hash", action="store_true", help="no calcular sha256 de los Parquet")
    parser.add_argument("--force-unlock", action="store_true")
    return parser.parse_args(argv)


def setup_logging(root: Path, run_id: str) -> None:
    log_dir = root / "runtime" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger("sonora.lyrics_corpus")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    for handler in (logging.StreamHandler(sys.stdout), logging.FileHandler(log_dir / f"{run_id}.log", encoding="utf-8")):
        handler.setFormatter(fmt)
        logger.addHandler(handler)


def main(argv=None) -> int:
    args = parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    root = args.root.resolve()
    config = lc.load_config(args.config or root / "config" / "lyrics_corpus.yaml")
    scope = lc.Scope(shards=args.shards or None, row_limit_per_shard=args.row_limit)
    run_id = args.run_id or lc.default_run_id(config, scope)
    run = lc.Run(root=root, config=config, run_id=run_id, scope=scope)

    if args.command == "inspect":
        for path in run.shard_paths():
            info = genius.inspect_shard(path)
            print(json.dumps(info, ensure_ascii=False))
        return 0
    if args.command == "status":
        print(json.dumps(run.load_manifest().get("stages", {}), indent=2, ensure_ascii=False))
        return 0

    setup_logging(root, run_id)
    log = logging.getLogger("sonora.lyrics_corpus")
    log.info("run_id=%s scope=%s ingest_hash=%s", run_id, scope.as_dict(), run.ingest_hash[:12])
    with runs.run_lock(run.lock_path, force=args.force_unlock):
        if args.command == "sources":
            for entry in lc.source_snapshot(run, with_sha256=True):
                print(json.dumps(entry, ensure_ascii=False))
            return 0
        todo = STAGES if args.command == "all" else (args.command,)
        for stage in todo:
            if stage == "ingest":
                result = lc.ingest(run, make_detector_factory(args.detector), batch_size=args.batch_size,
                                   max_chunks=args.max_chunks, hash_inputs=not args.no_input_hash)
                if result["status"] != "complete":
                    log.warning("Ingesta incompleta: %d partes restantes. Repite el comando para reanudar.",
                                result["chunks_remaining"])
                    return 2
            elif stage == "consolidate":
                lc.consolidate(run, batch_size=args.batch_size)
            elif stage == "split":
                lc.split(run)
            elif stage == "demo":
                lc.link_demo(run)
            elif stage == "report":
                rep = lc.report(run)
                log.info("Reporte: %s", run.report_dir / "quality_report.md")
                log.info("Estados: %s | canónicas: %d | reconciliado: %s",
                         rep["status_counts"], rep["canonical_lyrics"], rep["reconciled"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
