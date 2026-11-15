"""Per-lyric statistics on SYNTHETIC strings."""
from sonora.nlp.doc_stats import line_key, stats_for
from sonora.preprocessing.lyrics_text import build_views


def test_line_key_ignores_case_spaces_and_edge_punctuation():
    assert line_key("  Oh, Baby!  ") == line_key("oh,   baby") == "oh, baby"


def test_repetition_and_change_indicators():
    original = "[Chorus]\r\nI don’t care\nI don't care!\n\n\nSay it  \nI DON'T CARE"
    v = build_views(original)
    s = stats_for(original, v.structural, v.analysis)
    assert s["changed_any"] and s["had_curly_quotes"] and s["had_special_spaces"]
    assert s["had_crlf"] and s["had_multi_blank_lines"] and s["had_trailing_spaces"]
    assert s["n_lines_nonblank"] == 4 and s["n_unique_lines"] == 2
    assert s["max_line_repeats"] == 3
    assert abs(s["repeated_line_share"] - 0.5) < 1e-9
    assert s["n_words"] == 11 and s["n_types"] == 5


def test_no_changes_on_clean_text():
    original = "plain line\nanother line"
    v = build_views(original)
    s = stats_for(original, v.structural, v.analysis)
    assert not s["changed_any"] and s["repeated_line_share"] == 0.0
