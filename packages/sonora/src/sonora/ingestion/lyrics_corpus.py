"""Reproducible preparation of the full English lyrics corpus and the demo links.

Stages (each one resumable / idempotent, single writer per run):

1. ``ingest``      Genius shards -> per-chunk record tables (metadata, views stats,
                   hashes, language, status, exclusion reason). No text is copied here.
2. ``consolidate`` exact-duplicate consolidation by normalized text hash; mapping of
                   EVERY source record; exclusion log; canonical corpus with the three
                   text views (original / structural / analysis).
3. ``split``       related-document groups (identical hash + same artist/base title)
                   and a deterministic 70/20/10 split by group.
4. ``demo``        verifies the 886 retained FMA Medium locators and links them to
                   canonical lyrics, groups and splits, with capabilities.
5. ``report``      quality report and language audit sample.

Raw inputs are only read. Outputs are written atomically (``.tmp`` + rename).
"""
from __future__ import annotations

from collections import Counter
import gc
from dataclasses import dataclass, field
import hashlib
import json
import logging
from pathlib import Path
import re
import time
from typing import Callable

from sonora.ingestion import genius
from sonora.matching.normalize import NORMALIZATION_VERSION, base_title, normalize
from sonora.nlp.language import (
    Detector, LanguageRules, LanguageScores, SecondaryDetector, decide, needs_secondary,
)
from sonora.preprocessing.lyrics_text import (
    TEXT_VIEWS_VERSION, build_views, dedup_key, language_excerpt, sha256_hex,
)
from sonora.storage import runs

PIPELINE_VERSION = "lyrics-corpus-1.0.0"
LOG = logging.getLogger("sonora.lyrics_corpus")
SPLITS = ("train", "test", "validation")


# --------------------------------------------------------------------------- config

def load_config(path: Path) -> dict:
    import yaml

    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@dataclass
class Scope:
    shards: list[str] | None = None          # None = all expected shards
    row_limit_per_shard: int | None = None   # None = every row

    @property
    def is_full(self) -> bool:
        return self.shards is None and self.row_limit_per_shard is None

    def as_dict(self) -> dict:
        return {"shards": self.shards, "row_limit_per_shard": self.row_limit_per_shard}


def ingest_config(config: dict, scope: Scope) -> dict:
    """The part of the configuration that determines ingest results."""
    return {
        "pipeline_version": PIPELINE_VERSION,
        "text_views_version": TEXT_VIEWS_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "genius": config["genius"],
        "chunk_rows": config["chunk_rows"],
        "language": config["language"],
        "quality": config["quality"],
        "dedup": config["dedup"],
        "scope": scope.as_dict(),
        "detector_package_versions": _package_versions("lingua-language-detector", "py3langid"),
    }


