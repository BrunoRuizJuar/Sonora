"""Corpus-wide surface lexicon (regex word tokens) over the canonical analysis view.

Used for E1/E2 descriptive statistics and as a data-driven guard for the g-dropping
normalization of the annotation stage (``runnin'`` -> ``running`` only when ``running``
is attested in the corpus). The token definition is deliberately simple and documented:
maximal runs of Unicode letters with internal apostrophes (``don't``, ``y'all``),
lower-cased; digits and punctuation are not words. This is NOT the spaCy tokenization.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import logging
from pathlib import Path
import re
import time

LEXICON_VERSION = "regex-words-v1"
WORD = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)*", re.UNICODE)
GDROP_SURFACE = re.compile(r"(?<![^\W\d_'])([^\W\d_]{2,}?in)'(?![^\W\d_])", re.UNICODE)
LOG = logging.getLogger("sonora.nlp")


def count_file(path: str, batch_size: int = 5000) -> tuple[Counter, Counter, Counter, int, int]:
    """Return (token counts, document frequencies, g-dropped surface counts, docs, tokens)."""
    import pyarrow.parquet as pq

    counts: Counter = Counter()
    doc_freq: Counter = Counter()
    gdrop: Counter = Counter()
    docs = tokens = 0
    parquet = pq.ParquetFile(path)
    for batch in parquet.iter_batches(batch_size=batch_size, columns=["lyrics_analysis"]):
        for text in batch.column(0).to_pylist():
            words = WORD.findall(text.lower())
            counts.update(words)
            doc_freq.update(set(words))
            gdrop.update(m.group(1) for m in GDROP_SURFACE.finditer(text.lower()))
            docs += 1
            tokens += len(words)
    return counts, doc_freq, gdrop, docs, tokens


def build_lexicon(corpus_files: list[Path], workers: int = 5) -> dict:
    import pyarrow as pa

    started = time.time()
    total, dfreq, gdrop = Counter(), Counter(), Counter()
    docs = tokens = 0
    with ProcessPoolExecutor(workers) as pool:
        for path, (c, d, g, n_docs, n_tok) in zip(corpus_files, pool.map(count_file, map(str, corpus_files))):
            total.update(c)
            dfreq.update(d)
            gdrop.update(g)
            docs += n_docs
            tokens += n_tok
            LOG.info("Léxico %s: %d documentos, %d tokens", Path(path).name, n_docs, n_tok)
    words = sorted(total, key=lambda w: (-total[w], w))
    table = pa.table({
        "word": words,
        "count": pa.array([total[w] for w in words], pa.int64()),
        "doc_freq": pa.array([dfreq[w] for w in words], pa.int64()),
    })
    g_words = sorted(gdrop, key=lambda w: (-gdrop[w], w))
    gtable = pa.table({
        "surface_stem": g_words,  # e.g. "runnin" for "runnin'"
        "count": pa.array([gdrop[w] for w in g_words], pa.int64()),
        "ing_form": [w[:-2] + "ing" for w in g_words],
        "ing_form_count": pa.array([total.get(w[:-2] + "ing", 0) for w in g_words], pa.int64()),
    })
    return {"lexicon": table, "gdrop": gtable, "docs": docs, "tokens": tokens,
            "types": len(words), "seconds": round(time.time() - started, 1)}
