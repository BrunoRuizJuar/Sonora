"""Full-corpus morphosyntactic annotation (POS, lemmas, dependencies) with spaCy.

Design (E1-03, E3, E4; REQUIREMENTS §4.1 "POS, lemas y dependencias por lotes"):

* Input: canonical ``lyrics_analysis`` view (no section headers; lines and stanzas kept).
* Sentence policy: every verse (line) break is a forced sentence boundary; spaCy's parser
  may still split a line further on internal punctuation. Line breaks are never silently
  treated as the ONLY boundary nor ignored.
* g-dropping: ``runnin'`` is analysed through a same-length *shadow text* where ``in'`` ->
  ``ing`` (only if the ``-ing`` form is attested in the corpus lexicon). Offsets are
  identical, so every token keeps its ORIGINAL surface text; only POS/lemma/parse benefit.
* Whitespace tokens (``\\n``) are dropped from outputs. Indices refer to spaCy token
  positions inside the document (including whitespace tokens), so heads stay consistent.
* Workers write their own Parquet parts (no Doc objects travel between processes).
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import re
import time

ANNOTATION_VERSION = "spacy-lines-gdrop-v1"
LOG = logging.getLogger("sonora.nlp")
GDROP_TEXT = re.compile(r"(?<![^\W\d_'])([^\W\d_]{2,}?)(in)'(?![^\W\d_])", re.UNICODE | re.IGNORECASE)

_NLP = None
_GFORMS: frozenset[str] = frozenset()


def shadow_text(text: str, ing_forms: frozenset[str]) -> tuple[str, int]:
    """Replace attested g-dropped forms by their -ing form, keeping exact length."""
    count = 0

    def repl(match: re.Match) -> str:
        nonlocal count
        stem, suffix = match.group(1), match.group(2)
        if (stem + "ing").lower() in ing_forms:
            count += 1
            return stem + suffix + ("G" if suffix.isupper() else "g")
        return match.group(0)

    out = GDROP_TEXT.sub(repl, text)
    assert len(out) == len(text)
    return out, count


def build_nlp(model: str):
    import spacy
    from spacy.language import Language

    if "line_sentences" not in Language.factories:
        @Language.component("line_sentences")
        def line_sentences(doc):
            for token in doc[1:]:
                prev = doc[token.i - 1]
                if "\n" in prev.text or "\n" in prev.whitespace_:
                    token.is_sent_start = True
            return doc

    nlp = spacy.load(model, exclude=["ner"])
    nlp.add_pipe("line_sentences", before="parser")
    return nlp


def _init_worker(model: str, ing_forms: list[str], threads: str) -> None:
    global _NLP, _GFORMS
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[var] = threads
    try:  # numpy may already be imported: also limit the live BLAS pool
        from threadpoolctl import threadpool_limits

        threadpool_limits(int(threads))
    except ImportError:
        pass
    _NLP = build_nlp(model)
    _GFORMS = frozenset(ing_forms)


def token_schema():
    import pyarrow as pa

    d = pa.dictionary(pa.int32(), pa.string())
    return pa.schema([
        ("lyrics_id", d), ("tok_i", pa.int32()), ("sent_i", pa.int32()), ("line_i", pa.int32()),
        ("stanza_i", pa.int16()), ("text", d), ("lower", d), ("lemma", d), ("upos", d),
        ("tag", d), ("dep", d), ("head_i", pa.int32()), ("is_punct", pa.bool_()),
        ("is_alpha", pa.bool_()), ("is_stop", pa.bool_()), ("gdrop_normalized", pa.bool_()),
    ])


def sentence_schema():
    import pyarrow as pa

    return pa.schema([
        ("lyrics_id", pa.dictionary(pa.int32(), pa.string())), ("sent_i", pa.int32()),
        ("line_i", pa.int32()), ("stanza_i", pa.int16()), ("n_tokens", pa.int32()),
        ("n_words", pa.int32()), ("depth", pa.int16()), ("mean_dep_dist", pa.float32()),
        ("n_arcs", pa.int32()), ("root_upos", pa.string()), ("root_lemma", pa.string()),
    ])


def doc_schema():
    import pyarrow as pa

    return pa.schema([
        ("lyrics_id", pa.string()), ("n_tokens", pa.int32()), ("n_words", pa.int32()),
        ("n_sents", pa.int32()), ("n_lines", pa.int32()), ("n_stanzas", pa.int32()),
        ("n_gdrop_normalized", pa.int32()), ("mean_sent_words", pa.float32()),
        ("max_depth", pa.int16()), ("mean_depth", pa.float32()), ("mean_dep_dist", pa.float32()),
    ])


def depths(heads):
    """Depth of every token in its tree (root = 0): number of head hops to the root."""
    import numpy as np

    n = len(heads)
    anc = heads.copy()
    depth = (anc != np.arange(n)).astype(np.int32)
    for _ in range(n):
        up = heads[anc]
        moving = up != anc
        if not moving.any():
            break
        depth[moving] += 1
        anc = np.where(moving, up, anc)
    return depth


def _dict_from_hashes(hashes, strings):
    """spaCy string hashes -> pyarrow dictionary array (lookups only for unique values)."""
    import numpy as np
    import pyarrow as pa

    uniq, inverse = np.unique(hashes, return_inverse=True)
    dictionary = pa.array([strings[int(h)] for h in uniq], pa.string())
    return pa.DictionaryArray.from_arrays(pa.array(inverse.astype(np.int32)), dictionary)


def annotate_texts(lyrics_ids: list[str], texts: list[str]):
    """Annotate texts in the current process; returns three pyarrow tables.

    Token columns are accumulated as numpy arrays (string columns as spaCy hashes) and
    converted once per task, keeping the per-worker memory peak low.
    """
    import numpy as np
    import pyarrow as pa
    from spacy.attrs import DEP, HEAD, IS_ALPHA, IS_PUNCT, IS_SPACE, IS_STOP, LEMMA, POS, TAG

    nlp = _NLP
    strings = nlp.vocab.strings
    attrs = [LEMMA, POS, TAG, DEP, HEAD, IS_PUNCT, IS_ALPHA, IS_STOP, IS_SPACE]
    num_names = ("doc", "tok_i", "sent_i", "line_i", "stanza_i", "head_i", "is_punct", "is_alpha",
                 "is_stop", "gdrop", "lemma", "upos", "tag", "dep")
    tok_np: dict[str, list] = {k: [] for k in num_names}
    surface_all: list[str] = []
    sent_rows: dict[str, list] = {k: [] for k in sentence_schema().names}
    doc_rows: dict[str, list] = {k: [] for k in doc_schema().names}
    doc_ids: list[str] = []
    shadows, gcounts = [], []
    for text in texts:
        s, c = shadow_text(text, _GFORMS)
        shadows.append(s)
        gcounts.append(c)
    for lid, text, shadow, doc, gcount in zip(lyrics_ids, texts, shadows, nlp.pipe(shadows, batch_size=16), gcounts):
        n = len(doc)
        if n == 0:
            continue
        arr = doc.to_array(attrs).astype(np.int64)
        lemma, pos, tag, dep = (arr[:, k].astype(np.uint64) for k in range(4))
        heads = np.arange(n) + arr[:, 4]
        is_punct, is_alpha, is_stop, is_space = (arr[:, k].astype(bool) for k in range(5, 9))
        idx = np.fromiter((t.idx for t in doc), dtype=np.int64, count=n)
        lengths = np.fromiter((len(t) for t in doc), dtype=np.int64, count=n)
        # line / stanza from character offsets in the ORIGINAL text (same offsets as shadow)
        orig_cp = np.frombuffer(text.encode("utf-32-le"), dtype=np.uint32)
        newline_pos = np.flatnonzero(orig_cp == 10)
        line_i = np.searchsorted(newline_pos, idx, side="right")
        blank = newline_pos[1:][np.diff(newline_pos) == 1]  # second \n of each "\n\n"
        stanza_i = np.searchsorted(blank, idx, side="right")
        # tokens whose characters differ between original and shadow text (g-dropping)
        diff = np.concatenate([[0], np.cumsum(orig_cp != np.frombuffer(shadow.encode("utf-32-le"), dtype=np.uint32))])
        changed = (diff[idx + lengths] - diff[idx]) > 0
        sent_i = np.zeros(n, dtype=np.int32)
        sent_bounds = []
        for k, sent in enumerate(doc.sents):
            sent_i[sent.start:sent.end] = k
            sent_bounds.append((sent.start, sent.end))
        depth = depths(heads)
        keep = ~is_space
        kept = np.flatnonzero(keep)
        k = len(kept)
        doc_no = len(doc_ids)
        doc_ids.append(lid)
        surface_all.extend(text[i:i + l] for i, l in zip(idx[kept].tolist(), lengths[kept].tolist()))
        tok_np["doc"].append(np.full(k, doc_no, dtype=np.int32))
        tok_np["tok_i"].append(kept.astype(np.int32))
        tok_np["sent_i"].append(sent_i[kept])
        tok_np["line_i"].append(line_i[kept].astype(np.int32))
        tok_np["stanza_i"].append(stanza_i[kept].astype(np.int16))
        tok_np["head_i"].append(heads[kept].astype(np.int32))
        tok_np["is_punct"].append(is_punct[kept])
        tok_np["is_alpha"].append(is_alpha[kept])
        tok_np["is_stop"].append(is_stop[kept])
        tok_np["gdrop"].append(changed[kept])
        tok_np["lemma"].append(lemma[kept])
        tok_np["upos"].append(pos[kept])
        tok_np["tag"].append(tag[kept])
        tok_np["dep"].append(dep[kept])
        # sentence metrics: arcs between non-space, non-punct tokens; root excluded
        sent_words, sent_depths, sent_dists = [], [], []
        for k_s, (a, b) in enumerate(sent_bounds):
            sel = np.arange(a, b)
            content = sel[~is_space[sel]]
            if len(content) == 0:
                continue
            words = content[~is_punct[content]]
            arcs = words[heads[words] != words]
            arcs = arcs[~is_punct[heads[arcs]]]
            dist = np.abs(arcs - heads[arcs])
            roots = content[heads[content] == content]
            root = roots[0] if len(roots) else content[0]
            d = int(depth[words].max()) if len(words) else 0
            sent_rows["lyrics_id"].append(lid)
            sent_rows["sent_i"].append(k_s)
            sent_rows["line_i"].append(int(line_i[content[0]]))
            sent_rows["stanza_i"].append(int(stanza_i[content[0]]))
            sent_rows["n_tokens"].append(len(content))
            sent_rows["n_words"].append(len(words))
            sent_rows["depth"].append(d)
            sent_rows["mean_dep_dist"].append(float(dist.mean()) if len(dist) else None)
            sent_rows["n_arcs"].append(len(arcs))
            sent_rows["root_upos"].append(strings[int(pos[root])])
            sent_rows["root_lemma"].append(strings[int(lemma[root])])
            sent_words.append(len(words))
            sent_depths.append(d)
            sent_dists.append(dist)
        all_d = np.concatenate(sent_dists) if sent_dists else np.array([])
        doc_rows["lyrics_id"].append(lid)
        doc_rows["n_tokens"].append(k)
        doc_rows["n_words"].append(int((keep & ~is_punct).sum()))
        doc_rows["n_sents"].append(len(sent_words))
        doc_rows["n_lines"].append(len(set(line_i[keep].tolist())))
        doc_rows["n_stanzas"].append(len(set(stanza_i[keep].tolist())))
        doc_rows["n_gdrop_normalized"].append(gcount)
        doc_rows["mean_sent_words"].append(float(np.mean(sent_words)) if sent_words else None)
        doc_rows["max_depth"].append(max(sent_depths) if sent_depths else 0)
        doc_rows["mean_depth"].append(float(np.mean(sent_depths)) if sent_depths else None)
        doc_rows["mean_dep_dist"].append(float(all_d.mean()) if len(all_d) else None)

    def table(cols, schema):
        arrays = []
        for f in schema:
            values = cols[f.name]
            if pa.types.is_dictionary(f.type):
                arrays.append(pa.array(values, pa.string()).dictionary_encode().cast(f.type))
            else:
                arrays.append(pa.array(values, f.type))
        return pa.Table.from_arrays(arrays, schema=schema)

    schema = token_schema()
    if doc_ids:
        cat = {name: np.concatenate(parts) for name, parts in tok_np.items()}
    else:
        cat = {name: np.array([], dtype=np.int32) for name in tok_np}
        cat.update({h: np.array([], dtype=np.uint64) for h in ("lemma", "upos", "tag", "dep")})
    surface = pa.array(surface_all, pa.string())
    lower = pa.array([w.lower() for w in surface_all], pa.string())
    columns = {
        "lyrics_id": pa.DictionaryArray.from_arrays(pa.array(cat["doc"], pa.int32()), pa.array(doc_ids, pa.string())),
        "tok_i": pa.array(cat["tok_i"], pa.int32()), "sent_i": pa.array(cat["sent_i"], pa.int32()),
        "line_i": pa.array(cat["line_i"], pa.int32()), "stanza_i": pa.array(cat["stanza_i"], pa.int16()),
        "text": surface.dictionary_encode(), "lower": lower.dictionary_encode(),
        "lemma": _dict_from_hashes(cat["lemma"], strings), "upos": _dict_from_hashes(cat["upos"], strings),
        "tag": _dict_from_hashes(cat["tag"], strings), "dep": _dict_from_hashes(cat["dep"], strings),
        "head_i": pa.array(cat["head_i"], pa.int32()), "is_punct": pa.array(cat["is_punct"], pa.bool_()),
        "is_alpha": pa.array(cat["is_alpha"], pa.bool_()), "is_stop": pa.array(cat["is_stop"], pa.bool_()),
        "gdrop_normalized": pa.array(cat["gdrop"], pa.bool_()),
    }
    tokens = pa.Table.from_arrays([columns[f.name].cast(f.type) for f in schema], schema=schema)
    return tokens, table(sent_rows, sentence_schema()), table(doc_rows, doc_schema())


@dataclass(frozen=True)
class Task:
    corpus_file: str
    shard_stem: str
    index: int
    start: int
    end: int
    out_dir: str
    config_hash: str

    def part(self, kind: str) -> Path:
        return Path(self.out_dir) / kind / self.shard_stem / f"part-{self.index:05d}.parquet"


def part_complete(task: Task) -> bool:
    import pyarrow.parquet as pq

    for kind in ("tokens", "sentences", "docs"):
        path = task.part(kind)
        if not path.exists():
            return False
        try:
            meta = pq.ParquetFile(path).schema_arrow.metadata or {}
        except Exception:
            return False
        if meta.get(b"sonora_annotation_hash", b"").decode() != task.config_hash or \
                meta.get(b"sonora_range", b"").decode() != f"{task.start}:{task.end}":
            return False
    return True


def run_task(task: Task) -> dict:
    """Executed in a worker: read rows, annotate, write the three parts atomically."""
    import pyarrow.parquet as pq

    from sonora.ingestion.genius import iter_rows
    from sonora.storage.runs import write_parquet_atomic

    t0 = time.time()
    ids, texts = [], []
    for _, batch in iter_rows(Path(task.corpus_file), task.start, task.end, 1000, ["lyrics_id", "lyrics_analysis"]):
        ids.extend(batch.column(0).to_pylist())
        texts.extend(batch.column(1).to_pylist())
    tokens, sents, docs = annotate_texts(ids, texts)
    if docs.num_rows != len(ids):
        raise RuntimeError(f"{task}: {docs.num_rows} documentos anotados de {len(ids)}")
    meta = {"sonora_annotation_hash": task.config_hash, "sonora_range": f"{task.start}:{task.end}"}
    # docs written last: its presence + metadata marks the task as complete
    for kind, tbl in (("tokens", tokens), ("sentences", sents), ("docs", docs)):
        write_parquet_atomic(tbl.replace_schema_metadata(meta), task.part(kind))
    return {"task": f"{task.shard_stem}/{task.index}", "docs": len(ids), "tokens": tokens.num_rows,
            "words": int(sum(docs.column("n_words").to_pylist())), "seconds": round(time.time() - t0, 1),
            "pid": os.getpid()}


def plan_tasks(corpus_files: list[Path], out_dir: Path, docs_per_task: int, config_hash: str) -> list[Task]:
    import pyarrow.parquet as pq

    tasks = []
    for path in corpus_files:
        n = pq.ParquetFile(path).metadata.num_rows
        for i, start in enumerate(range(0, n, docs_per_task)):
            tasks.append(Task(str(path), path.stem, i, start, min(start + docs_per_task, n), str(out_dir), config_hash))
    return tasks


def run_annotation(tasks: list[Task], model: str, ing_forms: list[str], workers: int,
                   max_tasks: int | None = None, on_result=None) -> dict:
    from concurrent.futures import ProcessPoolExecutor, as_completed

    todo = [t for t in tasks if not part_complete(t)]
    for t in todo:
        for kind in ("tokens", "sentences", "docs"):
            t.part(kind).with_name(t.part(kind).name + ".tmp").unlink(missing_ok=True)
    if max_tasks is not None:
        todo = todo[:max_tasks]
    LOG.info("Anotación: %d tareas, %d pendientes en esta sesión, %d workers", len(tasks), len(todo), workers)
    done = words = 0
    started = time.time()
    if todo:
        with ProcessPoolExecutor(workers, initializer=_init_worker, initargs=(model, ing_forms, "1")) as pool:
            futures = [pool.submit(run_task, t) for t in todo]
            for future in as_completed(futures):
                result = future.result()
                done += 1
                words += result["words"]
                elapsed = time.time() - started
                rate = words / max(elapsed, 1e-9)
                LOG.info("%s: %d docs, %d tokens en %.0fs | %d/%d | %.0f palabras/s acumulado",
                         result["task"], result["docs"], result["tokens"], result["seconds"], done, len(todo), rate)
                if on_result:
                    on_result(result)
    remaining = sum(1 for t in tasks if not part_complete(t))
    return {"tasks_total": len(tasks), "tasks_done_this_session": done, "tasks_remaining": remaining,
            "words_this_session": words, "seconds_this_session": round(time.time() - started, 1),
            "status": "complete" if remaining == 0 else "incomplete"}