def _package_versions(*names: str) -> dict:
    import importlib.metadata

    out = {}
    for name in names:
        try:
            out[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            out[name] = None
    return out


def default_run_id(config: dict, scope: Scope) -> str:
    tag = "full" if scope.is_full else "subset"
    return f"lyrics_{tag}_{runs.config_hash(ingest_config(config, scope))[:10]}"


@dataclass
class Run:
    root: Path
    config: dict
    run_id: str
    scope: Scope = field(default_factory=Scope)

    @property
    def interim(self) -> Path:
        return self.root / "data" / "interim" / "lyrics" / self.run_id

    @property
    def records_dir(self) -> Path:
        return self.interim / "records"

    @property
    def processed(self) -> Path:
        return self.root / "data" / "processed" / "lyrics" / self.run_id

    @property
    def splits_dir(self) -> Path:
        return self.root / "data" / "processed" / "splits" / self.run_id

    @property
    def demo_dir(self) -> Path:
        return self.root / "data" / "processed" / "demo" / self.run_id

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifests" / "runs" / f"{self.run_id}.json"

    @property
    def report_dir(self) -> Path:
        return self.root / "reports" / "corpus" / self.run_id

    @property
    def lock_path(self) -> Path:
        return self.root / "runtime" / "locks" / f"{self.run_id}.lock"

    @property
    def ingest_hash(self) -> str:
        return runs.config_hash(ingest_config(self.config, self.scope))

    def genius_dir(self) -> Path:
        return self.root / self.config["genius"]["dir"]

    def shard_paths(self) -> list[Path]:
        paths = genius.list_shards(self.genius_dir(), self.config["genius"]["pattern"])
        expected = self.config["genius"].get("expected_files")
        if expected and len(paths) != expected:
            raise ValueError(f"Se esperaban {expected} shards Genius y hay {len(paths)} en {self.genius_dir()}")
        if self.scope.shards is not None:
            wanted = set(self.scope.shards)
            paths = [p for p in paths if p.name in wanted or p.stem in wanted]
            missing = wanted - {p.name for p in paths} - {p.stem for p in paths}
            if missing:
                raise ValueError(f"Shards no encontrados: {sorted(missing)}")
        return paths

    # ---------------------------------------------------------------- manifest
    def load_manifest(self) -> dict:
        if self.manifest_path.exists():
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return {}

    def update_manifest(self, **sections) -> dict:
        manifest = self.load_manifest()
        manifest.setdefault("run_id", self.run_id)
        manifest.setdefault("created_utc", runs.utc_now())
        manifest["updated_utc"] = runs.utc_now()
        stages = manifest.setdefault("stages", {})
        for key, value in sections.items():
            if key.startswith("stage_"):
                stages[key[6:]] = value
            else:
                manifest[key] = value
        runs.write_json_atomic(self.manifest_path, manifest)
        return manifest


def code_files() -> list[Path]:
    base = Path(__file__).resolve().parents[1]
    names = [
        "ingestion/genius.py", "ingestion/lyrics_corpus.py", "matching/normalize.py",
        "nlp/language.py", "preprocessing/lyrics_text.py", "storage/runs.py",
    ]
    return [base / name for name in names]


def provenance(run: Run) -> dict:
    return {
        "pipeline_version": PIPELINE_VERSION,
        "code_sha256": runs.code_fingerprint(code_files()),
        "git_revision": runs.git_revision(run.root),
        "environment": runs.environment_info(),
    }


# --------------------------------------------------------------------------- sources

def source_snapshot(run: Run, with_sha256: bool) -> list[dict]:
    """Size/mtime/rows of each shard; sha256 cached by (name, size, mtime)."""
    cache_path = run.root / "manifests" / "sources" / "genius_snapshot.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    entries = {e["name"]: e for e in cache.get("files", [])}
    out = []
    changed = False
    for path in run.shard_paths():
        info = genius.inspect_shard(path)
        cached = entries.get(path.name)
        if cached and cached.get("bytes") == info["bytes"] and cached.get("mtime_ns") == info["mtime_ns"]:
            info["sha256"] = cached.get("sha256")
        if with_sha256 and not info.get("sha256"):
            LOG.info("sha256 %s ...", path.name)
            info["sha256"] = runs.file_sha256(path)
            changed = True
        entries[path.name] = info
        out.append(info)
    if changed:
        runs.write_json_atomic(cache_path, {
            "dataset": run.config["genius"].get("dataset"),
            "revision": None,
            "note": "Revisión de Hugging Face no registrada en la descarga; la identidad se fija por sha256.",
            "updated_utc": runs.utc_now(),
            "files": sorted(entries.values(), key=lambda e: e["name"]),
        })
    return out


# --------------------------------------------------------------------------- ingest

def records_schema():
    import pyarrow as pa

    return pa.schema([
        ("source_file", pa.string()),
        ("source_row_zero_based", pa.int64()),
        ("source_key", pa.string()),
        ("title", pa.string()),
        ("artist", pa.string()),
        ("tag", pa.string()),
        ("year", pa.int64()),
        ("n_chars_original", pa.int32()),
        ("n_chars_analysis", pa.int32()),
        ("n_lines", pa.int32()),
        ("n_stanzas", pa.int32()),
        ("n_section_markers", pa.int32()),
        ("n_words", pa.int32()),
        ("section_labels", pa.list_(pa.string())),
        ("text_sha256_original", pa.string()),
        ("text_hash", pa.string()),
        ("lang_top", pa.string()),
        ("lang_top_conf", pa.float32()),
        ("lang_second", pa.string()),
        ("lang_second_conf", pa.float32()),
        ("lang_en_conf", pa.float32()),
        ("lang_secondary", pa.string()),
        ("lang_secondary_conf", pa.float32()),
        ("lang_status", pa.string()),
        ("lang_reason", pa.string()),
        ("quality_flags", pa.list_(pa.string())),
        ("status", pa.string()),
        ("exclusion_rule", pa.string()),
        ("exclusion_reason", pa.string()),
    ])


class RecordBuilder:
    """Pure per-row logic of the ingest stage (independent of batching)."""

    def __init__(self, config: dict, detector: Detector, secondary: SecondaryDetector) -> None:
        self.detector = detector
        self.secondary = secondary
        quality = config["quality"]
        language = config["language"]
        self.min_words = int(quality["min_words"])
        self.very_long = int(quality["very_long_chars"])
        self.placeholder_max_words = int(quality["placeholder_max_words"])
        self.placeholders = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in quality["placeholder_patterns"]]
        self.window = int(language["excerpt_window_chars"])
        self.windows = int(language["excerpt_windows"])
        self.rules = LanguageRules(**language["rules"])

    def build(self, shard: str, first_row: int, columns: dict[str, list]) -> list[dict]:
        rows: list[dict] = []
        pending: list[tuple[int, str]] = []
        for offset, lyrics in enumerate(columns["lyrics"]):
            row = first_row + offset
            year = columns["year"][offset]
            record = {
                "source_file": shard,
                "source_row_zero_based": row,
                "source_key": genius.locator(shard, row),
                "title": columns["title"][offset],
                "artist": columns["artist"][offset],
                "tag": columns["tag"][offset],
                "year": year,
                "section_labels": [],
                "quality_flags": [],
                "status": None,
            }
            flags = record["quality_flags"]
            if record["title"] is None or not str(record["title"]).strip():
                flags.append("missing_title")
            if record["artist"] is None or not str(record["artist"]).strip():
                flags.append("missing_artist")
            if lyrics is None or not lyrics.strip():
                record.update(status="excluded", exclusion_rule="empty_lyrics",
                              exclusion_reason="lyrics nulo o sólo espacios",
                              n_chars_original=0 if lyrics is None else len(lyrics))
                rows.append(record)
                continue
            views = build_views(lyrics)
            flags.extend(views.flags)
            record.update(
                n_chars_original=views.n_chars_original,
                n_chars_analysis=views.n_chars_analysis,
                n_lines=views.n_lines,
                n_stanzas=views.n_stanzas,
                n_section_markers=views.n_section_markers,
                n_words=views.n_words,
                section_labels=views.section_labels,
                text_sha256_original=sha256_hex(lyrics),
                text_hash=sha256_hex(dedup_key(views.analysis)),
            )
            if views.n_chars_original >= self.very_long:
                flags.append("very_long")
            if views.n_words < self.min_words:
                record.update(status="excluded", exclusion_rule="too_few_words",
                              exclusion_reason=f"{views.n_words} palabras < {self.min_words} en la vista de análisis")
            elif views.n_words <= self.placeholder_max_words and any(p.search(views.analysis) for p in self.placeholders):
                record.update(status="excluded", exclusion_rule="placeholder_text",
                              exclusion_reason="texto de marcador/instrumental en lugar de letra")
            else:
                pending.append((len(rows), language_excerpt(views.analysis, self.window, self.windows)))
            rows.append(record)
        if pending:
            scores = self.detector.score_many([text for _, text in pending])
            for (index, excerpt), score in zip(pending, scores):
                self._apply_language(rows[index], score, excerpt)
        return rows

    def _apply_language(self, record: dict, score: LanguageScores, excerpt: str) -> None:
        secondary = None
        if needs_secondary(score, record["n_words"], self.rules):
            secondary = self.secondary.classify(excerpt)
        status, reason = decide(score, record["n_words"], self.rules, secondary)
        record.update(
            lang_top=score.top, lang_top_conf=score.top_conf, lang_second=score.second,
            lang_second_conf=score.second_conf, lang_en_conf=score.en_conf,
            lang_secondary=secondary.lang if secondary else None,
            lang_secondary_conf=secondary.conf if secondary else None,
            lang_status=status, lang_reason=reason,
        )
        if record["n_words"] < self.rules.short_text_words:
            record["quality_flags"].append("short_text_language")
        if status == "en":
            record["status"] = "accepted"
        elif status == "non_en":
            record.update(status="excluded", exclusion_rule="non_english",
                          exclusion_reason=f"{reason}: {score.top} ({score.top_conf:.3f}) y "
                                           f"{secondary.lang} ({secondary.conf:.3f}); en={score.en_conf:.3f}")
        else:
            sec = f"{secondary.lang} ({secondary.conf:.3f})" if secondary else "-"
            record.update(status="review", exclusion_rule="language_uncertain",
                          exclusion_reason=f"{reason}: primario={score.top} ({score.top_conf:.3f}), "
                                           f"secundario={sec}; en={score.en_conf:.3f}")


def _part_is_complete(path: Path, chunk: genius.Chunk, ingest_hash: str) -> bool:
    import pyarrow.parquet as pq

    try:
        parquet = pq.ParquetFile(path)
    except Exception:  # corrupt or partial file
        return False
    meta = parquet.schema_arrow.metadata or {}
    expected_chunk = json.dumps({"start": chunk.start, "end": chunk.end})
    return (
        meta.get(b"sonora_ingest_hash", b"").decode() == ingest_hash
        and meta.get(b"sonora_chunk", b"").decode() == expected_chunk
        and parquet.metadata.num_rows == chunk.end - chunk.start
    )


def plan_all_chunks(run: Run) -> list[tuple[Path, genius.Chunk]]:
    planned = []
    for path in run.shard_paths():
        info = genius.inspect_shard(path)
        missing = set(run.config["genius"]["columns"]) - set(info["columns"])
        if missing:
            raise ValueError(f"{path.name}: faltan columnas {sorted(missing)}; esquema real {info['columns']}")
        for chunk in genius.plan_chunks(path.name, info["num_rows"], run.config["chunk_rows"], run.scope.row_limit_per_shard):
            planned.append((path, chunk))
    return planned


def _check_or_write_run_config(run: Run, snapshot: list[dict]) -> None:
    path = run.interim / "run_config.json"
    inputs = [{k: s[k] for k in ("name", "bytes", "mtime_ns", "num_rows")} for s in snapshot]
    payload = {"ingest_hash": run.ingest_hash, "ingest_config": ingest_config(run.config, run.scope), "inputs": inputs}
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("ingest_hash") != run.ingest_hash:
            raise ValueError(
                f"La ejecución {run.run_id} se creó con otra configuración "
                f"({existing.get('ingest_hash', '?')[:12]} != {run.ingest_hash[:12]}). Usa otro --run-id."
            )
        if existing.get("inputs") != inputs:
            raise ValueError(f"Los archivos de entrada cambiaron desde que empezó {run.run_id}; no se puede reanudar.")
        return
    runs.write_json_atomic(path, payload)


