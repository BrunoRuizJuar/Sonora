"""Memory-bounded n-gram counting over the FULL canonical corpus (E2-01, E2-02, E2-05).

Token definition = ``sonora.nlp.lexicon.WORD`` on the lower-cased analysis view.
Boundary rule: n-grams never cross a verse (line) boundary. For the language model,
train-split lines additionally produce boundary n-grams with ``<s>``/``</s>``
(two ``<s>`` pads for trigrams). Descriptive analyses filter those out.

Algorithm (map/spill/reduce):
* map: each worker streams one corpus shard, counts ``(order, split, ngram)`` in a Counter
  and spills to ``n_partitions`` Parquet partitions (by stable hash of the n-gram) whenever
  the Counter exceeds ``spill_entries``;
* reduce: each partition is aggregated independently with pyarrow ``group_by``.
Peak memory is bounded by ``spill_entries`` (map) and one partition (reduce), not by N.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import json
import logging
from pathlib import Path
import time
import zlib

from sonora.nlp.lexicon import WORD

NGRAMS_VERSION = "ngrams-lines-v1"
BOS, EOS = "<s>", "</s>"
LOG = logging.getLogger("sonora.nlp")


def line_tokens(analysis: str) -> list[list[str]]:
    return [toks for toks in (WORD.findall(line) for line in analysis.lower().split("\n")) if toks]


def count_lines(lines: list[list[str]], split: str, counter: Counter, max_order: int, lm_markers: bool) -> int:
    n_tokens = 0
    for toks in lines:
        n_tokens += len(toks)
        for order in range(1, max_order + 1):
            for i in range(len(toks) - order + 1):
                counter[(order, split, " ".join(toks[i:i + order]))] += 1
        if lm_markers:
            # boundary-only n-grams (inner ones already counted above)
            counter[(1, split, EOS)] += 1
            counter[(2, split, f"{BOS} {toks[0]}")] += 1
            counter[(2, split, f"{toks[-1]} {EOS}")] += 1
            counter[(3, split, f"{BOS} {BOS} {toks[0]}")] += 1
            if len(toks) >= 2:
                counter[(3, split, f"{BOS} {toks[0]} {toks[1]}")] += 1
                counter[(3, split, f"{toks[-2]} {toks[-1]} {EOS}")] += 1
            else:
                counter[(3, split, f"{BOS} {toks[0]} {EOS}")] += 1
    return n_tokens


def partition_of(ngram: str, n_partitions: int) -> int:
    return zlib.crc32(ngram.encode("utf-8")) % n_partitions


def _spill(counter: Counter, spill_dir: Path, tag: str, seq: int, n_partitions: int) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    buckets: dict[int, tuple[list, list, list, list]] = {}
    for (order, split, ngram), c in counter.items():
        b = buckets.setdefault(partition_of(ngram, n_partitions), ([], [], [], []))
        b[0].append(order); b[1].append(split); b[2].append(ngram); b[3].append(c)
    for p, (orders, splits, grams, counts) in buckets.items():
        path = spill_dir / f"p={p:03d}" / f"{tag}-{seq:04d}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        table = pa.table({"order": pa.array(orders, pa.int8()), "split": pa.array(splits, pa.string()),
                          "ngram": pa.array(grams, pa.string()), "count": pa.array(counts, pa.int64())})
        tmp = path.with_name(path.name + ".tmp")
        pq.write_table(table, tmp, compression="zstd")
        tmp.replace(path)
    counter.clear()


def map_shard(args: tuple) -> dict:
    """Count one corpus shard; returns token/line totals. Idempotent via a done-marker."""
    import pyarrow.parquet as pq

    corpus_file, split_file, spill_dir, max_order, spill_entries, n_partitions = args
    spill_dir = Path(spill_dir)
    tag = Path(corpus_file).stem
    done = spill_dir / "_done" / f"{tag}.json"
    if done.exists():
        return json.loads(done.read_text(encoding="utf-8"))
    for stale in spill_dir.glob(f"p=*/{tag}-*.parquet*"):
        stale.unlink()  # partial output of an interrupted map of this shard
    splits = pq.read_table(split_file, columns=["split"])["split"].to_pylist()
    counter: Counter = Counter()
    seq = 0
    totals: dict[str, dict[str, int]] = {}
    row = 0
    for batch in pq.ParquetFile(corpus_file).iter_batches(batch_size=1000, columns=["lyrics_analysis"]):
        for text in batch.column(0).to_pylist():
            split = splits[row]
            row += 1
            lines = line_tokens(text)
            n = count_lines(lines, split, counter, max_order, lm_markers=(split == "train"))
            t = totals.setdefault(split, {"docs": 0, "lines": 0, "tokens": 0})
            t["docs"] += 1; t["lines"] += len(lines); t["tokens"] += n
        if len(counter) >= spill_entries:
            _spill(counter, spill_dir, tag, seq, n_partitions); seq += 1
    if counter:
        _spill(counter, spill_dir, tag, seq, n_partitions)
    if row != len(splits):
        raise RuntimeError(f"{tag}: {row} letras leídas y {len(splits)} splits alineados")
    result = {"shard": tag, "totals": totals}
    done.parent.mkdir(parents=True, exist_ok=True)
    done.write_text(json.dumps(result), encoding="utf-8")
    return result


def reduce_partition(args: tuple) -> dict:
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.dataset as ds
    import pyarrow.parquet as pq

    part_dir, out_dir = Path(args[0]), Path(args[1])
    out = out_dir / f"{part_dir.name}.parquet"
    if out.exists():
        t = pq.read_table(out, columns=["order"])
        return {"partition": part_dir.name, "rows": t.num_rows, "skipped": True}
    table = ds.dataset(sorted(str(p) for p in part_dir.glob("*.parquet")), format="parquet").to_table()
    agg = table.group_by(["order", "split", "ngram"]).aggregate([("count", "sum")]).rename_columns(
        ["order", "split", "ngram", "count"])
    agg = agg.sort_by([("order", "ascending"), ("ngram", "ascending"), ("split", "ascending")])
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    pq.write_table(agg, tmp, compression="zstd")
    tmp.replace(out)
    return {"partition": part_dir.name, "rows": agg.num_rows, "skipped": False}


def write_aligned_splits(corpus_files: list[Path], splits_path: Path, out_dir: Path) -> list[Path]:
    """One small file per corpus shard with the split of each row, in row order."""
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    splits = pq.read_table(splits_path, columns=["lyrics_id", "split"])
    out = []
    for f in corpus_files:
        target = out_dir / f.name
        out.append(target)
        if target.exists() and pq.ParquetFile(target).metadata.num_rows == pq.ParquetFile(f).metadata.num_rows:
            continue
        ids = pq.read_table(f, columns=["lyrics_id"])["lyrics_id"]
        pos = pc.index_in(ids, value_set=splits["lyrics_id"])
        if pc.sum(pc.is_null(pos)).as_py():
            raise RuntimeError(f"{f.name}: letras sin split")
        aligned = pa.table({"lyrics_id": ids, "split": splits["split"].take(pos)})
        target.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(aligned, target)
    return out


def count_corpus(corpus_files: list[Path], splits_path: Path, work_dir: Path, max_order: int = 3,
                 workers: int = 2, spill_entries: int = 3_000_000, n_partitions: int = 256) -> dict:
    started = time.time()
    split_files = write_aligned_splits(corpus_files, splits_path, work_dir / "aligned_splits")
    spill_dir = work_dir / "spill"
    tasks = [(str(c), str(s), str(spill_dir), max_order, spill_entries, n_partitions)
             for c, s in zip(corpus_files, split_files)]
    totals: dict[str, dict[str, int]] = {}
    with ProcessPoolExecutor(workers) as pool:
        for result in pool.map(map_shard, tasks):
            LOG.info("n-gramas map %s: %s", result["shard"], result["totals"])
            for split, t in result["totals"].items():
                agg = totals.setdefault(split, {"docs": 0, "lines": 0, "tokens": 0})
                for k, v in t.items():
                    agg[k] += v
    map_seconds = time.time() - started
    parts = sorted(p for p in spill_dir.glob("p=*") if p.is_dir())
    out_dir = work_dir / "counts"
    rows = 0
    with ProcessPoolExecutor(workers) as pool:
        for r in pool.map(reduce_partition, [(str(p), str(out_dir)) for p in parts]):
            rows += r["rows"]
    summary = {"version": NGRAMS_VERSION, "max_order": max_order, "partitions": len(parts),
               "rows": rows, "totals_by_split": totals, "map_seconds": round(map_seconds, 1),
               "seconds": round(time.time() - started, 1), "spill_entries": spill_entries,
               "boundary_rule": "within verse line; <s> <s> ... </s> markers only for train-split LM counts"}
    (work_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
