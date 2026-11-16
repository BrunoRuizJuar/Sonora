#!/usr/bin/env python3
"""E2-05 - modelo de lenguaje de n-gramas con KenLM (Kneser-Ney modificado) en WSL.

  .venv\\Scripts\\python.exe pipelines\\nlp\\ngram_lm.py check
  .venv\\Scripts\\python.exe pipelines\\nlp\\ngram_lm.py train --order 3 [--memory 40%]
  .venv\\Scripts\\python.exe pipelines\\nlp\\ngram_lm.py eval --order 3

Entrada: data/processed/nlp/<run>/lm/text/shards/ (e2_frequency.py lm-export): un verso por
línea, tokens regex en minúsculas, palabras con frecuencia < min_count en train -> <oov>
(vocabulario cerrado ajustado SOLO con train). lmplz añade <s> y </s> a cada verso.
El ARPA y el binario quedan en WSL (~/sonora_lm/<run>/), fuera del repositorio; los resultados
en data/processed/nlp/<run>/lm/results.json y manifests/nlp/<run>.json ("ngram_lm").
`eval` sólo acepta validation: test queda reservado para la evaluación final.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "sonora" / "src"))

from sonora.storage import runs  # noqa: E402

DISTRO = "Ubuntu-24.04"
BIN = "$HOME/opt/kenlm/build/bin"
TAGS = ("pop", "rap", "rock", "rb", "country")


def wsl(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run(["wsl", "-d", DISTRO, "--", "bash", "-lc", cmd], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        raise SystemExit(f"Falló en WSL ({p.returncode}): {cmd}\n{p.stdout[-2000:]}\n{p.stderr[-4000:]}")
    return p


def wsl_path(path: Path) -> str:
    return wsl(f"wslpath -a '{path}'").stdout.strip()


def parse_query(text: str) -> dict:
    out = {}
    for key, pat in (("ppl_incl_oov", r"Perplexity including OOVs:\s*([\d.einf+-]+)"),
                     ("ppl_excl_oov", r"Perplexity excluding OOVs:\s*([\d.einf+-]+)"),
                     ("kenlm_oovs", r"^OOVs:\s*(\d+)"), ("tokens_incl_eos", r"^Tokens:\s*(\d+)")):
        m = re.search(pat, text, re.M)
        out[key] = (float(m.group(1)) if "ppl" in key else int(m.group(1))) if m else None
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("check", "train", "eval"))
    parser.add_argument("--run-id", default="lyrics_full_v1")
    parser.add_argument("--order", type=int, default=3)
    parser.add_argument("--memory", default="40%", help="lmplz -S (memoria de ordenamiento dentro de WSL)")
    parser.add_argument("--keep-arpa", action="store_true")
    parser.add_argument("--force-unlock", action="store_true")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    lm_dir = ROOT / "data/processed/nlp" / args.run_id / "lm"
    text = wsl_path(lm_dir / "text" / "shards")
    work = f"$HOME/sonora_lm/{args.run_id}"
    model = f"{work}/o{args.order}.binary"
    results_path = lm_dir / "results.json"
    manifest_path = ROOT / "manifests/nlp" / f"{args.run_id}.json"

    if args.command == "check":
        p = wsl(f"ls {BIN}/lmplz {BIN}/build_binary {BIN}/query && cat $HOME/opt/kenlm/SONORA_COMMIT; "
                f"ls {text} | sed -e 's/\\.[^.]*\\.txt$//' | sort | uniq -c; df -h $HOME | tail -1; free -g", check=False)
        print(p.stdout, p.stderr)
        return p.returncode

    with runs.run_lock(ROOT / "runtime/locks" / f"nlp_{args.run_id}.lock", force=args.force_unlock):
        results = json.loads(results_path.read_text(encoding="utf-8")) if results_path.exists() else {}
        entry = results.setdefault(f"o{args.order}", {})
        if args.command == "train":
            t0 = time.time()
            arpa = f"{work}/o{args.order}.arpa"
            wsl(f"set -euo pipefail; mkdir -p {work}/tmp; cat {text}/train.*.txt | "
                f"{BIN}/lmplz -o {args.order} -S {args.memory} -T {work}/tmp > {arpa}.tmp 2> {work}/o{args.order}.lmplz.log; "
                f"mv {arpa}.tmp {arpa}")
            header = wsl(f"head -n {args.order + 3} {arpa}").stdout
            counts = {f"{m.group(1)}-gram": int(m.group(2)) for m in re.finditer(r"ngram (\d+)=(\d+)", header)}
            t1 = time.time()
            wsl(f"set -euo pipefail; {BIN}/build_binary trie {arpa} {model}.tmp > {work}/o{args.order}.build.log 2>&1; "
                f"mv {model}.tmp {model}")
            sizes = wsl(f"stat -c '%n %s' {arpa} {model}").stdout.split("\n")
            if not args.keep_arpa:
                wsl(f"rm -f {arpa}")
            commit = wsl("cat $HOME/opt/kenlm/SONORA_COMMIT").stdout.strip()
            entry["train"] = {"order": args.order, "smoothing": "interpolated modified Kneser-Ney (lmplz defaults)",
                              "pruning": "none", "ngram_counts": counts, "kenlm_commit": commit,
                              "lmplz_seconds": round(t1 - t0, 1), "build_binary_seconds": round(time.time() - t1, 1),
                              "files_bytes": {Path(s.split()[0]).name: int(s.split()[1]) for s in sizes if s.strip()},
                              "model_path_wsl": model, "input": "train.*.txt (verses, <oov> for train count < min_count)",
                              "finished_utc": runs.utc_now()}
        else:
            evals = {}
            for name, pattern in [("validation", "validation.*.txt")] + [(f"validation.{t}", f"validation.{t}.*.txt") for t in TAGS]:
                p = wsl(f"set -euo pipefail; cat {text}/{pattern} | {BIN}/query -v summary {model}")
                evals[name] = parse_query(p.stdout + p.stderr)
                print(name, evals[name])
            # hand-written illustrative sentences (not corpus data); same tokenization as export
            sentences = ["i love you", "you love i", "i love you baby", "love baby i you",
                         "na na na na", "the of and to", "i can't stop thinking about you",
                         "you about thinking stop can't i"]
            ex_file = lm_dir / "examples.txt"
            runs.write_text_atomic(ex_file, "\n".join(sentences) + "\n")
            p = wsl(f"{BIN}/query {model} < {wsl_path(ex_file)} 2>/dev/null")
            totals = [float(m.group(1)) for m in re.finditer(r"Total:\s*(-?[\d.]+)", p.stdout)]
            entry["examples"] = [{"sentence": s, "total_log10": t} for s, t in zip(sentences, totals)]
            entry["eval"] = {**evals, "note": "perplexity per token incl. </s>; <oov> is an in-vocabulary class",
                             "finished_utc": runs.utc_now()}
        runs.write_json_atomic(results_path, results)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        manifest["ngram_lm"] = {"results": str(results_path.relative_to(ROOT)).replace("\\", "/"),
                                **{k: {kk: vv for kk, vv in v.items()} for k, v in results.items()}}
        runs.write_json_atomic(manifest_path, manifest)
        print(json.dumps(entry, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