def ingest(run: Run, detector_factory: Callable[[], tuple[Detector, SecondaryDetector]], batch_size: int = 2000,
           max_chunks: int | None = None, hash_inputs: bool = True) -> dict:
    """Process every planned chunk not yet complete. ``max_chunks`` simulates/limits work."""
    import pyarrow as pa

    started = time.time()
    snapshot = source_snapshot(run, with_sha256=hash_inputs)
    run.interim.mkdir(parents=True, exist_ok=True)
    _check_or_write_run_config(run, snapshot)
    for tmp in run.records_dir.rglob("*.tmp"):
        LOG.warning("Eliminando temporal incompleto %s", tmp)
        tmp.unlink()
    planned = plan_all_chunks(run)
    todo = [(p, c) for p, c in planned
            if not _part_is_complete(run.records_dir / c.shard_stem / c.part_name, c, run.ingest_hash)]
    total_rows = sum(c.end - c.start for _, c in planned)
    LOG.info("Ingesta %s: %d partes planificadas, %d pendientes, %d filas en alcance",
             run.run_id, len(planned), len(todo), total_rows)
    run.update_manifest(
        scope=run.scope.as_dict(), scope_is_full_corpus=run.scope.is_full,
        ingest_hash=run.ingest_hash, config=run.config, provenance=provenance(run), inputs=snapshot,
        stage_ingest={"status": "running", "started_utc": runs.utc_now(), "chunks_total": len(planned),
                      "chunks_pending_at_start": len(todo), "rows_in_scope": total_rows, "batch_size": batch_size},
    )
    detector, secondary = detector_factory() if todo else (None, None)
    builder = RecordBuilder(run.config, detector, secondary) if detector else None
    schema = records_schema().with_metadata({})
    done_now = 0
    rows_now = 0
    columns = run.config["genius"]["columns"]
    for path, chunk in todo:
        if max_chunks is not None and done_now >= max_chunks:
            break
        t0 = time.time()
        rows: list[dict] = []
        for first_row, batch in genius.iter_rows(path, chunk.start, chunk.end, batch_size, columns):
            rows.extend(builder.build(chunk.shard, first_row, batch.to_pydict()))
        if [r["source_row_zero_based"] for r in rows] != list(range(chunk.start, chunk.end)):
            raise RuntimeError(f"Localizadores no contiguos en {chunk}")
        table = pa.Table.from_pylist(rows, schema=schema).replace_schema_metadata({
            "sonora_ingest_hash": run.ingest_hash,
            "sonora_chunk": json.dumps({"start": chunk.start, "end": chunk.end}),
            "sonora_detector": f"{detector.name}=={detector.version}+{secondary.name}=={secondary.version}",
        })
        runs.write_parquet_atomic(table, run.records_dir / chunk.shard_stem / chunk.part_name)
        done_now += 1
        rows_now += len(rows)
        elapsed = time.time() - t0
        counts = Counter(r["status"] for r in rows)
        LOG.info("%s %s filas [%d,%d) en %.1fs (%.0f filas/s) %s | %d/%d partes en esta sesión",
                 chunk.shard_stem, chunk.part_name, chunk.start, chunk.end, elapsed,
                 len(rows) / max(elapsed, 1e-9), dict(counts), done_now, len(todo))
    remaining = sum(1 for p, c in planned
                    if not _part_is_complete(run.records_dir / c.shard_stem / c.part_name, c, run.ingest_hash))
    status = "complete" if remaining == 0 else "incomplete"
    result = {
        "status": status, "finished_utc": runs.utc_now(), "chunks_total": len(planned),
        "chunks_remaining": remaining, "chunks_written_this_session": done_now,
        "rows_written_this_session": rows_now, "rows_in_scope": total_rows,
        "seconds_this_session": round(time.time() - started, 1), "batch_size": batch_size,
        "peak_rss_bytes": runs.peak_rss_bytes(),
        "detector": (f"{detector.name}=={detector.version} ({getattr(detector, 'mode', '?')}) + "
                     f"{secondary.name}=={secondary.version}") if detector else None,
    }
    run.update_manifest(stage_ingest=result)
    LOG.info("Ingesta %s: %s (%d partes restantes)", run.run_id, status, remaining)
    return result


def require_ingest_complete(run: Run) -> list[tuple[Path, genius.Chunk]]:
    planned = plan_all_chunks(run)
    missing = [c for _, c in planned
               if not _part_is_complete(run.records_dir / c.shard_stem / c.part_name, c, run.ingest_hash)]
    if missing:
        raise RuntimeError(
            f"Ingesta incompleta: faltan {len(missing)} de {len(planned)} partes "
            f"(p. ej. {missing[0].shard_stem}/{missing[0].part_name}). Reanuda con el subcomando ingest."
        )
    return planned


def read_records(run: Run, columns: list[str] | None = None, filter=None):
    import pyarrow.dataset as ds

    planned = require_ingest_complete(run)
    files = [str(run.records_dir / c.shard_stem / c.part_name) for _, c in planned]
    return ds.dataset(files, format="parquet", schema=records_schema()).to_table(columns=columns, filter=filter)


def _lyrics_ids(run: Run, text_hash):
    """``lyr_`` + first hex chars of the text hash (null stays null)."""
    import pyarrow as pa
    import pyarrow.compute as pc

    prefix = run.config["dedup"]["id_prefix"]
    width = int(run.config["dedup"]["id_hex_chars"])
    return pc.binary_join_element_wise(pa.scalar(prefix), pc.utf8_slice_codeunits(text_hash, 0, width), "")


# --------------------------------------------------------------------------- consolidate

def _with_order(run: Run, table):
    import pyarrow as pa
    import pyarrow.compute as pc

    names = [p.name for p in run.shard_paths()]
    index = pa.array(names)
    shard_idx = pc.index_in(table["source_file"], value_set=index).cast(pa.int64())
    order = pc.add(pc.multiply(shard_idx, pa.scalar(10**9, pa.int64())), table["source_row_zero_based"])
    return table.append_column("source_order", order)


def mapping_schema():
    import pyarrow as pa

    return pa.schema([
        ("source_key", pa.string()), ("source_file", pa.string()), ("source_row_zero_based", pa.int64()),
        ("title", pa.string()), ("artist", pa.string()), ("status", pa.string()),
        ("exclusion_rule", pa.string()), ("exclusion_reason", pa.string()), ("lang_status", pa.string()),
        ("text_hash", pa.string()), ("lyrics_id", pa.string()), ("is_canonical", pa.bool_()),
        ("consolidation_reason", pa.string()), ("matches_accepted_lyrics_id", pa.string()),
    ])


def corpus_schema():
    import pyarrow as pa

    return pa.schema([
        ("lyrics_id", pa.string()), ("source_key", pa.string()), ("source_file", pa.string()),
        ("source_row_zero_based", pa.int64()), ("title", pa.string()), ("artist", pa.string()),
        ("tag", pa.string()), ("year", pa.int64()),
        ("lyrics_original", pa.string()), ("lyrics_structural", pa.string()), ("lyrics_analysis", pa.string()),
        ("text_hash", pa.string()), ("text_sha256_original", pa.string()),
        ("lang_top", pa.string()), ("lang_top_conf", pa.float32()), ("lang_en_conf", pa.float32()),
        ("lang_status", pa.string()), ("lang_reason", pa.string()), ("language_detector", pa.string()),
        ("n_chars_original", pa.int32()), ("n_chars_analysis", pa.int32()), ("n_lines", pa.int32()),
        ("n_stanzas", pa.int32()), ("n_section_markers", pa.int32()), ("n_words", pa.int32()),
        ("section_labels", pa.list_(pa.string())), ("quality_flags", pa.list_(pa.string())),
        ("n_source_records", pa.int32()), ("status", pa.string()),
    ])


