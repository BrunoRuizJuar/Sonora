"""Parsing of KenLM `query -v summary` output (SYNTHETIC text, no KenLM needed)."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipelines" / "nlp"))
import ngram_lm  # noqa: E402


def test_parse_query_does_not_confuse_perplexity_line_with_oov_count():
    text = ("This binary file contains trie.\n"
            "Perplexity including OOVs:\t153.52\nPerplexity excluding OOVs:\t150.1\n"
            "OOVs:\t7\nTokens:\t1000\nName:query\tVmPeak:1 kB\n")
    r = ngram_lm.parse_query(text)
    assert r == {"ppl_incl_oov": 153.52, "ppl_excl_oov": 150.1, "kenlm_oovs": 7, "tokens_incl_eos": 1000}


def test_parse_query_missing_fields_are_none():
    assert ngram_lm.parse_query("nothing here")["kenlm_oovs"] is None
