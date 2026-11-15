"""Annotation helpers on SYNTHETIC texts (real spaCy model, invented lines)."""
import numpy as np
import pytest

from sonora.nlp import annotate as an
from sonora.nlp.lexicon import GDROP_SURFACE, WORD


def test_shadow_text_same_length_and_guarded():
    forms = frozenset({"running", "nothing", "living"})
    text = "Runnin' and livin', nothin' but rain' again'\nRUNNIN' fast"
    shadow, n = an.shadow_text(text, forms)
    assert len(shadow) == len(text)
    assert shadow == "Running and living, nothing but rain' again'\nRUNNING fast"
    assert n == 4


def test_lexicon_patterns():
    assert WORD.findall("i don't wanna, y'all 2 nothin' rock-n-roll") == \
        ["i", "don't", "wanna", "y'all", "nothin", "rock", "n", "roll"]
    assert [m.group(1) for m in GDROP_SURFACE.finditer("runnin' 'til the rain' nothin'")] == ["runnin", "rain", "nothin"]


def test_depths():
    #   0 <- 1 (root) -> 2 -> 3 ; 4 is its own root
    heads = np.array([1, 1, 1, 2, 4])
    assert an.depths(heads).tolist() == [1, 0, 1, 2, 0]


@pytest.fixture(scope="module")
def worker():
    pytest.importorskip("spacy")
    an._init_worker("en_core_web_sm", ["running", "nothing"], "1")


def test_annotate_texts_lines_stanzas_and_surface(worker):
    text = "I don't wanna go\nKeep runnin' now\n\nNothin' left for me tonight"
    tokens, sents, docs = an.annotate_texts(["lyr_x"], [text])
    rows = tokens.to_pylist()
    assert "".join(r["text"] for r in rows).replace(" ", "") == text.replace(" ", "").replace("\n", "")
    assert {r["text"] for r in rows} >= {"runnin'", "Nothin'", "n't"}
    run = next(r for r in rows if r["text"] == "runnin'")
    assert run["gdrop_normalized"] and run["lemma"] == "run" and run["upos"] == "VERB"
    neg = next(r for r in rows if r["text"] == "n't")
    assert neg["lemma"] == "not"
    assert max(r["line_i"] for r in rows) == 3          # blank line counts as a line
    assert {r["stanza_i"] for r in rows} == {0, 1}
    # a forced boundary at every line break: no sentence spans two lines
    lines_per_sent = {}
    for r in rows:
        lines_per_sent.setdefault(r["sent_i"], set()).add(r["line_i"])
    assert all(len(v) == 1 for v in lines_per_sent.values())
    d = docs.to_pylist()[0]
    assert d["n_lines"] == 3 and d["n_stanzas"] == 2 and d["n_gdrop_normalized"] == 2
    assert sents.num_rows >= 3
    assert all(s["depth"] >= 0 for s in sents.to_pylist())
