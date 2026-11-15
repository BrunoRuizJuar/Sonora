"""Text views on synthetic strings (not real corpus data)."""
from sonora.nlp.language import LanguageRules, LanguageScores, SecondaryScore, decide, needs_secondary
from sonora.preprocessing.lyrics_text import build_views, dedup_key, language_excerpt, section_label


def test_original_untouched_and_structure_preserved():
    original = ("[Verse 1]\r\nI don’t wanna go,  no I won't\r\n\r\n\r\n"
                "[Chorus x2]\nCan’t stop \\'til the end tonight\n  \nNever, never\n")
    copy = str(original)
    views = build_views(original)
    assert original == copy
    # contractions and negations survive, typographic apostrophes become ASCII
    assert "I don't wanna go, no I won't" in views.structural
    assert "Can't stop 'til the end tonight" in views.structural
    # section markers stay in the structural view, not in the analysis view
    assert "[Chorus x2]" in views.structural
    assert "[" not in views.analysis
    assert views.section_labels == ["verse", "chorus"]
    assert views.n_section_markers == 2
    # stanza breaks: runs of blank lines collapse to exactly one; headers start stanzas
    assert "\n\n\n" not in views.structural
    assert views.analysis.split("\n\n") == ["I don't wanna go, no I won't", "Can't stop 'til the end tonight", "Never, never"]
    assert views.n_stanzas == 3
    assert "escaped_quote_fixed" in views.flags


def test_unicode_kept_and_replacement_flagged():
    views = build_views("Café olé � niño\nSecond line")
    assert "Café olé � niño" in views.structural
    assert "replacement_char" in views.flags
    assert views.n_words == 5


def test_html_artifacts_and_inline_annotations():
    views = build_views("Hello &amp; goodbye<br>Next line [?] here\nYou might also like\nEnd 12Embed")
    assert views.structural.split("\n") == ["Hello & goodbye", "Next line [?] here", "End"]
    assert views.analysis.split("\n") == ["Hello & goodbye", "Next line here", "End"]
    assert {"html_entity_unescaped", "html_tag_removed", "widget_line_removed", "embed_suffix_removed"} <= set(views.flags)


def test_dedup_key_only_case_and_whitespace():
    a = build_views("[Intro]\nHello  World\n\nBye").analysis
    b = build_views("hello world\nbye").analysis
    c = build_views("Hello, world\nBye").analysis
    assert dedup_key(a) == dedup_key(b)
    assert dedup_key(a) != dedup_key(c)  # punctuation differences are not merged


def test_section_label():
    assert section_label("Chorus: Drake & Rihanna") == "chorus"
    assert section_label("Pre-Chorus 2") == "pre-chorus"
    assert section_label("Verse 1: X") == "verse"
    assert section_label("?") == "?"


def test_language_excerpt_windows():
    text = "a" * 1000 + "b" * 1000 + "c" * 1000
    ex = language_excerpt(text, 100, 3)
    assert ex.split("\n") == ["a" * 100, "b" * 100, "c" * 100]
    assert language_excerpt("short", 100, 3) == "short"


def test_language_decisions():
    rules = LanguageRules()
    en = SecondaryScore("en", 0.99)
    es = SecondaryScore("es", 0.99)
    assert decide(LanguageScores("en", 0.995, "es", 0.0, 0.995), 100, rules) == ("en", "primary_en_high_conf")
    assert needs_secondary(LanguageScores("en", 0.9, "es", 0.1, 0.9), 100, rules)
    assert decide(LanguageScores("en", 0.6, "tl", 0.1, 0.6), 100, rules, en) == ("en", "both_detectors_en")
    assert decide(LanguageScores("en", 0.6, "es", 0.4, 0.6), 100, rules, es)[0] == "uncertain"
    # lingua confidently wrong on English: disagreement -> review, never an exclusion
    assert decide(LanguageScores("de", 1.0, "en", 0.0, 0.0), 100, rules, en) == ("uncertain", "primary_not_en_secondary_en")
    assert decide(LanguageScores("es", 0.97, "en", 0.03, 0.03), 100, rules, es) == ("non_en", "both_detectors_es")
    assert decide(LanguageScores("es", 0.97, "pt", 0.03, 0.0), 100, rules, SecondaryScore("it", 0.9))[0] == "uncertain"
    # short texts always need the second opinion
    assert needs_secondary(LanguageScores("en", 1.0, "de", 0.0, 1.0), 10, rules)
    assert decide(LanguageScores("en", 1.0, "de", 0.0, 1.0), 10, rules, en)[0] == "en"
    assert decide(LanguageScores("es", 0.99, "en", 0.0, 0.0), 10, rules, es)[0] == "uncertain"
    assert decide(LanguageScores(None, 0, None, 0, 0), 100, rules, en)[0] == "uncertain"


def test_real_detectors_on_tiny_synthetic_texts():
    import pytest

    pytest.importorskip("lingua")
    pytest.importorskip("py3langid")
    from sonora.nlp.language import LangidDetector, LinguaDetector

    texts = [
        "I don't want to lose you, baby, never let me go tonight, hold me close until the morning light",
        "No quiero perderte nunca, mi amor, quédate conmigo esta noche hasta que salga el sol",
    ]
    en, es = LinguaDetector().score_many(texts)
    assert en.top == "en" and es.top == "es" and es.en_conf < 0.2
    secondary = LangidDetector()
    assert secondary.classify(texts[0]).lang == "en"
    assert secondary.classify(texts[1]).lang == "es"
