"""Title/artist normalization shared with the original FMA -> Genius matching run.

Must stay byte-for-byte equivalent to ``normalize`` in ``scripts/check_fma_genius.py``
(``nfkc-casefold-punctuation-spaces-v1``); ``tests/unit/test_normalize.py`` checks it.
"""
from __future__ import annotations

import html
import re
import unicodedata

NORMALIZATION_VERSION = "nfkc-casefold-punctuation-spaces-v1"

# Words that may distinguish a different recording/version of the same work.
VERSION_WORDS = (
    "live", "remix", "instrumental", "karaoke", "acoustic", "demo", "remaster",
    "remastered", "version", "edit", "mix", "radio", "extended", "original",
    "unplugged", "mono", "stereo", "explicit", "clean", "reprise", "cover",
)

_PUNCT = re.compile(r"[^\w\s]", flags=re.UNICODE)
_BRACKETED = re.compile(r"[\(\[\{][^\)\]\}]*[\)\]\}]")
_DASH_SUFFIX = re.compile(r"\s+[-–—]\s+.*$")
_VERSION_RE = re.compile(r"\b(" + "|".join(VERSION_WORDS) + r")\b")


def normalize(value: str | None) -> str:
    """Preserve accents and version WORDS; normalize only formatting variants."""
    if not value:
        return ""
    value = unicodedata.normalize("NFKC", html.unescape(str(value))).casefold()
    value = value.replace("&", " and ")
    value = _PUNCT.sub(" ", value)
    return " ".join(value.split())


def base_title(title: str | None) -> str:
    """Title of the underlying work, used ONLY to group related versions for splits.

    Removes a bracketed or dash suffix when it contains a version word
    (``Song (Live)``, ``Song - 2011 Remaster``). Never used to accept a match.
    """
    if not title:
        return ""
    raw = unicodedata.normalize("NFKC", html.unescape(str(title)))
    pieces = [m.group(0) for m in _BRACKETED.finditer(raw)]
    for piece in pieces:
        if _VERSION_RE.search(piece.casefold()):
            raw = raw.replace(piece, " ")
    dash = _DASH_SUFFIX.search(raw)
    if dash and _VERSION_RE.search(dash.group(0).casefold()):
        raw = raw[: dash.start()]
    result = normalize(raw)
    return result or normalize(title)
