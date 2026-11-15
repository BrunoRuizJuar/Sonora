"""End-to-end checks of the corpus pipeline on SYNTHETIC shards (tests/conftest.py)."""
from __future__ import annotations

import json

import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest

from conftest import fake_detectors, make_run
from sonora.ingestion import genius, lyrics_corpus as lc
from sonora.storage import runs


def _ingest(run, **kw):
    return lc.ingest(run, fake_detectors, hash_inputs=False, **kw)


def _all_records(run):
    return lc.read_records(run).sort_by([("source_file", "ascending"), ("source_row_zero_based", "ascending")])


def test_iter_rows_global_locators_independent_of_batch(project):
    root, _ = project
    path = root / "data" / "raw" / "genius" / "train-00001-of-00003.parquet"
    full = pq.read_table(path)["title"].to_pylist()
    for batch_size in (1, 5, 13, 1000):
        got = []
        for first, batch in genius.iter_rows(path, 27, 71, batch_size, ["title"]):
            got.extend((first + i, t) for i, t in enumerate(batch.column(0).to_pylist()))
        assert got == [(i, full[i]) for i in range(27, 71)]
    assert genius.read_rows_at(path, [0, 94, 40], ["title"])[94]["title"] == full[94]


def test_batch_size_does_not_change_records(project):
    root, config = project
    a = make_run(root, config, "a")
    b = make_run(root, config, "b")
    assert _ingest(a, batch_size=7)["status"] == "complete"
    assert _ingest(b, batch_size=500)["status"] == "complete"
    assert _all_records(a).equals(_all_records(b))


def test_interrupt_and_resume_without_duplicates(project):
    root, config = project
    reference = make_run(root, config, "ref")
    _ingest(reference)
    run = make_run(root, config, "resume")
    first = _ingest(run, max_chunks=2)
    assert first["status"] == "incomplete" and first["chunks_written_this_session"] == 2
    # leftover temp file from a crash must not be treated as a finished part
    stray = run.records_dir / "train-00001-of-00003" / "part-00000.parquet.tmp"
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_bytes(b"partial")
    with pytest.raises(RuntimeError, match="incompleta"):
        lc.consolidate(run)
    second = _ingest(run)
    assert second["status"] == "complete"
    assert second["chunks_written_this_session"] == first["chunks_total"] - 2
    assert not stray.exists()
    third = _ingest(run)
    assert third["chunks_written_this_session"] == 0
    records = _all_records(run)
    assert records.num_rows == 120 + 95 + 101
    assert pc.count_distinct(records["source_key"]).as_py() == records.num_rows
    assert records.equals(_all_records(reference))


def test_resume_refuses_other_config(project):
    root, config = project
    run = make_run(root, config, "cfg")
    _ingest(run, max_chunks=1)
    config2 = json.loads(json.dumps(config))
    config2["quality"]["min_words"] = 6
    with pytest.raises(ValueError, match="otra configuración"):
        _ingest(make_run(root, config2, "cfg"))