def consolidate(run: Run, batch_size: int = 2000) -> dict:
    import numpy as np
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    started = time.time()
    planned = require_ingest_complete(run)
    run.update_manifest(stage_consolidate={"status": "running", "started_utc": runs.utc_now()})
    cols = ["source_key", "source_file", "source_row_zero_based", "title", "artist", "status",
            "exclusion_rule", "exclusion_reason", "lang_status", "text_hash"]
    table = _with_order(run, read_records(run, cols))
    n_source = table.num_rows
    LOG.info("Consolidación: %d registros de origen", n_source)
    status_counts = {r["values"]: r["counts"] for r in pc.value_counts(table["status"]).to_pylist()}

    accepted = table.filter(pc.equal(table["status"], "accepted"))
    n_accepted = accepted.num_rows
    canon = accepted.group_by("text_hash").aggregate([("source_order", "min"), ("source_order", "count")])
    del accepted
    n_canonical = canon.num_rows
    if pc.count_distinct(_lyrics_ids(run, canon["text_hash"])).as_py() != n_canonical:
        raise RuntimeError("Colisión de prefijos de hash al crear lyrics_id; aumenta dedup.id_hex_chars")

    joined = table.join(canon, keys="text_hash", join_type="left outer").sort_by("source_order")
    del table, canon
    gc.collect()
    is_acc = pc.equal(joined["status"], "accepted")
    null_str = pa.scalar(None, pa.string())
    text_id = _lyrics_ids(run, joined["text_hash"])
    matched = pc.fill_null(pc.is_valid(joined["source_order_min"]), False)
    lyrics_id = pc.if_else(is_acc, text_id, null_str)
    is_canonical = pc.and_(is_acc, pc.equal(joined["source_order"], joined["source_order_min"]))
    is_canonical = pc.fill_null(is_canonical, False)
    reason = pc.if_else(is_canonical, pa.scalar("canonical_first_source_order"),
                        pc.if_else(is_acc, pa.scalar("identical_normalized_text_hash"), null_str))
    matches = pc.if_else(pc.and_(pc.invert(is_acc), matched), text_id, null_str)
    mapping = pa.table({
        **{name: joined[name] for name in cols},
        "lyrics_id": lyrics_id, "is_canonical": is_canonical,
        "consolidation_reason": reason, "matches_accepted_lyrics_id": matches,
    }, schema=mapping_schema())
    if mapping.num_rows != n_source:
        raise RuntimeError("La correspondencia no conserva todos los registros de origen")
    # Per-shard canonical rows and their duplicate counts, kept as compact columns.
    canon_rows = joined.filter(is_canonical).select(["source_file", "source_row_zero_based", "source_order_count"])
    del joined, is_acc, text_id, matched, lyrics_id, is_canonical, reason, matches
    run.processed.mkdir(parents=True, exist_ok=True)
    meta = {"sonora_ingest_hash": run.ingest_hash}
    runs.write_parquet_atomic(mapping.replace_schema_metadata(meta), run.processed / "source_to_lyrics.parquet")
    del mapping
    gc.collect()
    exclusions = read_records(run, [
        "source_key", "source_file", "source_row_zero_based", "title", "artist", "status", "exclusion_rule",
        "exclusion_reason", "lang_top", "lang_top_conf", "lang_second", "lang_second_conf", "lang_en_conf",
        "lang_secondary", "lang_secondary_conf", "lang_status", "lang_reason", "n_words", "n_chars_original",
        "quality_flags", "text_hash",
    ], filter=pc.field("status") != "accepted")
    runs.write_parquet_atomic(exclusions.replace_schema_metadata(meta), run.processed / "exclusions.parquet")
    del exclusions

    # Canonical corpus, one file per shard, rebuilding views from the untouched raw text.
    corpus_dir = run.processed / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    for tmp in corpus_dir.glob("*.tmp"):
        tmp.unlink()
    shard_files = {p.name: p for p in run.shard_paths()}
    detector_label = None
    corpus_rows = 0
    by_shard: dict[str, list[genius.Chunk]] = {}
    for _, chunk in planned:
        by_shard.setdefault(chunk.shard, []).append(chunk)
    prefix = run.config["dedup"]["id_prefix"]
    width = int(run.config["dedup"]["id_hex_chars"])
    for shard, chunks in by_shard.items():
        rows_here = canon_rows.filter(pc.equal(canon_rows["source_file"], shard))
        counts = np.zeros(chunks[-1].end, dtype=np.int32)
        counts[rows_here["source_row_zero_based"].to_numpy()] = rows_here["source_order_count"].to_numpy()
        mask = counts > 0
        expected_here = int(mask.sum())
        out_path = corpus_dir / f"{shard.removesuffix('.parquet')}.parquet"
        if out_path.exists():
            existing = pq.ParquetFile(out_path)
            if ((existing.schema_arrow.metadata or {}).get(b"sonora_ingest_hash", b"").decode() == run.ingest_hash
                    and existing.metadata.num_rows == expected_here):
                LOG.info("Corpus %s ya completo; se conserva", out_path.name)
                corpus_rows += expected_here
                continue
        writer = runs.ParquetStreamWriter(out_path, corpus_schema().with_metadata(meta))
        try:
            for chunk in chunks:
                local = np.flatnonzero(mask[chunk.start:chunk.end])
                if not len(local):
                    continue
                records = pq.read_table(run.records_dir / chunk.shard_stem / chunk.part_name)
                detector_label = (records.schema.metadata or {}).get(b"sonora_detector", b"").decode() or detector_label
                rec_iter = iter(records.take(pa.array(local)).to_pylist())
                del records
                out_rows = []
                for first_row, batch in genius.iter_rows(shard_files[shard], chunk.start, chunk.end, batch_size, ["lyrics"]):
                    lyrics = batch.column(0).to_pylist()
                    sel = np.flatnonzero(mask[first_row:first_row + len(lyrics)])
                    for offset in sel:
                        r = next(rec_iter)
                        row = first_row + int(offset)
                        if r["source_row_zero_based"] != row:
                            raise RuntimeError("Desalineación entre registros y Parquet original")
                        original = lyrics[offset]
                        views = build_views(original)
                        if sha256_hex(dedup_key(views.analysis)) != r["text_hash"]:
                            raise RuntimeError(f"Hash no reproducible para {r['source_key']}")
                        out_rows.append({
                            "lyrics_id": prefix + r["text_hash"][:width], "source_key": r["source_key"],
                            "source_file": shard, "source_row_zero_based": row,
                            "title": r["title"], "artist": r["artist"], "tag": r["tag"], "year": r["year"],
                            "lyrics_original": original, "lyrics_structural": views.structural,
                            "lyrics_analysis": views.analysis, "text_hash": r["text_hash"],
                            "text_sha256_original": r["text_sha256_original"],
                            "lang_top": r["lang_top"], "lang_top_conf": r["lang_top_conf"],
                            "lang_en_conf": r["lang_en_conf"], "lang_status": r["lang_status"],
                            "lang_reason": r["lang_reason"], "language_detector": detector_label,
                            **{k: r[k] for k in ("n_chars_original", "n_chars_analysis", "n_lines", "n_stanzas",
                                                 "n_section_markers", "n_words", "section_labels", "quality_flags")},
                            "n_source_records": int(counts[row]), "status": "accepted",
                        })
                writer.write(pa.Table.from_pylist(out_rows, schema=corpus_schema()))
                del out_rows
            writer.close()
        except BaseException:
            writer.abort()
            raise
        corpus_rows += writer.rows
        LOG.info("Corpus %s: %d letras canónicas", out_path.name, writer.rows)
    if corpus_rows != n_canonical:
        raise RuntimeError(f"Corpus con {corpus_rows} filas y {n_canonical} hashes canónicos")
    result = {
        "status": "complete", "finished_utc": runs.utc_now(), "seconds": round(time.time() - started, 1),
        "source_records": n_source, "status_counts": status_counts,
        "canonical_lyrics": n_canonical,
        "accepted_duplicates_consolidated": n_accepted - n_canonical,
        "peak_rss_bytes": runs.peak_rss_bytes(),
        "code_sha256": runs.code_fingerprint(code_files()),
    }
    run.update_manifest(stage_consolidate=result)
    return result


