#!/usr/bin/env python3
"""SONORA - léxico y anotación spaCy (POS, lemas, dependencias) del corpus canónico COMPLETO.

  .venv\\Scripts\\python.exe pipelines\\nlp\\annotate_corpus.py lexicon
  .venv\\Scripts\\python.exe pipelines\\nlp\\annotate_corpus.py annotate            # reanudable
  .venv\\Scripts\\python.exe pipelines\\nlp\\annotate_corpus.py annotate --max-tasks 20 --workers 4
  .venv\\Scripts\\python.exe pipelines\\nlp\\annotate_corpus.py status

Salidas en data/processed/nlp/<corpus_run_id>/ (fuera de Git); manifiesto en manifests/nlp/.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import logging
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "sonora" / "src"))

from sonora.nlp import annotate as an  # noqa: E402
from sonora.nlp import lexicon as lx  # noqa: E402
from sonora.storage import runs  # noqa: E402


def load_config(path: Path) -> dict:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def setup_logging(name: str) -> None:
    (ROOT / "runtime" / "logs").mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger("sonora.nlp")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    for handler in (logging.StreamHandler(sys.stdout),
                    logging.FileHandler(ROOT / "runtime" / "logs" / f"{name}.log", encoding="utf-8")):
        handler.setFormatter(fmt)
        logger.addHandler(handler)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("lexicon", "annotate", "status"))
    parser.add_argument("--config", type=Path, default=ROOT / "config" / "nlp_annotation.yaml")
    parser.add_argument("--annotation-id", default="spacy_sm_v1")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--max-tasks", type=int, default=None)
    parser.add_argument("--force-unlock", action="store_true")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")

    cfg = load_config(args.config)
    corpus_dir = ROOT / "data" / "processed" / "lyrics" / cfg["corpus_run_id"] / "corpus"
    corpus_files = sorted(corpus_dir.glob("*.parquet"))
    if not corpus_files:
        raise SystemExit(f"No hay corpus en {corpus_dir}")
    nlp_dir = ROOT / "data" / "processed" / "nlp" / cfg["corpus_run_id"]
    lexicon_path = nlp_dir / "lexicon" / "lexicon.parquet"
    gdrop_path = nlp_dir / "lexicon" / "gdrop_forms.parquet"
    manifest_path = ROOT / "manifests" / "nlp" / f"{cfg['corpus_run_id']}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    setup_logging(f"nlp_{cfg['corpus_run_id']}")
    log = logging.getLogger("sonora.nlp")

    if args.command == "status":
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return 0

    with runs.run_lock(ROOT / "runtime" / "locks" / f"nlp_{cfg['corpus_run_id']}.lock", force=args.force_unlock):
        if args.command == "lexicon":
            result = lx.build_lexicon(corpus_files)
            runs.write_parquet_atomic(result["lexicon"], lexicon_path)
            runs.write_parquet_atomic(result["gdrop"], gdrop_path)
            manifest["lexicon"] = {
                "version": lx.LEXICON_VERSION, "token_definition": lx.WORD.pattern,
                "lowercased": True, "view": cfg["text_view"], "docs": result["docs"],
                "tokens": result["tokens"], "types": result["types"], "seconds": result["seconds"],
                "finished_utc": runs.utc_now(), "path": str(lexicon_path.relative_to(ROOT)).replace("\\", "/"),
            }
            log.info("Léxico: %d documentos, %d tokens, %d tipos en %.0fs",
                     result["docs"], result["tokens"], result["types"], result["seconds"])
        else:
            import pyarrow.compute as pc
            import pyarrow.parquet as pq

            if not gdrop_path.exists():
                raise SystemExit("Falta el léxico: ejecuta primero el subcomando lexicon")
            g = pq.read_table(gdrop_path)
            min_count = int(cfg["gdrop"]["min_ing_form_count"])
            forms = sorted(g.filter(pc.greater_equal(g["ing_form_count"], min_count))["ing_form"].to_pylist()) \
                if cfg["gdrop"]["enabled"] else []
            hash_input = {
                "annotation_version": an.ANNOTATION_VERSION, "model": cfg["model"],
                "model_version": importlib.metadata.version(cfg["model"]),
                "spacy": importlib.metadata.version("spacy"), "sentence_policy": cfg["sentence_policy"],
                "text_view": cfg["text_view"], "docs_per_task": cfg["docs_per_task"],
                "corpus_run_id": cfg["corpus_run_id"], "gdrop_forms_sha256": runs.config_hash({"f": forms}),
            }
            h = runs.config_hash(hash_input)
            out_dir = nlp_dir / args.annotation_id
            run_cfg = out_dir / "annotation_config.json"
            if run_cfg.exists() and json.loads(run_cfg.read_text(encoding="utf-8"))["hash"] != h:
                raise SystemExit(f"{out_dir} se creó con otra configuración; usa otro --annotation-id")
            runs.write_json_atomic(run_cfg, {"hash": h, **hash_input, "gdrop_forms_count": len(forms)})
            tasks = an.plan_tasks(corpus_files, out_dir, int(cfg["docs_per_task"]), h)
            workers = args.workers or int(cfg["workers"])
            entry = manifest.setdefault("annotations", {}).setdefault(args.annotation_id, {})
            entry.update({"config": hash_input, "hash": h, "gdrop_forms": len(forms), "workers": workers,
                          "status": "running", "started_utc": runs.utc_now(),
                          "path": str(out_dir.relative_to(ROOT)).replace("\\", "/")})
            runs.write_json_atomic(manifest_path, manifest)
            result = an.run_annotation(tasks, cfg["model"], forms, workers, args.max_tasks)
            entry.update(result)
            entry["finished_utc"] = runs.utc_now()
            log.info("Anotación %s: %s (%d tareas restantes)", args.annotation_id, result["status"],
                     result["tasks_remaining"])
        runs.write_json_atomic(manifest_path, manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