def test_full_pipeline_reconciles(project):
    root, config = project
    run = make_run(root, config, "full")
    _ingest(run)
    cons = lc.consolidate(run)
    records = _all_records(run)
    status = dict(zip(*[records[c].to_pylist() for c in ("source_key", "status")]))
    rules = dict(zip(*[records[c].to_pylist() for c in ("source_key", "exclusion_rule")]))
    assert rules["train-00000-of-00003.parquet#row=3"] == "non_english"
    assert rules["train-00000-of-00003.parquet#row=5"] == "empty_lyrics"
    assert rules["train-00000-of-00003.parquet#row=7"] == "too_few_words"
    assert status["train-00000-of-00003.parquet#row=11"] == "accepted"
    assert sum(cons["status_counts"].values()) == records.num_rows == 316

    mapping = pq.read_table(run.processed / "source_to_lyrics.parquet")
    assert mapping.num_rows == records.num_rows
    acc = mapping.filter(pc.equal(mapping["status"], "accepted"))
    assert pc.all(pc.is_valid(acc["lyrics_id"])).as_py()
    # exact duplicates (rows with g % 31 == 11) share one lyrics_id; the first is canonical
    dup = mapping.filter(pc.equal(mapping["consolidation_reason"], "identical_normalized_text_hash"))
    assert dup.num_rows >= 8
    assert len(set(dup["lyrics_id"].to_pylist())) == 1

    corpus = pq.ParquetDataset([str(p) for p in (run.processed / "corpus").glob("*.parquet")]).read()
    assert corpus.num_rows == cons["canonical_lyrics"] == len(set(acc["lyrics_id"].to_pylist()))
    raw = {genius.locator(p.name, i): t for p in (root / "data/raw/genius").glob("*.parquet")
           for i, t in enumerate(pq.read_table(p)["lyrics"].to_pylist())}
    for row in corpus.to_pylist():
        assert row["lyrics_original"] == raw[row["source_key"]]  # original preserved byte-for-byte
        assert "[" not in row["lyrics_analysis"]
    excl = pq.read_table(run.processed / "exclusions.parquet")
    assert excl.num_rows == records.num_rows - acc.num_rows
    assert pc.all(pc.is_valid(excl["exclusion_rule"])).as_py()

    sp = lc.split(run)
    splits = pq.read_table(run.splits_dir / "lyrics_splits.parquet")
    assert splits.num_rows == corpus.num_rows
    per_group = {}
    for g, s in zip(splits["group_id"].to_pylist(), splits["split"].to_pylist()):
        per_group.setdefault(g, set()).add(s)
    assert all(len(v) == 1 for v in per_group.values())
    assert sum(v["lyrics"] for v in sp["by_split"].values()) == splits.num_rows

    demo = lc.link_demo(run)
    links = {r["fma_track_id"]: r for r in pq.read_table(run.demo_dir / "demo_links.parquet").to_pylist()}
    assert demo["selection_rows"] == 5 and len(links) == 5
    assert links["1"]["lyrics_id"] == links["2"]["lyrics_id"] is not None  # one Genius row, two recordings
    assert links["1"]["split"] == links["2"]["split"]
    assert links["3"]["locator_verified"] and links["3"]["has_audio_file"] and links["3"]["has_lyrics"]
    assert links["4"]["locator_verified"] is False and links["4"]["locator_check"] == "title_mismatch"
    assert links["5"]["lyrics_status"] == "excluded" and links["5"]["lyrics_id"] is None
    assert not any(r["catalog_eligible"] for r in links.values())
    assert links["3"]["playback_allowed"] is None

    rep = lc.report(run)
    assert rep["reconciled"] is True
    assert rep["status_counts"]["accepted"] + rep["status_counts"].get("excluded", 0) + \
        rep["status_counts"].get("review", 0) == 316
    assert (run.report_dir / "quality_report.md").exists()
    manifest = json.loads(run.manifest_path.read_text(encoding="utf-8"))
    assert manifest["complete_full_corpus_run"] is True  # synthetic scope = all synthetic shards


def test_subset_scope_is_never_marked_complete(project):
    root, config = project
    scope = lc.Scope(shards=["train-00000-of-00003"], row_limit_per_shard=50)
    run = make_run(root, config, "sub", scope)
    _ingest(run)
    lc.consolidate(run)
    lc.split(run)
    lc.link_demo(run)
    rep = lc.report(run)
    assert rep["source_records_read"] == 50 and rep["scope_is_full_corpus"] is False
    assert json.loads(run.manifest_path.read_text(encoding="utf-8"))["complete_full_corpus_run"] is False


def test_groups_merge_related_versions():
    groups = lc.build_groups(
        ["lyr_a", "lyr_b", "lyr_c", "lyr_d", "lyr_a"],
        ["Halo", "Halo (Live)", "Other", "Halo", "Cover Name"],
        ["Beyoncé", "Beyoncé", "Beyoncé", "Someone Else", "Band"],
    )
    assert groups["lyr_a"] == groups["lyr_b"]
    assert groups["lyr_c"] != groups["lyr_a"]
    assert groups["lyr_d"] != groups["lyr_a"]  # same title, different artist: not merged


def test_split_assignment_is_deterministic_and_close_to_target():
    fractions = {"train": 0.7, "test": 0.2, "validation": 0.1}
    names = [lc.assign_split(f"grp_{i}", 42, fractions) for i in range(20000)]
    assert names == [lc.assign_split(f"grp_{i}", 42, fractions) for i in range(20000)]
    for split, target in fractions.items():
        assert abs(names.count(split) / len(names) - target) < 0.015


def test_lock_prevents_second_writer(tmp_path):
    lock = tmp_path / "x.lock"
    with runs.run_lock(lock):
        with pytest.raises(runs.LockError):
            with runs.run_lock(lock):
                pass
    assert not lock.exists()