# --------------------------------------------------------------------------- split

class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        parent = self.parent
        root = item
        while parent[root] != root:
            root = parent[root]
        while parent[item] != root:
            parent[item], item = root, parent[item]
        return root

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            if ra < rb:
                self.parent[rb] = ra
            else:
                self.parent[ra] = rb


def assign_split(group_id: str, seed: int, fractions: dict[str, float]) -> str:
    digest = hashlib.sha256(f"{seed}:{group_id}".encode()).hexdigest()
    u = int(digest[:15], 16) / 16**15
    cumulative = 0.0
    for name in SPLITS:
        cumulative += fractions[name]
        if u < cumulative:
            return name
    return SPLITS[-1]


def _group_roots(lyrics_id, titles, artists, batch_rows: int = 200_000):
    """Union-find over lyrics_ids (arrow arrays of ACCEPTED source rows, one row per record).

    Returns ``(unique_sorted_ids, roots)`` where ``roots[i]`` is the index (in the sorted
    unique ids) of the smallest lyrics_id connected to ``unique_sorted_ids[i]``.
    Relation: same normalized artist + base title (exact duplicates already share an id).
    Memory: compact ``array('q')`` parents and 16-byte key digests, processed in batches.
    """
    from array import array

    import numpy as np
    import pyarrow.compute as pc

    unique = pc.unique(lyrics_id)
    unique = unique.take(pc.sort_indices(unique))
    index = pc.index_in(lyrics_id, value_set=unique).to_numpy(zero_copy_only=False)
    parent = array("q", range(len(unique)))

    def find(item: int) -> int:
        root = item
        while parent[root] != root:
            root = parent[root]
        while parent[item] != root:
            parent[item], item = root, parent[item]
        return root

    first_by_key: dict[bytes, int] = {}
    artist_cache: dict = {}
    n = len(lyrics_id)
    for start in range(0, n, batch_rows):
        t_batch = titles.slice(start, batch_rows).to_pylist()
        a_batch = artists.slice(start, batch_rows).to_pylist()
        for offset, (title, artist) in enumerate(zip(t_batch, a_batch)):
            a = artist_cache.get(artist)
            if a is None:
                a = artist_cache[artist] = normalize(artist)
            t = base_title(title)
            if not a or not t:
                continue
            key = hashlib.blake2b(f"{a}\x00{t}".encode(), digest_size=16).digest()
            i = int(index[start + offset])
            j = first_by_key.setdefault(key, i)
            if j != i:
                ri, rj = find(i), find(j)
                if ri != rj:
                    if ri < rj:
                        parent[rj] = ri
                    else:
                        parent[ri] = rj
    roots = np.fromiter((find(i) for i in range(len(unique))), dtype=np.int64, count=len(unique))
    return unique, roots, index


def build_groups(lyrics_ids: list[str], titles: list[str | None], artists: list[str | None]) -> dict[str, str]:
    """``lyrics_id -> group_id`` (convenience wrapper over :func:`_group_roots`)."""
    import pyarrow as pa

    unique, roots, _ = _group_roots(pa.array(lyrics_ids, pa.string()), pa.array(titles, pa.string()),
                                    pa.array(artists, pa.string()))
    ids = unique.to_pylist()
    return {lid: "grp_" + ids[int(r)].removeprefix("lyr_") for lid, r in zip(ids, roots)}


def split(run: Run) -> dict:
    import numpy as np
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    started = time.time()
    mapping_path = run.processed / "source_to_lyrics.parquet"
    if not mapping_path.exists():
        raise RuntimeError("Falta source_to_lyrics.parquet; ejecuta consolidate primero")
    cfg = run.config["split"]
    seed = int(cfg["seed"])
    fractions = cfg["fractions"]
    if abs(sum(fractions.values()) - 1) > 1e-9:
        raise ValueError("Las fracciones del split deben sumar 1")
    mapping = pq.read_table(mapping_path, columns=["lyrics_id", "title", "artist"],
                            filters=[("status", "=", "accepted")])
    unique, roots, index = _group_roots(mapping["lyrics_id"], mapping["title"], mapping["artist"])
    del mapping
    gc.collect()
    n = len(unique)
    src_count = np.bincount(index, minlength=n).astype(np.int32)
    group_roots, group_pos = np.unique(roots, return_inverse=True)
    group_size = np.bincount(group_pos).astype(np.int32)
    group_ids = pc.replace_substring_regex(unique.take(pa.array(group_roots)), "^lyr_", "grp_")
    codes = np.fromiter((SPLITS.index(assign_split(g, seed, fractions)) for g in group_ids.to_pylist()),
                        dtype=np.int8, count=len(group_roots))
    lyric_codes = codes[group_pos]
    table = pa.table({
        "lyrics_id": unique,
        "group_id": group_ids.take(pa.array(group_pos)),
        "split": pa.array(np.array(SPLITS, dtype=object)[lyric_codes], pa.string()),
        "group_size_lyrics": pa.array(group_size[group_pos], pa.int32()),
        "n_source_records": pa.array(src_count, pa.int32()),
    }).replace_schema_metadata({"sonora_ingest_hash": run.ingest_hash, "seed": str(seed)})
    runs.write_parquet_atomic(table, run.splits_dir / "lyrics_splits.parquet")
    n_groups = len(group_roots)
    by_split = {
        name: {"lyrics": int((lyric_codes == k).sum()), "groups": int((codes == k).sum()),
               "source_records": int(src_count[lyric_codes == k].sum())}
        for k, name in enumerate(SPLITS)
    }
    sizes, size_counts = np.unique(group_size, return_counts=True)
    largest = np.argsort(-group_size, kind="stable")[:10]
    summary = {
        "run_id": run.run_id, "seed": seed, "target_fractions": fractions,
        "assignment": "sha256(f'{seed}:{group_id}') -> uniforme [0,1) -> train/test/validation acumulado",
        "group_rules": cfg["group_rules"],
        "group_rule_notes": [
            "identical_normalized_text_hash: los duplicados exactos ya comparten lyrics_id.",
            "same_artist_and_base_title: artista normalizado igual y título sin sufijo de versión "
            "((Live), - Remix, etc.) igual; une versiones y títulos repetidos del mismo artista.",
            "No se detectan casi-duplicados por similitud ni covers con letra modificada (limitación).",
        ],
        "lyrics": n, "groups": n_groups,
        "by_split": by_split,
        "actual_fraction_lyrics": {s: round(v["lyrics"] / n, 5) if n else None for s, v in by_split.items()},
        "actual_fraction_groups": {s: round(v["groups"] / n_groups, 5) if n_groups else None
                                   for s, v in by_split.items()},
        "group_size_distribution": {str(int(k)): int(v) for k, v in list(zip(sizes, size_counts))[:20]},
        "group_size_max": int(group_size.max()) if n_groups else 0,
        "lyrics_in_groups_larger_than_1": int(group_size[group_pos].__gt__(1).sum()),
        "largest_groups": [{"group_id": group_ids[int(i)].as_py(), "lyrics": int(group_size[i])} for i in largest],
        "parquet": str((run.splits_dir / "lyrics_splits.parquet").relative_to(run.root)).replace("\\", "/"),
        "parquet_sha256": runs.file_sha256(run.splits_dir / "lyrics_splits.parquet"),
    }
    runs.write_json_atomic(run.root / "manifests" / "splits" / f"{run.run_id}.json", summary)
    result = {"status": "complete", "finished_utc": runs.utc_now(), "seconds": round(time.time() - started, 1),
              "lyrics": n, "groups": n_groups, "by_split": by_split, "peak_rss_bytes": runs.peak_rss_bytes()}
    run.update_manifest(stage_split=result)
    return result


