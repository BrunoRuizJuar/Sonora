"""n-gram counting on SYNTHETIC corpus files."""
from collections import Counter

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from sonora.nlp import ngrams as ng


def test_line_tokens_and_boundaries():
    assert ng.line_tokens("I don't know\n\nNa-na, OH\n") == [["i", "don't", "know"], ["na", "na", "oh"]]
    c = Counter()
    n = ng.count_lines([["a", "b"], ["c"]], "test", c, 3, lm_markers=False)
    assert n == 3
    assert c[(2, "test", "a b")] == 1 and (2, "test", "b c") not in c  # no cross-verse n-gram
    assert not any("<s>" in k[2] for k in c)
    c2 = Counter()
    ng.count_lines([["a", "b"], ["c"]], "train", c2, 3, lm_markers=True)
    assert c2[(1, "train", "</s>")] == 2
    assert c2[(3, "train", "<s> <s> a")] == 1 and c2[(3, "train", "<s> a b")] == 1
    assert c2[(3, "train", "a b </s>")] == 1 and c2[(3, "train", "<s> c </s>")] == 1


def test_count_corpus_end_to_end(tmp_path):
    corpus = tmp_path / "corpus"; corpus.mkdir()
    texts = [["Oh yeah\nOh yeah oh", "I love you\nyou love me"], ["oh yeah", "love love love"]]
    ids = [["lyr_1", "lyr_2"], ["lyr_3", "lyr_4"]]
    for k, (t, i) in enumerate(zip(texts, ids)):
        pq.write_table(pa.table({"lyrics_id": i, "lyrics_analysis": t}), corpus / f"s{k}.parquet")
    pq.write_table(pa.table({"lyrics_id": ["lyr_1", "lyr_2", "lyr_3", "lyr_4"],
                             "split": ["train", "test", "train", "validation"]}), tmp_path / "splits.parquet")
    summary = ng.count_corpus(sorted(corpus.glob("*.parquet")), tmp_path / "splits.parquet", tmp_path / "work",
                              workers=1, spill_entries=3, n_partitions=4)
    assert summary["totals_by_split"]["train"]["tokens"] == 5 + 2
    t = ds.dataset(tmp_path / "work" / "counts").to_table()
    def get(order, split, gram):
        f = t.filter(pc.and_(pc.and_(pc.equal(t["order"], order), pc.equal(t["split"], split)), pc.equal(t["ngram"], gram)))
        return sum(f["count"].to_pylist())
    assert get(1, "train", "oh") == 4 and get(2, "train", "oh yeah") == 3
    assert get(1, "test", "love") == 2 and get(1, "validation", "love") == 3
    assert get(2, "validation", "love love") == 2
    assert get(1, "test", "</s>") == 0 and get(1, "train", "</s>") == 3
    # rerun is idempotent (done markers + existing reduced partitions)
    again = ng.count_corpus(sorted(corpus.glob("*.parquet")), tmp_path / "splits.parquet", tmp_path / "work",
                            workers=1, spill_entries=3, n_partitions=4)
    assert again["rows"] == summary["rows"]
