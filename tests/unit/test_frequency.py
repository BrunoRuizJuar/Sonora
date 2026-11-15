"""Frequency aggregates (E2) on SYNTHETIC data only."""
import json

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from sonora.nlp import frequency as fq
from sonora.nlp import ngrams as ng


def test_decade_and_patterns():
    assert fq.decade_of(1999) == 1990 and fq.decade_of(1899) is None and fq.decade_of(None) is None
    assert fq.REPEATED_SYLLABLE.match("nanana") and fq.REPEATED_SYLLABLE.match("lala")
    assert not fq.REPEATED_SYLLABLE.match("love")
    assert fq.ELONGATED.search("ooooh") and not fq.ELONGATED.search("good")


def test_vocable_candidates_uses_only_requested_split():
    t = pa.table({
        "split": ["train", "train", "train", "train", "validation", "train"],
        "lower": ["oh", "oh", "love", "nanana", "zzz", "please"],
        "lemma": ["oh", "oh", "love", "nanana", "zzz", "please"],
        "upos": ["INTJ", "PROPN", "NOUN", "PROPN", "INTJ", "INTJ"],
        "count": [150, 50, 900, 120, 500, 40],
    })
    rows = {r["form"]: r for r in fq.vocable_candidates(t, min_count=100)}
    assert set(rows) == {"oh", "nanana"}           # zzz only in validation; please below threshold
    assert rows["oh"]["intj_share"] == 0.75 and rows["oh"]["reasons"] == ["intj_majority"]
    assert rows["nanana"]["reasons"] == ["repeated_syllable"]


def _write_counts(tmp_path):
    corpus = tmp_path / "corpus"; corpus.mkdir()
    pq.write_table(pa.table({"lyrics_id": ["a", "b", "c"], "tag": ["pop", "rap", "pop"], "year": [1995, 2011, 1800],
                             "lyrics_analysis": ["Oh yeah\nI love you", "love love you", "oh oh"]}),
                   corpus / "s0.parquet")
    pq.write_table(pa.table({"lyrics_id": ["a", "b", "c"], "split": ["train", "validation", "train"]}),
                   tmp_path / "splits.parquet")
    ng.count_corpus([corpus / "s0.parquet"], tmp_path / "splits.parquet", tmp_path / "ng", workers=1,
                    spill_entries=5, n_partitions=3)
    return corpus


def test_ngram_summary_reconciles_and_filters(tmp_path):
    _write_counts(tmp_path)
    fq.ngram_summary(tmp_path / "ng" / "counts", {"oh", "yeah", "i", "you"}, tmp_path / "s.json", top_k=5, workers=1)
    s = json.loads((tmp_path / "s.json").read_text(encoding="utf-8"))["orders"]
    assert s["1"]["all"]["tokens"] == 10                        # no </s> in descriptive counts
    assert s["1"]["train"]["tokens"] == 7 and s["1"]["validation"]["tokens"] == 3
    assert dict(s["1"]["all"]["top"])["love"] == 3 and dict(s["1"]["all"]["top"])["oh"] == 3
    assert [g for g, _ in s["1"]["all"]["top_content"]] == ["love"]
    assert dict(s["2"]["all"]["top"])["oh oh"] == 1 and not any("<s>" in g for g, _ in s["2"]["all"]["top"])
    assert sum(int(k) * v for k, v in s["1"]["all"]["spectrum_le1000"].items()) == 10


def test_group_unigrams(tmp_path):
    corpus = _write_counts(tmp_path)
    fq.group_unigrams([corpus / "s0.parquet"], tmp_path / "g", workers=1)
    t = pq.read_table(tmp_path / "g" / "group_unigrams.parquet")
    get = {(k, g, w): c for k, g, w, c in zip(*(t[c].to_pylist() for c in ("kind", "group", "word", "count")))}
    assert get[("tag", "pop", "oh")] == 3 and get[("tag", "rap", "love")] == 2
    assert get[("decade", "1990", "love")] == 1 and ("decade", "1800", "oh") not in get  # dubious year skipped


def test_export_lm_text_maps_oov_and_skips_test(tmp_path):
    corpus = _write_counts(tmp_path)
    (tmp_path / "vocab.txt").write_text("oh\nlove\nyou", encoding="utf-8")
    r = fq.export_lm_text([corpus / "s0.parquet"], tmp_path / "ng" / "aligned_splits", tmp_path / "lm",
                          tmp_path / "vocab.txt", workers=1)
    train = (tmp_path / "lm" / "shards" / "train.s0.txt").read_text(encoding="utf-8").splitlines()
    assert train == ["oh <oov>", "<oov> love you", "oh oh"]
    assert (tmp_path / "lm" / "shards" / "validation.rap.s0.txt").read_text(encoding="utf-8") == "love love you\n"
    assert r["totals"]["train"]["mapped_oov"] == 2
    assert not list((tmp_path / "lm").rglob("*.tmp"))


def test_shard_pos_counts(tmp_path):
    shard = tmp_path / "ann" / "tokens" / "s0"; shard.mkdir(parents=True)
    d = pa.dictionary(pa.int32(), pa.string())
    for i, (ids, rng) in enumerate([(["a", "a", "b"], "0:2"), (["c"], "2:3")]):
        n = len(ids)
        t = pa.table({"lyrics_id": pa.array(ids).cast(d), "lower": pa.array(["oh", "love", "oh"][:n]).cast(d),
                      "lemma": pa.array(["oh", "love", "oh"][:n]).cast(d), "upos": pa.array(["INTJ", "NOUN", "INTJ"][:n]).cast(d)})
        pq.write_table(t.replace_schema_metadata({"sonora_range": rng}), shard / f"part-{i:05d}.parquet")
    pq.write_table(pa.table({"lyrics_id": ["a", "b", "c"], "split": ["train", "test", "train"]}), tmp_path / "al.parquet")
    pq.write_table(pa.table({"lyrics_id": ["a", "b", "c"], "tag": ["pop", "rap", "pop"], "year": [1995, 2001, None]},
                            schema=pa.schema([("lyrics_id", pa.string()), ("tag", pa.string()), ("year", pa.int64())])),
                   tmp_path / "ds.parquet")
    r = fq._shard_pos_counts((shard, tmp_path / "al.parquet", tmp_path / "ds.parquet", tmp_path / "out"))
    assert r["tokens"] == 4
    w = pq.read_table(tmp_path / "out" / "word_pos" / "s0.parquet")
    got = {(s, l, u): c for s, l, u, c in zip(w["split"].to_pylist(), w["lower"].to_pylist(), w["upos"].to_pylist(), w["count"].to_pylist())}
    assert got == {("train", "oh", "INTJ"): 2, ("train", "love", "NOUN"): 1, ("test", "oh", "INTJ"): 1}
    g = pq.read_table(tmp_path / "out" / "group_pos" / "s0.parquet")
    assert int(pc.sum(g.filter(pc.is_null(g["decade"]))["count"]).as_py()) == 1   # doc c: no year
    assert fq._shard_pos_counts((shard, tmp_path / "al.parquet", tmp_path / "ds.parquet", tmp_path / "out"))["skipped"]
