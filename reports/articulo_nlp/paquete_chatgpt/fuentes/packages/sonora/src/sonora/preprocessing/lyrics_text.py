"""Deterministic text views for Genius lyrics.

Three views (DAT-04):

* ``original``   - the exact string read from the source Parquet. Never modified.
* ``structural`` - verifiable formatting/scraping artifacts removed; keeps section
  markers (``[Chorus]``), line breaks, stanza breaks, punctuation, case, contractions,
  negations and repeated refrains exactly as written.
* ``analysis``   - structural view without editorial bracket annotations
  (section headers, ``[?]``). Header lines become stanza boundaries. Still keeps
  case, punctuation, contractions, negations, line and stanza structure, so it is
  usable for POS/lemma/dependency work. Lower-casing/tokenization happen downstream.

Refrains are NOT expanded or deduplicated (``[Chorus x2]`` is not multiplied out);
repeated lines written out in the source stay repeated in every view.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import html
import re
import unicodedata

TEXT_VIEWS_VERSION = "lyrics-views-v1"

_SPACE_CHARS = dict.fromkeys(
    [0x00A0, 0x1680, *range(0x2000, 0x200B), 0x202F, 0x205F, 0x3000, 0x0009], " "
)
_ZERO_WIDTH = dict.fromkeys([0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD], None)
_QUOTES = {
    0x2019: "'", 0x2018: "'", 0x02BC: "'", 0x2032: "'", 0x201B: "'",
    0x201C: '"', 0x201D: '"', 0x201E: '"', 0x201F: '"', 0x2033: '"',
}
_TRANSLATION = {**_SPACE_CHARS, **_ZERO_WIDTH, **_QUOTES}

_ESCAPED_QUOTE = re.compile(r"\\(['\"])")
_HTML_ENTITY = re.compile(r"&(?:[a-zA-Z]{2,8}|#\d{1,6}|#x[0-9a-fA-F]{1,6});")
_HTML_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
_HTML_TAG = re.compile(r"</?(?:p|i|b|em|strong|span|div|a|u)\b[^>\n]{0,200}>", re.IGNORECASE)
_EMBED_TAIL = re.compile(r"\d*Embed\s*$")
_YOU_MIGHT = re.compile(r"^[ \t]*You might also like[ \t]*(?:\n|$)", re.MULTILINE)
_URL = re.compile(r"https?://", re.IGNORECASE)
_HEADER_LINE = re.compile(r"^\s*\[([^\]\n]{0,120})\]\s*$")
_INLINE_BRACKET = re.compile(r"\[[^\]\n]{0,120}\]")
_MULTI_SPACE = re.compile(r" {2,}")
_WORD = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)*", re.UNICODE)
_WS = re.compile(r"\s+")


@dataclass(slots=True)
class LyricsViews:
    structural: str
    analysis: str
    n_chars_original: int
    n_chars_structural: int
    n_chars_analysis: int
    n_lines: int
    n_stanzas: int
    n_section_markers: int
    n_words: int
    section_labels: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


def _collapse_lines(lines: list[str]) -> str:
    """Strip line ends, collapse runs of blank lines into one stanza break."""
    out: list[str] = []
    blank = False
    for line in lines:
        line = _MULTI_SPACE.sub(" ", line).strip()
        if not line:
            blank = bool(out)
            continue
        if blank:
            out.append("")
            blank = False
        out.append(line)
    return "\n".join(out)


def section_label(header: str) -> str:
    """``Chorus: Artist x2`` -> ``chorus``; ``Pre-Chorus 2`` -> ``pre-chorus``; ``?`` -> ``?``."""
    head = header.strip().casefold()
    head = re.split(r"[:(\d]|\bx\d", head, maxsplit=1)[0].strip()
    return head.split(" ")[0] if head else ""


def structural_view(original: str) -> tuple[str, list[str]]:
    flags: list[str] = []
    text = unicodedata.normalize("NFC", original)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if _HTML_ENTITY.search(text):
        text = html.unescape(text)
        flags.append("html_entity_unescaped")
    if _HTML_BR.search(text) or _HTML_TAG.search(text):
        text = _HTML_TAG.sub("", _HTML_BR.sub("\n", text))
        flags.append("html_tag_removed")
    if _ESCAPED_QUOTE.search(text):
        text = _ESCAPED_QUOTE.sub(r"\1", text)
        flags.append("escaped_quote_fixed")
    if _EMBED_TAIL.search(text):
        text = _EMBED_TAIL.sub("", text)
        flags.append("embed_suffix_removed")
    if _YOU_MIGHT.search(text):
        text = _YOU_MIGHT.sub("", text)
        flags.append("widget_line_removed")
    text = text.translate(_TRANSLATION)
    if "\ufffd" in text:
        flags.append("replacement_char")
    if _URL.search(text):
        flags.append("contains_url")
    return _collapse_lines(text.split("\n")), flags


def build_views(original: str) -> LyricsViews:
    structural, flags = structural_view(original)
    labels: list[str] = []
    analysis_lines: list[str] = []
    for line in structural.split("\n"):
        match = _HEADER_LINE.match(line)
        if match:
            labels.append(section_label(match.group(1)))
            analysis_lines.append("")  # a section header always starts a new stanza
            continue
        analysis_lines.append(_INLINE_BRACKET.sub(" ", line))
    analysis = _collapse_lines(analysis_lines)
    non_blank = [line for line in analysis.split("\n") if line]
    n_stanzas = (analysis.count("\n\n") + 1) if non_blank else 0
    return LyricsViews(
        structural=structural,
        analysis=analysis,
        n_chars_original=len(original),
        n_chars_structural=len(structural),
        n_chars_analysis=len(analysis),
        n_lines=len(non_blank),
        n_stanzas=n_stanzas,
        n_section_markers=len(labels),
        n_words=len(_WORD.findall(analysis)),
        section_labels=labels,
        flags=flags,
    )


def dedup_key(analysis: str) -> str:
    """Normalization used ONLY for exact-duplicate detection: casefold + whitespace.

    Punctuation, word order and wording differences are kept, so distinct versions
    are not merged without evidence.
    """
    return _WS.sub(" ", analysis.casefold()).strip()


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def language_excerpt(analysis: str, window: int, windows: int) -> str:
    """Start/middle/end windows of the analysis view, so long mixed-language lyrics are
    not judged only by their intro. Returns the whole text when it is short enough."""
    if windows <= 1 or len(analysis) <= window * windows:
        return analysis[: window * max(windows, 1)]
    step = (len(analysis) - window) / (windows - 1)
    parts = [analysis[int(i * step): int(i * step) + window] for i in range(windows)]
    return "\n".join(parts)
