"""Per-lyric descriptive statistics over the FULL canonical corpus (E1-01, E1-04, E2-04).

One row per ``lyrics_id``. Text-change indicators compare the original and the structural
view (which normalizations actually fired); repetition indicators describe refrains:
a *line* is compared after casefold + whitespace collapse + stripping edge punctuation.

Memory: each worker streams one shard in batches and writes its own Parquet file
(``<out_dir>/<shard>.parquet``) batch by batch; nothing is accumulated per shard.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import re

DOC_STATS_VERSION = "doc-stats-v1"
WORD = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)*", re.UNICODE)
CURLY = re.compile("[‘’“”ʼ′‛„‟″]")
SPECIAL_SPACE = re.compile("[   -   　\t]")
ZERO_WIDTH = re.compile("[​‌‍⁠﻿­]")
EDGE_PUNCT = re.compile(r"^[\W_]+|[\W_]+$", re.UNICODE)


def line_key(line: str) -> str:
    return EDGE_PUNCT.sub("", " ".join(line.casefold().split()))


def stats_for(original: str, structural: str, analysis: str) -> dict:
    lines = [l for l in analysis.split("\n") if l.strip()]
    keys = [line_key(l) for l in lines]
    keys = [k for k in keys if k]
    counts = Counter(keys)
    words = WORD.findall(analysis.lower())
    return {
        "changed_any": original != structural,
        "had_curly_quotes": bool(CURLY.search(original)),
        "had_special_spaces": bool(SPECIAL_SPACE.search(original)),
        "had_zero_width": bool(ZERO_WIDTH.search(original)),
        "had_crlf": "\r" in original,
        "had_multi_blank_lines": "\n\n\n" in original.replace("\r\n", "\n"),
        "had_trailing_spaces": any(l != l.rstrip() for l in original.split("\n")),
        "n_words": len(words),
        "n_types": len(set(words)),
        "n_lines_nonblank": len(keys),
        "n_unique_lines": len(counts),
        "max_line_repeats": max(counts.values()) if counts else 0,
        "repeated_line_share": (1 - len(counts) / len(keys)) if keys else 0.0,
        "n_unique_words_in_repeated_lines": len({w for k, c in counts.items() if c > 1 for w in k.split()}),
    }


def schema():
    import pyarrow as pa

    return pa.schema([
        ("lyrics_id", pa.string()), ("tag", pa.string()), ("year", pa.int64()),
        ("changed_any", pa.bool_()), ("had_curly_quotes", pa.bool_()), ("had_special_spaces", pa.bool_()),
        ("had_zero_width", pa.bool_()), ("had_crlf", pa.bool_()), ("had_multi_blank_lines", pa.bool_()),
        ("had_trailing_spaces", pa.bool_()), ("n_words", pa.int32()), ("n_types", pa.int32()),
        ("n_lines_nonblank", pa.int32()), ("n_unique_lines", pa.int32()), ("max_line_repeats", pa.int32()),
        ("repeated_line_share", pa.float32()), ("n_unique_words_in_repeated_lines", pa.int32()),
    ], metadata={"version": DOC_STATS_VERSION})


def stats_file(args: tuple[str, str]) -> int:
    import pyarrow as pa
    import pyarrow.parquet as pq

    from sonora.storage.runs import ParquetStreamWriter

    path, out_path = args
    sch = schema()
    writer = ParquetStreamWriter(Path(out_path), sch)
    cols = ["lyrics_id", "tag", "year", "lyrics_original", "lyrics_structural", "lyrics_analysis"]
    try:
        for batch in pq.ParquetFile(path).iter_batches(batch_size=2000, columns=cols):
            d = batch.to_pydict()
            rows = [{"lyrics_id": d["lyrics_id"][i], "tag": d["tag"][i], "year": d["year"][i],
                     **stats_for(d["lyrics_original"][i], d["lyrics_structural"][i], d["lyrics_analysis"][i])}
                    for i in range(batch.num_rows)]
            writer.write(pa.Table.from_pylist(rows, schema=sch))
        writer.close()
    except BaseException:
        writer.abort()
        raise
    return writer.rows


def build_doc_stats(corpus_files: list[Path], out_dir: Path, workers: int = 2) -> int:
    import pyarrow.parquet as pq

    out_dir.mkdir(parents=True, exist_ok=True)
    todo = []
    total = 0
    for path in corpus_files:
        out = out_dir / path.name
        if out.exists() and pq.ParquetFile(out).metadata.num_rows == pq.ParquetFile(path).metadata.num_rows:
            total += pq.ParquetFile(out).metadata.num_rows  # already complete: resume
            continue
        todo.append((str(path), str(out)))
    with ProcessPoolExecutor(workers) as pool:
        total += sum(pool.map(stats_file, todo))
    return total
