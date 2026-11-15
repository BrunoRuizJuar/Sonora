#!/usr/bin/env python3
"""Agregados de frecuencia para E2 (y E3/E5) sobre el corpus canónico COMPLETO.

  .venv\\Scripts\\python.exe pipelines\\nlp\\e2_frequency.py pos-lexicon [--workers 3]
  .venv\\Scripts\\python.exe pipelines\\nlp\\e2_frequency.py vocable-candidates
  .venv\\Scripts\\python.exe pipelines\\nlp\\e2_frequency.py vocables   # aplica config/vocables_review.yaml
  .venv\\Scripts\\python.exe pipelines\\nlp\\e2_frequency.py group-unigrams [--workers 3]
  .venv\\Scripts\\python.exe pipelines\\nlp\\e2_frequency.py ngram-summary [--workers 3]
  .venv\\Scripts\\python.exe pipelines\\nlp\\e2_frequency.py lm-vocab --min-count 2
  .venv\\Scripts\\python.exe pipelines\\nlp\\e2_frequency.py lm-export [--workers 3]

Cada subcomando es reanudable (por shard) y escribe atómicamente en
data/processed/nlp/<run>/frequency/ y data/processed/nlp/<run>/lm/ (fuera de Git); el resumen
queda en manifests/nlp/<run>.json bajo "frequency". El vocabulario del modelo de lenguaje se
ajusta SOLO con train; test no se exporta.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "sonora" / "src"))

from sonora.nlp import frequency as fq  # noqa: E402
from sonora.storage import runs  # noqa: E402


def stopwords() -> set[str]:
    from spacy.lang.en.stop_words import STOP_WORDS

    return {w.lower() for w in STOP_WORDS}


def vocables() -> set[str]:
    import yaml

    cfg = yaml.safe_load((ROOT / "config" / "vocables.yaml").read_text(encoding="utf-8"))
    return set(cfg["vocables"])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("pos-lexicon", "vocable-candidates", "vocables", "group-unigrams",
                                            "ngram-summary", "lm-vocab", "lm-export"))
    parser.add_argument("--run-id", default="lyrics_full_v1")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--min-count", type=int, default=2, help="lm-vocab: frecuencia mínima en train")
    parser.add_argument("--force-unlock", action="store_true")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    (ROOT / "runtime/logs").mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout),
                                  logging.FileHandler(ROOT / "runtime/logs" / f"e2_{args.run_id}.log", encoding="utf-8")])
    log = logging.getLogger("sonora.nlp")

    nlp_dir = ROOT / "data/processed/nlp" / args.run_id
    freq_dir = nlp_dir / "frequency"
    lm_dir = nlp_dir / "lm"
    corpus = sorted((ROOT / "data/processed/lyrics" / args.run_id / "corpus").glob("*.parquet"))
    aligned = nlp_dir / "ngrams" / "aligned_splits"
    manifest_path = ROOT / "manifests/nlp" / f"{args.run_id}.json"

    with runs.run_lock(ROOT / "runtime/locks" / f"nlp_{args.run_id}.lock", force=args.force_unlock):
        if args.command == "pos-lexicon":
            result = fq.pos_lexicon(nlp_dir / "spacy_sm_v1", aligned, nlp_dir / "doc_stats", freq_dir,
                                    workers=args.workers)
        elif args.command == "vocable-candidates":
            import pyarrow.parquet as pq

            rep, uni = fq.self_repetition(nlp_dir / "ngrams" / "counts", "train")
            rows = fq.vocable_candidates(pq.read_table(freq_dir / "word_pos.parquet"), self_rep=rep,
                                         surface_counts=uni)
            out = freq_dir / "vocable_candidates.json"
            runs.write_json_atomic(out, rows)
            result = {"candidates": len(rows), "path": str(out.relative_to(ROOT)).replace("\\", "/"),
                      "rule": "train only; count>=100 and (majority INTJ or repeated syllable or elongation) "
                              "or (self-repetition share>=0.2 and count>=1000)"}
        elif args.command == "vocables":
            import yaml

            review = yaml.safe_load((ROOT / "config" / "vocables_review.yaml").read_text(encoding="utf-8"))
            cand_path = freq_dir / "vocable_candidates.json"
            cand = json.loads(cand_path.read_text(encoding="utf-8"))
            vocab = fq.select_vocables(cand, review["include"], review["exclude"])
            header = ("# GENERADO por pipelines/nlp/e2_frequency.py vocables; no editar a mano.\n"
                      "# Revisión humana en config/vocables_review.yaml; candidatos derivados SOLO de train.\n")
            payload = {"version": "vocables-v1", "derived_from": "train split of lyrics_full_v1 (spaCy POS + n-gram counts)",
                       "candidates_sha256": runs.file_sha256(cand_path),
                       "review_sha256": runs.file_sha256(ROOT / "config" / "vocables_review.yaml"),
                       "rule": review["rule"], "excluded": review["exclude"], "included_manually": review["include"],
                       "count": len(vocab), "vocables": vocab}
            runs.write_text_atomic(ROOT / "config" / "vocables.yaml",
                                   header + yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=100))
            result = {"vocables": len(vocab), "path": "config/vocables.yaml"}
        elif args.command == "group-unigrams":
            result = fq.group_unigrams(corpus, freq_dir / "group_unigrams", workers=args.workers)
        elif args.command == "ngram-summary":
            excluded = stopwords() | vocables()
            result = fq.ngram_summary(nlp_dir / "ngrams" / "counts", excluded, freq_dir / "ngram_summary.json",
                                      workers=args.workers)
        elif args.command == "lm-vocab":
            import pyarrow.compute as pc
            import pyarrow.dataset as ds

            d = ds.dataset(nlp_dir / "ngrams" / "counts")
            t = d.to_table(columns=["ngram", "count"],
                           filter=(pc.field("order") == 1) & (pc.field("split") == "train"))
            t = t.filter(pc.and_(pc.not_equal(t["ngram"], "</s>"), pc.greater_equal(t["count"], args.min_count)))
            words = sorted(t["ngram"].to_pylist())
            out = lm_dir / f"vocab_train_min{args.min_count}.txt"
            runs.write_text_atomic(out, "\n".join(words))
            covered = int(pc.sum(t["count"]).as_py())
            result = {"min_count": args.min_count, "types": len(words), "train_tokens_covered": covered,
                      "path": str(out.relative_to(ROOT)).replace("\\", "/")}
        else:
            vocab = sorted(lm_dir.glob("vocab_train_min*.txt"))
            if len(vocab) != 1:
                raise SystemExit("Se necesita exactamente un vocab_train_min*.txt (ejecuta lm-vocab)")
            result = fq.export_lm_text(corpus, aligned, lm_dir / "text", vocab[0], workers=args.workers)
            result["vocab"] = vocab[0].name
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        manifest.setdefault("frequency", {})[args.command] = {**result, "finished_utc": runs.utc_now()}
        runs.write_json_atomic(manifest_path, manifest)
    log.info("%s: %s", args.command, json.dumps({k: v for k, v in result.items() if k != "totals"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
