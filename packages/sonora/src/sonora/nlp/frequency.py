"""Corpus-wide frequency aggregates for E2 (and reusable by E3/E5), memory-bounded.

Three passes, each resumable per shard and never holding the corpus in memory:

* ``pos_lexicon``: from the spaCy annotation, counts of ``(split, lower, lemma, upos)`` and of
  ``(split, tag, decade, upos)``. Used to derive vocables (majority ``INTJ`` in *train*) and
  for E3 denominators.
* ``group_unigrams``: regex-token unigram counts (``sonora.nlp.lexicon.WORD``, lower-cased
  analysis view, same tokens as the n-gram counts) by source ``tag`` and by ``decade``.
* ``ngram_summary``: per n-gram order, reads the 256 reduced count partitions one at a time
  (an n-gram always lives in a single partition) and keeps global totals, the frequency
  spectrum, the top-K overall and the top-K after removing stopwords/vocables.

All counts are over the FULL canonical corpus unless a split is named explicitly.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import heapq
import json
import logging
from pathlib import Path
import re
import time

from sonora.nlp.lexicon import WORD

FREQUENCY_VERSION = "frequency-v1"
LOG = logging.getLogger("sonora.nlp")
MARKERS = ("<s>", "</s>")
# Non-lexical syllable patterns: a short syllable repeated (nana, lalala, dumdum) or a
# letter stretched three or more times (ooooh, yeahhh, nooo).
REPEATED_SYLLABLE = re.compile(r"^([a-z]{1,3}?)\1+$")
ELONGATED = re.compile(r"([a-z])\1\1")


def decade_of(year) -> int | None:
    if year is None or year < 1900 or year > 2022:
        return None
    return int(year) // 10 * 10


# --------------------------------------------------------------------------- POS lexicon

def _shard_pos_counts(args: tuple) -> dict:
    """Aggregate one annotation shard; writes two Parquet files atomically."""
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    from sonora.storage.runs import write_parquet_atomic

    token_dir, aligned_split_file, doc_stats_file, out_dir = map(Path, args)
    shard = token_dir.name
    out_words = out_dir / "word_pos" / f"{shard}.parquet"
    out_groups = out_dir / "group_pos" / f"{shard}.parquet"
    if out_words.exists() and out_groups.exists():
        return {"shard": shard, "skipped": True}
    aligned = pq.read_table(aligned_split_file, columns=["lyrics_id", "split"])
    meta = pq.read_table(doc_stats_file, columns=["lyrics_id", "tag", "year"])
    if aligned.num_rows != meta.num_rows or aligned["lyrics_id"] != meta["lyrics_id"]:
        raise RuntimeError(f"{shard}: splits y doc_stats no están alineados")
    decade = pa.array([decade_of(y) for y in meta["year"].to_pylist()], pa.int16())
    keys = ["split", "lower", "lemma", "upos"]
    acc: list = []
    groups: Counter = Counter()
    tokens = 0
    parts = sorted(token_dir.glob("part-*.parquet"))
    for i, part in enumerate(parts):
        pf = pq.ParquetFile(part)
        start, end = map(int, pf.schema_arrow.metadata[b"sonora_range"].decode().split(":"))
        t = pf.read(columns=["lyrics_id", "lower", "lemma", "upos"])
        doc_ids = aligned["lyrics_id"].slice(start, end - start)
        # corpus row of each token's document (the part covers corpus rows [start, end))
        pos = pc.index_in(t["lyrics_id"].cast(pa.string()), value_set=doc_ids)
        if pc.sum(pc.is_null(pos)).as_py():
            raise RuntimeError(f"{part}: lyrics_id fuera del rango {start}:{end}")
        row = pc.add(pos, start)
        tbl = pa.table({
            "split": aligned["split"].take(row),
            "lower": t["lower"].cast(pa.string()), "lemma": t["lemma"].cast(pa.string()),
            "upos": t["upos"].cast(pa.string()),
        })
        acc.append(tbl.group_by(keys).aggregate([([], "count_all")]).rename_columns(keys + ["count"]))
        g = pa.table({"split": tbl["split"], "tag": meta["tag"].take(row), "decade": decade.take(row),
                      "upos": tbl["upos"]})
        for r in g.group_by(["split", "tag", "decade", "upos"]).aggregate([([], "count_all")]).to_pylist():
            groups[(r["split"], r["tag"], r["decade"], r["upos"])] += r["count_all"]
        tokens += tbl.num_rows
        if len(acc) >= 40 or i == len(parts) - 1:
            merged = pa.concat_tables(acc)
            acc = [merged.group_by(keys).aggregate([("count", "sum")]).rename_columns(keys + ["count"])]
    words = acc[0] if acc else pa.table({k: pa.array([], pa.string()) for k in keys} | {"count": pa.array([], pa.int64())})
    if int(pc.sum(words["count"]).as_py() or 0) != tokens:
        raise RuntimeError(f"{shard}: conteo POS no reconcilia")
    g_rows = [{"split": s, "tag": tg, "decade": d, "upos": u, "count": c} for (s, tg, d, u), c in groups.items()]
    gtable = pa.Table.from_pylist(g_rows, schema=pa.schema([("split", pa.string()), ("tag", pa.string()),
                                                            ("decade", pa.int16()), ("upos", pa.string()),
                                                            ("count", pa.int64())]))
    write_parquet_atomic(gtable, out_groups)
    write_parquet_atomic(words, out_words)  # written last: marks the shard as done
    return {"shard": shard, "skipped": False, "tokens": tokens, "parts": len(parts)}


def pos_lexicon(annotation_dir: Path, aligned_dir: Path, doc_stats_dir: Path, out_dir: Path,
                workers: int = 2) -> dict:
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.dataset as ds

    from sonora.storage.runs import write_parquet_atomic

    t0 = time.time()
    shards = sorted(p for p in (annotation_dir / "tokens").iterdir() if p.is_dir())
    tasks = [(str(s), str(aligned_dir / f"{s.name}.parquet"), str(doc_stats_dir / f"{s.name}.parquet"),
              str(out_dir / "shards")) for s in shards]
    with ProcessPoolExecutor(workers) as pool:
        for r in pool.map(_shard_pos_counts, tasks):
            LOG.info("POS léxico %s", r)
    keys = ["split", "lower", "lemma", "upos"]
    words = ds.dataset(out_dir / "shards" / "word_pos").to_table()
    words = words.group_by(keys).aggregate([("count", "sum")]).rename_columns(keys + ["count"])
    write_parquet_atomic(words.sort_by([("count", "descending")]), out_dir / "word_pos.parquet")
    gk = ["split", "tag", "decade", "upos"]
    groups = ds.dataset(out_dir / "shards" / "group_pos").to_table()
    groups = groups.group_by(gk).aggregate([("count", "sum")]).rename_columns(gk + ["count"])
    write_parquet_atomic(groups, out_dir / "group_pos.parquet")
    total = int(pc.sum(words["count"]).as_py())
    return {"version": FREQUENCY_VERSION, "tokens": total, "rows": words.num_rows,
            "group_rows": groups.num_rows, "seconds": round(time.time() - t0, 1),
            "path": "word_pos.parquet, group_pos.parquet"}


# --------------------------------------------------------------------------- vocables

def vocable_candidates(word_pos, min_count: int = 100, split: str = "train",
                       self_rep: dict[str, float] | None = None, self_rep_min: float = 0.2,
                       self_rep_min_count: int = 1000, surface_counts: dict[str, int] | None = None) -> list[dict]:
    """Data-driven vocable candidates from the annotation of ``split`` (train by default).

    A lower-cased form qualifies if (a) its majority UPOS is INTJ, or (b) it is a repeated
    short syllable or an elongation (``ooooh``), or (c) at least ``self_rep_min`` of its
    occurrences are followed by itself inside the verse (bigram ``w w``; ``na na``), with
    ``self_rep_min_count`` occurrences. Forms with internal apostrophes/digits are excluded.
    If ``surface_counts`` (regex-token counts of the same split) is given, thresholds and the
    reported ``count`` use it: spaCy splits ``gonna``/``ain't`` into ``gon na``/``ai n't``, which
    would otherwise inflate fragments such as ``na``. Rows are sorted by frequency; the final list
    is reviewed and versioned.
    """
    import pyarrow.compute as pc

    t = word_pos.filter(pc.equal(word_pos["split"], split))
    by_form: dict[str, Counter] = {}
    for lower, upos, c in zip(t["lower"].to_pylist(), t["upos"].to_pylist(), t["count"].to_pylist()):
        by_form.setdefault(lower, Counter())[upos] += c
    out = []
    for form, pos in by_form.items():
        spacy_total = sum(pos.values())
        total = spacy_total if surface_counts is None else surface_counts.get(form, 0)
        if total < min_count or not form.isalpha() or not form.isascii():
            continue
        top, top_c = pos.most_common(1)[0]
        reasons = []
        if top == "INTJ":
            reasons.append("intj_majority")
        if REPEATED_SYLLABLE.match(form) and re.search("[aeiouy]", form):
            reasons.append("repeated_syllable")
        if ELONGATED.search(form):
            reasons.append("elongated")
        share = (self_rep or {}).get(form, 0.0)
        if share >= self_rep_min and total >= self_rep_min_count:
            reasons.append("self_repetition")
        if reasons:
            out.append({"form": form, "count": total, "majority_upos": top,
                        "spacy_count": spacy_total, "intj_share": round(pos.get("INTJ", 0) / spacy_total, 4),
                        "self_rep": round(share, 4), "reasons": reasons})
    return sorted(out, key=lambda r: -r["count"])


def self_repetition(counts_dir: Path, split: str = "train") -> tuple[dict[str, float], dict[str, int]]:
    """Share of each word's occurrences followed by the same word in the verse (``w w``), and
    the regex unigram counts of ``split``."""
    import pyarrow.compute as pc
    import pyarrow.dataset as ds

    uni: dict[str, int] = {}
    same: Counter = Counter()
    d = ds.dataset(counts_dir)
    scanner = d.scanner(columns=["order", "ngram", "count"], batch_size=1 << 20,
                        filter=(pc.field("split") == split) & (pc.field("order") <= 2))
    for b in scanner.to_batches():
        for o, g, c in zip(b.column(0).to_pylist(), b.column(1).to_pylist(), b.column(2).to_pylist()):
            if o == 1:
                uni[g] = c
            else:
                a, _, z = g.partition(" ")
                if a == z:
                    same[a] += c
    uni.pop("</s>", None)
    return {w: same[w] / uni[w] for w in same if uni.get(w)}, uni


def reductions(form: str) -> set[str]:
    """Forms obtained by collapsing letter runs (``ooooh`` -> ``oh``, ``ooh``) or taking the
    repeated unit (``nanana`` -> ``na``)."""
    out = {re.sub(r"(.)\1{2,}", r"\1", form), re.sub(r"(.)\1{2,}", r"\1\1", form), re.sub(r"(.)\1+", r"\1", form)}
    m = REPEATED_SYLLABLE.match(form)
    if m:
        out.update({m.group(1), m.group(1) * 2})  # nanana -> na; hehehe -> hehe
    out.discard(form)
    return out


def select_vocables(candidates: list[dict], include: dict[str, str], exclude: dict[str, str]) -> list[str]:
    """Final vocable list (deterministic given the reviewed include/exclude maps).

    Base = candidates with ``intj_majority`` or ``self_repetition`` (minus ``exclude``) plus
    ``include``. Pattern-only candidates (repeated syllable / elongation) are accepted only if
    one of their :func:`reductions` belongs to the base: ``yeahhh`` -> ``yeah`` is a vocable,
    ``nooo`` -> ``no`` and ``mama`` -> ``ma`` are not.
    """
    base = {c["form"] for c in candidates
            if {"intj_majority", "self_repetition"} & set(c["reasons"]) and c["form"] not in exclude}
    base |= set(include)
    derived = {c["form"] for c in candidates if c["form"] not in base and c["form"] not in exclude
               and reductions(c["form"]) & base}
    return sorted(base | derived)


# --------------------------------------------------------------------------- unigrams by group

def _group_unigrams_file(args: tuple) -> dict:
    import pyarrow as pa
    import pyarrow.parquet as pq

    from sonora.storage.runs import write_parquet_atomic

    corpus_file, out_path = Path(args[0]), Path(args[1])
    if out_path.exists():
        return {"shard": corpus_file.stem, "skipped": True}
    counts: Counter = Counter()
    docs: Counter = Counter()
    for batch in pq.ParquetFile(corpus_file).iter_batches(batch_size=2000, columns=["tag", "year", "lyrics_analysis"]):
        d = batch.to_pydict()
        for tag, year, text in zip(d["tag"], d["year"], d["lyrics_analysis"]):
            words = Counter(WORD.findall(text.lower()))
            dec = decade_of(year)
            groups = [("tag", str(tag))] + ([("decade", str(dec))] if dec is not None else [])
            for kind, value in groups:
                docs[(kind, value)] += 1
                for w, c in words.items():
                    counts[(kind, value, w)] += c
    kinds, values, ws, cs = zip(*((k, v, w, c) for (k, v, w), c in counts.items())) if counts else ((), (), (), ())
    table = pa.table({"kind": pa.array(kinds, pa.string()), "group": pa.array(values, pa.string()),
                      "word": pa.array(ws, pa.string()), "count": pa.array(cs, pa.int64())})
    write_parquet_atomic(table, out_path)
    return {"shard": corpus_file.stem, "skipped": False, "docs": {f"{k}={v}": n for (k, v), n in docs.items()}}


def group_unigrams(corpus_files: list[Path], out_dir: Path, workers: int = 2) -> dict:
    import pyarrow.compute as pc
    import pyarrow.dataset as ds

    from sonora.storage.runs import write_parquet_atomic

    t0 = time.time()
    tasks = [(str(f), str(out_dir / "shards" / f.name)) for f in corpus_files]
    with ProcessPoolExecutor(workers) as pool:
        for r in pool.map(_group_unigrams_file, tasks):
            LOG.info("unigramas por grupo %s", r.get("shard"))
    keys = ["kind", "group", "word"]
    t = ds.dataset(out_dir / "shards").to_table()
    t = t.group_by(keys).aggregate([("count", "sum")]).rename_columns(keys + ["count"])
    write_parquet_atomic(t, out_dir / "group_unigrams.parquet")
    tag_total = int(pc.sum(t.filter(pc.equal(t["kind"], "tag"))["count"]).as_py())
    return {"version": FREQUENCY_VERSION, "rows": t.num_rows, "tokens_by_tag_total": tag_total,
            "seconds": round(time.time() - t0, 1)}


# --------------------------------------------------------------------------- n-gram summary

def _partition_summary(args: tuple) -> dict:
    import numpy as np
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    path, top_k, excluded = Path(args[0]), int(args[1]), frozenset(args[2])
    t = pq.read_table(path)
    out: dict = {}
    for order in (1, 2, 3):
        o = t.filter(pc.equal(t["order"], order))
        res: dict = {}
        for scope in ("all", "train", "validation", "test"):
            s = o if scope == "all" else o.filter(pc.equal(o["split"], scope))
            agg = s.group_by(["ngram"]).aggregate([("count", "sum")])
            grams = agg["ngram"].to_pylist()
            counts = agg["count_sum"].to_numpy()
            keep = np.array([not any(m in g for m in MARKERS) for g in grams], dtype=bool) if len(grams) else np.zeros(0, bool)
            grams = [g for g, k in zip(grams, keep) if k]
            counts = counts[keep]
            spec = Counter(counts[counts <= 1000].tolist())
            r = {"tokens": int(counts.sum()), "types": int(len(counts)), "spectrum_le1000": dict(spec)}
            if scope == "all":
                idx = np.argsort(-counts, kind="stable")[:top_k]
                r["top"] = [(grams[i], int(counts[i])) for i in idx]
                content = [i for i in np.argsort(-counts, kind="stable")
                           if not any(w in excluded for w in grams[i].split())][:top_k]
                r["top_content"] = [(grams[i], int(counts[i])) for i in content]
                r["counts_gt1000"] = counts[counts > 1000].tolist()
            res[scope] = r
        out[order] = res
    return out


def ngram_summary(counts_dir: Path, excluded_words: set[str], out_path: Path, top_k: int = 2000,
                  workers: int = 2) -> dict:
    """Global n-gram statistics; descriptive (marker n-grams ``<s>``/``</s>`` removed)."""
    t0 = time.time()
    parts = sorted(counts_dir.glob("p=*.parquet"))
    summary: dict = {}
    tops: dict = {}
    with ProcessPoolExecutor(workers) as pool:
        for res in pool.map(_partition_summary, [(str(p), top_k, sorted(excluded_words)) for p in parts]):
            for order, scopes in res.items():
                for scope, r in scopes.items():
                    s = summary.setdefault(str(order), {}).setdefault(scope, {"tokens": 0, "types": 0, "spectrum_le1000": Counter()})
                    s["tokens"] += r["tokens"]; s["types"] += r["types"]
                    s["spectrum_le1000"].update(r["spectrum_le1000"])
                    if scope == "all":
                        tt = tops.setdefault(order, {"top": [], "top_content": [], "counts_gt1000": []})
                        tt["top"] = heapq.nlargest(top_k, tt["top"] + r["top"], key=lambda x: x[1])
                        tt["top_content"] = heapq.nlargest(top_k, tt["top_content"] + r["top_content"], key=lambda x: x[1])
                        tt["counts_gt1000"].extend(r["counts_gt1000"])
    for order, tt in tops.items():
        s = summary[str(order)]["all"]
        s["top"] = tt["top"]; s["top_content"] = tt["top_content"]
        s["counts_gt1000"] = sorted(tt["counts_gt1000"], reverse=True)
    for order in summary.values():
        for s in order.values():
            s["spectrum_le1000"] = {str(k): v for k, v in sorted(s["spectrum_le1000"].items())}
    payload = {"version": FREQUENCY_VERSION, "partitions": len(parts), "top_k": top_k,
               "excluded_words": len(excluded_words), "seconds": round(time.time() - t0, 1),
               "note": "descriptive: n-grams with <s>/</s> removed; within-verse n-grams only",
               "orders": summary}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(out_path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp.replace(out_path)
    return {k: v for k, v in payload.items() if k != "orders"}


# --------------------------------------------------------------------------- LM text export

def _export_lm_file(args: tuple) -> dict:
    import pyarrow.parquet as pq

    from sonora.nlp.ngrams import line_tokens

    corpus_file, split_file, out_dir, vocab_path, splits = args
    out_dir = Path(out_dir)
    stem = Path(corpus_file).stem
    done = out_dir / "_done" / f"{stem}.json"
    if done.exists():
        return json.loads(done.read_text(encoding="utf-8"))
    vocab = frozenset(Path(vocab_path).read_text(encoding="utf-8").split("\n")) if vocab_path else None
    split_of = pq.read_table(split_file, columns=["split"])["split"].to_pylist()
    handles, stats = {}, {}
    row = 0
    try:
        for batch in pq.ParquetFile(corpus_file).iter_batches(batch_size=2000, columns=["tag", "lyrics_analysis"]):
            d = batch.to_pydict()
            for tag, text in zip(d["tag"], d["lyrics_analysis"]):
                split = split_of[row]; row += 1
                if split not in splits:
                    continue
                key = split if split == "train" else f"{split}.{tag}"
                if key not in handles:
                    p = out_dir / "shards" / f"{key}.{stem}.txt.tmp"
                    p.parent.mkdir(parents=True, exist_ok=True)
                    handles[key] = p.open("w", encoding="utf-8", newline="\n")
                st = stats.setdefault(key, {"docs": 0, "lines": 0, "tokens": 0, "mapped_oov": 0})
                st["docs"] += 1
                for toks in line_tokens(text):
                    if vocab is not None:
                        mapped = [w if w in vocab else "<oov>" for w in toks]
                        st["mapped_oov"] += sum(1 for w in mapped if w == "<oov>")
                        toks = mapped
                    handles[key].write(" ".join(toks) + "\n")
                    st["lines"] += 1; st["tokens"] += len(toks)
    finally:
        for h in handles.values():
            h.close()
    for key in handles:
        tmp = out_dir / "shards" / f"{key}.{stem}.txt.tmp"
        tmp.replace(tmp.with_suffix(""))
    result = {"shard": stem, "stats": stats}
    done.parent.mkdir(parents=True, exist_ok=True)
    done.write_text(json.dumps(result), encoding="utf-8")
    return result


def export_lm_text(corpus_files: list[Path], aligned_dir: Path, out_dir: Path, vocab_path: Path | None,
                   splits=("train", "validation"), workers: int = 2) -> dict:
    """Write one verse per line (regex tokens, lower-cased, rare words -> ``<oov>``).

    Train goes to ``train.<shard>.txt``; validation/test are split by ``tag`` so perplexity
    can be reported per source tag. Test is NOT exported unless requested explicitly.
    """
    t0 = time.time()
    tasks = [(str(f), str(aligned_dir / f.name), str(out_dir), str(vocab_path) if vocab_path else None,
              tuple(splits)) for f in corpus_files]
    totals: dict = {}
    with ProcessPoolExecutor(workers) as pool:
        for r in pool.map(_export_lm_file, tasks):
            for key, st in r["stats"].items():
                agg = totals.setdefault(key, Counter())
                agg.update(st)
            LOG.info("export LM %s", r["shard"])
    return {"totals": {k: dict(v) for k, v in sorted(totals.items())}, "seconds": round(time.time() - t0, 1)}