# --------------------------------------------------------------------------- demo

def fma_audio_path(dirs: list[Path], track_id: str) -> Path | None:
    tid = f"{int(track_id):06d}"
    for base in dirs:
        candidate = base / tid[:3] / f"{tid}.mp3"
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def link_demo(run: Run) -> dict:
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    started = time.time()
    cfg = run.config["demo"]
    selection = json.loads((run.root / cfg["selection"]).read_text(encoding="utf-8"))
    rows = selection["rows"]
    if len(rows) != cfg["expected_count"] or selection.get("count") != cfg["expected_count"]:
        raise ValueError(f"Selección demo con {len(rows)} filas; se esperaban {cfg['expected_count']}")
    distinct = {r["genius_locator"] for r in rows}
    if len(distinct) != cfg["expected_distinct_genius_rows"]:
        raise ValueError(f"{len(distinct)} localizadores distintos; se esperaban {cfg['expected_distinct_genius_rows']}")
    if len({r["fma_track_id"] for r in rows}) != len(rows):
        raise ValueError("fma_track_id repetido en la selección demo")

    mapping = pq.read_table(run.processed / "source_to_lyrics.parquet",
                            filters=pc.field("source_key").isin(sorted(distinct)))
    by_key = {r["source_key"]: r for r in mapping.to_pylist()}
    splits_path = run.splits_dir / "lyrics_splits.parquet"
    wanted_ids = sorted({r["lyrics_id"] for r in by_key.values() if r["lyrics_id"]})
    splits = ({r["lyrics_id"]: r for r in pq.read_table(
        splits_path, filters=pc.field("lyrics_id").isin(wanted_ids)).to_pylist()}
        if splits_path.exists() and wanted_ids else {})
    audio_dirs = [run.root / d for d in cfg["fma_audio_dirs"]]
    existing_audio_dirs = [str(d.relative_to(run.root)).replace("\\", "/") for d in audio_dirs if d.is_dir()]

    out = []
    for r in rows:
        key = r["genius_locator"]
        if key != genius.locator(r["genius_file"], int(r["genius_row_zero_based"])):
            raise ValueError(f"Localizador inconsistente en la selección: {key}")
        src = by_key.get(key)
        reasons: list[str] = []
        if src is None:
            in_scope = False
            verified = None
            check = "locator_outside_processed_scope"
            reasons.append(check)
        else:
            in_scope = True
            title_ok = normalize(src["title"]) == normalize(r["fma_title"])
            artist_ok = normalize(src["artist"]) == normalize(r["fma_artist"])
            verified = title_ok and artist_ok
            check = "title_artist_normalized_equal" if verified else (
                "title_mismatch" if not title_ok and artist_ok else
                "artist_mismatch" if title_ok else "title_and_artist_mismatch")
            if not verified:
                reasons.append(f"locator_{check}")
        lyrics_id = src["lyrics_id"] if src else None
        status = src["status"] if src else None
        if src and status != "accepted":
            reasons.append(f"lyrics_{status}:{src['exclusion_rule']}")
        info = splits.get(lyrics_id) if lyrics_id else None
        audio = fma_audio_path(audio_dirs, r["fma_track_id"])
        has_lyrics = bool(verified and lyrics_id)
        if not audio:
            reasons.append("audio_file_not_found_locally")
        reasons.append("lyrics_not_human_validated")
        reasons.append("audio_not_decoded_or_validated")
        reasons.append("playback_license_not_verified")
        out.append({
            "fma_track_id": str(r["fma_track_id"]), "fma_title": r["fma_title"], "fma_artist": r["fma_artist"],
            "metadata_subset": r["metadata_subset"], "genre_top": r.get("genre_top"),
            "genius_locator": key, "genius_file": r["genius_file"],
            "genius_row_zero_based": int(r["genius_row_zero_based"]),
            "original_status": r["original_status"], "risk_flags": list(r.get("risk_flags") or []),
            "fma_tracks_in_source_group": int(r.get("fma_tracks_in_source_group") or 1),
            "provisional_source_group": r.get("lyrics_source_group"),
            "genius_title": src["title"] if src else None, "genius_artist": src["artist"] if src else None,
            "in_processed_scope": in_scope, "locator_verified": verified, "locator_check": check,
            "lyrics_status": status, "lyrics_exclusion_rule": src["exclusion_rule"] if src else None,
            "lyrics_id": lyrics_id,
            "group_id": info["group_id"] if info else None, "split": info["split"] if info else None,
            "retained_for_experiment": bool(r.get("retained_for_experiment", True)),
            "lyrics_validated": r.get("lyrics_validated"), "audio_validated": r.get("audio_validated"),
            "human_decision": r.get("human_decision"),
            "has_lyrics": has_lyrics, "has_text_vector": False, "has_audio_features": False,
            "has_audio_file": audio is not None,
            "audio_path": str(audio.relative_to(run.root)).replace("\\", "/") if audio else None,
            "playback_allowed": None,
            "catalog_eligible": False,
            "not_eligible_reasons": reasons,
        })
    schema = pa.schema([
        ("fma_track_id", pa.string()), ("fma_title", pa.string()), ("fma_artist", pa.string()),
        ("metadata_subset", pa.string()), ("genre_top", pa.string()), ("genius_locator", pa.string()),
        ("genius_file", pa.string()), ("genius_row_zero_based", pa.int64()), ("original_status", pa.string()),
        ("risk_flags", pa.list_(pa.string())), ("fma_tracks_in_source_group", pa.int32()),
        ("provisional_source_group", pa.string()), ("genius_title", pa.string()), ("genius_artist", pa.string()),
        ("in_processed_scope", pa.bool_()), ("locator_verified", pa.bool_()), ("locator_check", pa.string()),
        ("lyrics_status", pa.string()), ("lyrics_exclusion_rule", pa.string()), ("lyrics_id", pa.string()),
        ("group_id", pa.string()), ("split", pa.string()), ("retained_for_experiment", pa.bool_()),
        ("lyrics_validated", pa.bool_()), ("audio_validated", pa.bool_()), ("human_decision", pa.string()),
        ("has_lyrics", pa.bool_()), ("has_text_vector", pa.bool_()), ("has_audio_features", pa.bool_()),
        ("has_audio_file", pa.bool_()), ("audio_path", pa.string()), ("playback_allowed", pa.bool_()),
        ("catalog_eligible", pa.bool_()), ("not_eligible_reasons", pa.list_(pa.string())),
    ])
    table = pa.Table.from_pylist(out, schema=schema)
    runs.write_parquet_atomic(table.replace_schema_metadata({"sonora_ingest_hash": run.ingest_hash}),
                              run.demo_dir / "demo_links.parquet")
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(schema.names), lineterminator="\n")
    writer.writeheader()
    for row in out:
        writer.writerow({k: ("|".join(v) if isinstance(v, list) else v) for k, v in row.items()})
    runs.write_text_atomic(run.demo_dir / "demo_links.csv", buffer.getvalue())

    lyric_ids = {o["lyrics_id"] for o in out if o["lyrics_id"]}
    summary = {
        "selection_rows": len(out), "distinct_genius_locators": len(distinct),
        "in_processed_scope": sum(o["in_processed_scope"] for o in out),
        "locator_verified": sum(bool(o["locator_verified"]) for o in out),
        "locator_check": dict(Counter(o["locator_check"] for o in out)),
        "lyrics_status": dict(Counter(str(o["lyrics_status"]) for o in out)),
        "lyrics_exclusion_rule": dict(Counter(o["lyrics_exclusion_rule"] for o in out if o["lyrics_exclusion_rule"])),
        "has_lyrics": sum(o["has_lyrics"] for o in out),
        "distinct_lyrics_ids": len(lyric_ids),
        "recordings_per_lyrics_id_max": max(Counter(o["lyrics_id"] for o in out if o["lyrics_id"]).values(), default=0),
        "by_split_recordings": dict(Counter(str(o["split"]) for o in out)),
        "by_split_lyrics": dict(Counter(splits[l]["split"] for l in lyric_ids if l in splits)),
        "has_audio_file": sum(o["has_audio_file"] for o in out),
        "fma_audio_dirs_found": existing_audio_dirs,
        "original_status": dict(Counter(o["original_status"] for o in out)),
        "catalog_eligible": sum(o["catalog_eligible"] for o in out),
    }
    runs.write_json_atomic(run.demo_dir / "demo_summary.json", summary)
    result = {"status": "complete", "finished_utc": runs.utc_now(), "seconds": round(time.time() - started, 1), **summary}
    run.update_manifest(stage_demo=result)
    return result


# --------------------------------------------------------------------------- report

def _percentiles(values, qs=(0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1)) -> dict:
    import numpy as np

    arr = np.asarray(values)
    if not len(arr):
        return {}
    return {f"p{int(q * 100)}": float(np.quantile(arr, q)) for q in qs} | {"mean": float(arr.mean())}


def _value_counts(array, drop_null: bool = False) -> dict:
    """Arrow-side counting (no Python list of millions of strings). Null -> 'None'."""
    import pyarrow.compute as pc

    out = {}
    for item in pc.value_counts(array).to_pylist():
        if item["values"] is None and drop_null:
            continue
        out[str(item["values"])] = int(item["counts"])
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def report(run: Run) -> dict:
    import numpy as np
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    records = read_records(run, ["source_file", "status", "exclusion_rule", "lang_status", "lang_reason",
                                 "lang_secondary",
                                 "lang_top", "lang_en_conf", "quality_flags", "tag", "year", "n_words",
                                 "n_chars_original", "source_key"])
    n = records.num_rows
    status = _value_counts(records["status"])
    rules = _value_counts(records["exclusion_rule"], drop_null=True)
    reconciled = sum(status.values()) == n and set(status) <= {"accepted", "excluded", "review"}
    expected_rows = sum(c.end - c.start for _, c in plan_all_chunks(run))
    flags = _value_counts(pc.list_flatten(records["quality_flags"]))
    en_conf = records["lang_en_conf"].to_numpy(zero_copy_only=False)
    en_conf = en_conf[~np.isnan(en_conf.astype(float))] if len(en_conf) else en_conf
    hist, edges = np.histogram(en_conf.astype(float), bins=[0, .05, .2, .5, .8, .9, .95, .99, 1.0001])
    mapping = pq.read_table(run.processed / "source_to_lyrics.parquet",
                            columns=["status", "is_canonical", "matches_accepted_lyrics_id"])
    corpus_cols = ["n_words", "n_chars_original", "n_lines", "n_stanzas", "n_section_markers", "tag", "year",
                   "n_source_records", "section_labels"]
    corpus = pq.ParquetDataset(sorted(str(p) for p in (run.processed / "corpus").glob("*.parquet"))).read(columns=corpus_cols)
    accepted = records.filter(pc.equal(records["status"], "accepted"))
    canonical = corpus.num_rows
    labels = Counter(_value_counts(pc.list_flatten(corpus["section_labels"])))
    year = corpus["year"].to_numpy()
    split_summary_path = run.root / "manifests" / "splits" / f"{run.run_id}.json"
    demo_summary_path = run.demo_dir / "demo_summary.json"
    rep = {
        "run_id": run.run_id,
        "generated_utc": runs.utc_now(),
        "universe": "corpus completo (10 shards, todas las filas)" if run.scope.is_full
                    else f"SUBCONJUNTO de prueba: {run.scope.as_dict()} — NO es el corpus completo",
        "scope_is_full_corpus": run.scope.is_full,
        "source_records_read": n, "source_records_expected_in_scope": expected_rows,
        "reconciled": bool(reconciled and n == expected_rows),
        "status_counts": dict(status), "exclusion_or_review_rule_counts": dict(rules),
        "language_status_counts": _value_counts(records["lang_status"]),
        "language_reason_counts": _value_counts(records["lang_reason"]),
        "detected_top_language_counts_top20": dict(Counter(_value_counts(records["lang_top"])).most_common(20)),
        "secondary_detector_runs": int(pc.sum(pc.is_valid(records["lang_secondary"])).as_py() or 0),
        "secondary_language_counts_top20": dict(Counter(
            _value_counts(records["lang_secondary"], drop_null=True)).most_common(20)),
        "english_confidence_histogram": {f"[{edges[i]:.2f},{min(edges[i + 1], 1):.2f})": int(hist[i]) for i in range(len(hist))},
        "quality_flag_counts": dict(flags),
        "accepted_source_records": accepted.num_rows,
        "canonical_lyrics": canonical,
        "accepted_duplicate_source_records": accepted.num_rows - canonical,
        "non_accepted_records_matching_an_accepted_text": int(pc.sum(pc.is_valid(mapping["matches_accepted_lyrics_id"])).as_py() or 0),
        "canonical_lyrics_with_duplicates": int(pc.sum(pc.greater(corpus["n_source_records"], 1)).as_py() or 0),
        "canonical_n_words": _percentiles(corpus["n_words"].to_numpy()),
        "canonical_n_chars_original": _percentiles(corpus["n_chars_original"].to_numpy()),
        "canonical_n_lines": _percentiles(corpus["n_lines"].to_numpy()),
        "canonical_n_stanzas": _percentiles(corpus["n_stanzas"].to_numpy()),
        "canonical_with_section_markers": int(pc.sum(pc.greater(corpus["n_section_markers"], 0)).as_py() or 0),
        "canonical_total_words": int(pc.sum(corpus["n_words"]).as_py() or 0),
        "canonical_tag_counts": _value_counts(corpus["tag"]),
        "canonical_year": {"min": int(year.min()) if len(year) else None, "max": int(year.max()) if len(year) else None,
                           "below_1900": int((year < 1900).sum()), "decades": {
                               str(d): int(c) for d, c in sorted(Counter((year // 10 * 10)[year >= 1900].tolist()).items())}},
        "section_label_top30": dict(labels.most_common(30)),
        "split": json.loads(split_summary_path.read_text(encoding="utf-8")) if split_summary_path.exists() else None,
        "demo": json.loads(demo_summary_path.read_text(encoding="utf-8")) if demo_summary_path.exists() else None,
    }
    rep["language_audit_sample"] = _language_audit_sample(run, records)
    run.report_dir.mkdir(parents=True, exist_ok=True)
    runs.write_json_atomic(run.report_dir / "quality_report.json", rep)
    runs.write_text_atomic(run.report_dir / "quality_report.md", render_report_md(rep))
    manifest = run.load_manifest()
    stages = manifest.get("stages", {})
    complete = run.scope.is_full and rep["reconciled"] and all(
        stages.get(s, {}).get("status") == "complete" for s in ("ingest", "consolidate", "split", "demo"))
    outputs = {}
    for path in [run.processed / "source_to_lyrics.parquet", run.processed / "exclusions.parquet",
                 run.splits_dir / "lyrics_splits.parquet", run.demo_dir / "demo_links.parquet",
                 *sorted((run.processed / "corpus").glob("*.parquet"))]:
        if path.exists():
            outputs[str(path.relative_to(run.root)).replace("\\", "/")] = {
                "bytes": path.stat().st_size, "rows": pq.ParquetFile(path).metadata.num_rows}
    run.update_manifest(stage_report={"status": "complete", "finished_utc": runs.utc_now(),
                                      "reconciled": rep["reconciled"]},
                        outputs=outputs, complete_full_corpus_run=bool(complete))
    return rep


def _language_audit_sample(run: Run, records) -> dict:
    """Reproducible sample for manual language audit; excerpts stay under data/ (not in Git).
    Selection: ``numpy.random.default_rng(seed).choice`` over records ordered by (shard, row)."""
    import numpy as np
    import pyarrow as pa
    import pyarrow.compute as pc

    cfg = run.config["audit"]
    seed = cfg["seed"]
    picks = []
    for label, mask, size in [
        ("accepted", pc.equal(records["status"], "accepted"), cfg["accepted_sample"]),
        ("uncertain", pc.equal(records["lang_status"], "uncertain"), cfg["uncertain_sample"]),
        ("non_english", pc.equal(records["lang_status"], "non_en"), cfg["non_english_sample"]),
    ]:
        keys = records.filter(pc.fill_null(mask, False))["source_key"]
        take = min(size, len(keys))
        chosen = sorted(np.random.default_rng(seed).choice(len(keys), size=take, replace=False).tolist()) if take else []
        picks += [(label, k) for k in keys.take(pa.array(chosen, pa.int64())).to_pylist()]
    by_file: dict[str, list[int]] = {}
    for _, key in picks:
        name, row = key.split("#row=")
        by_file.setdefault(name, []).append(int(row))
    shard_files = {p.name: p for p in run.shard_paths()}
    texts = {}
    for name, rows in by_file.items():
        got = genius.read_rows_at(shard_files[name], rows, ["title", "artist", "lyrics"])
        for row, value in got.items():
            texts[genius.locator(name, row)] = value
    rec_by_key = {r["source_key"]: r for r in records.filter(
        pc.is_in(records["source_key"], value_set=pa.array([k for _, k in picks], pa.string()))).to_pylist()}
    limit = cfg["excerpt_chars"]
    rows = []
    for label, key in picks:
        value = texts[key]
        rec = rec_by_key[key]
        rows.append({
            "sample": label, "source_key": key, "title": value["title"], "artist": value["artist"],
            "lang_top": rec["lang_top"], "lang_en_conf": rec["lang_en_conf"],
            "lang_secondary": rec["lang_secondary"], "lang_reason": rec["lang_reason"],
            "excerpt_analysis": build_views(value["lyrics"]).analysis[:limit] if value["lyrics"] else "",
            "human_language": None, "human_notes": None,
        })
    if rows:
        runs.write_parquet_atomic(pa.Table.from_pylist(rows), run.processed / "language_audit_sample.parquet")
    return {"seed": seed, "sizes": dict(Counter(label for label, _ in picks)),
            "path": str((run.processed / "language_audit_sample.parquet").relative_to(run.root)).replace("\\", "/"),
            "human_review_done": False}


def render_report_md(rep: dict) -> str:
    def table(d: dict, h=("Clave", "Cantidad")) -> str:
        lines = [f"| {h[0]} | {h[1]} |", "|---|---:|"]
        lines += [f"| {k} | {v:,} |" if isinstance(v, int) else f"| {k} | {v} |" for k, v in d.items()]
        return "\n".join(lines)

    split = rep.get("split") or {}
    demo = rep.get("demo") or {}
    parts = [
        f"# Reporte de calidad del corpus de letras — `{rep['run_id']}`",
        "",
        f"Generado: {rep['generated_utc']} (UTC). Universo: **{rep['universe']}**.",
        "Todos los conteos proceden de la ejecución indicada sobre los Parquet Genius locales; "
        "no son fixtures de prueba.",
        "",
        "## Reconciliación",
        "",
        f"Registros de origen leídos: {rep['source_records_read']:,}; esperados en el alcance: "
        f"{rep['source_records_expected_in_scope']:,}. Reconciliado: **{rep['reconciled']}**.",
        "",
        table(rep["status_counts"], ("Estado", "Registros")),
        "",
        "## Exclusiones y revisión por regla",
        "",
        table(rep["exclusion_or_review_rule_counts"], ("Regla", "Registros")),
        "",
        "## Idioma (lingua, vista de análisis sin marcadores de sección)",
        "",
        table(rep["language_status_counts"], ("Estado de idioma", "Registros")),
        "",
        table(rep["language_reason_counts"], ("Motivo", "Registros")),
        "",
        table(rep["english_confidence_histogram"], ("Confianza inglés", "Registros")),
        "",
        table(rep["detected_top_language_counts_top20"], ("Idioma más probable", "Registros")),
        "",
        "## Duplicados y corpus canónico",
        "",
        table({
            "Registros aceptados": rep["accepted_source_records"],
            "Letras canónicas (lyrics_id)": rep["canonical_lyrics"],
            "Registros aceptados consolidados como duplicado": rep["accepted_duplicate_source_records"],
            "Letras canónicas con más de un registro": rep["canonical_lyrics_with_duplicates"],
            "No aceptados cuyo texto coincide con una letra aceptada": rep["non_accepted_records_matching_an_accepted_text"],
            "Palabras totales (vista de análisis, canónicas)": rep["canonical_total_words"],
            "Canónicas con marcadores de sección": rep["canonical_with_section_markers"],
        }),
        "",
        "## Longitudes (letras canónicas)",
        "",
        "| Medida | " + " | ".join(rep["canonical_n_words"].keys()) + " |",
        "|---|" + "---:|" * len(rep["canonical_n_words"]),
    ]
    for name in ("canonical_n_words", "canonical_n_chars_original", "canonical_n_lines", "canonical_n_stanzas"):
        parts.append(f"| {name.removeprefix('canonical_')} | " + " | ".join(f"{v:,.0f}" for v in rep[name].values()) + " |")
    parts += [
        "",
        "## Grupos comparables (DAT-03)",
        "",
        table(rep["canonical_tag_counts"], ("tag", "Letras")),
        "",
        table(rep["canonical_year"]["decades"], ("Década", "Letras")),
        "",
        f"Años < 1900 (dato de origen dudoso): {rep['canonical_year']['below_1900']:,}.",
        "",
        "## Banderas de calidad",
        "",
        table(rep["quality_flag_counts"], ("Bandera", "Registros")),
        "",
        "## Marcadores de sección más frecuentes",
        "",
        table(rep["section_label_top30"], ("Etiqueta", "Apariciones")),
    ]
    if split:
        parts += ["", "## Split por grupos", "",
                  f"Semilla {split['seed']}; objetivo {split['target_fractions']}; {split['lyrics']:,} letras en "
                  f"{split['groups']:,} grupos.", "",
                  "| Partición | Letras | Grupos | Registros de origen | Fracción real (letras) |",
                  "|---|---:|---:|---:|---:|"]
        for s, v in split["by_split"].items():
            parts.append(f"| {s} | {v['lyrics']:,} | {v['groups']:,} | {v['source_records']:,} | "
                         f"{split['actual_fraction_lyrics'][s]} |")
    if demo:
        parts += ["", "## Cobertura de la demo (FMA Medium, 886 exactas retenidas)", "",
                  table({k: v for k, v in demo.items() if not isinstance(v, (dict, list))}), "",
                  "Estado de letras: " + json.dumps(demo["lyrics_status"], ensure_ascii=False), "",
                  "Reglas de exclusión: " + json.dumps(demo["lyrics_exclusion_rule"], ensure_ascii=False), "",
                  "Grabaciones por split: " + json.dumps(demo["by_split_recordings"], ensure_ascii=False), "",
                  f"Carpetas de audio FMA encontradas: {demo['fma_audio_dirs_found'] or 'ninguna'}.",
                  "`catalog_eligible` permanece en falso hasta validar letra/audio y licencia de reproducción."]
    audit = rep["language_audit_sample"]
    parts += ["", "## Auditoría de idioma", "",
              f"Muestra reproducible (semilla {audit['seed']}): {audit['sizes']} en `{audit['path']}`. "
              "Revisión humana pendiente: no se reporta exactitud del detector."]
    return "\n".join(parts) + "\n"
