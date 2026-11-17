"""Language identification for lyrics (DAT-02).

The Genius Parquet files have no language column, so language is detected on an
excerpt of the *analysis* view (section headers such as ``[Chorus]`` are removed
first because they are English words even in non-English lyrics).

Two independent, versioned detectors are used:

* primary: ``lingua-language-detector`` (all languages, high-accuracy mode), run on
  every eligible record;
* secondary: ``py3langid`` (langid.py model, normalized probabilities), run only when
  the primary is not conclusive.

Calibration observed on real Genius rows (2026-11-12, shard 7, 106 000 rows): lingua's
confidence is unreliable on short/repetitive lyrics and it sometimes assigns
confidence 1.0 to a wrong language (``de``/``tl``/``la`` for plain English), so a
non-English decision, or any decision on a short text, requires both detectors to agree.
Disagreements are kept as ``uncertain`` for human review, never silently accepted.
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib.metadata
from typing import Protocol, Sequence

PRIMARY_NAME = "lingua-language-detector"
SECONDARY_NAME = "py3langid"


@dataclass(frozen=True, slots=True)
class LanguageScores:
    top: str | None          # ISO 639-1 code, or None when undetectable
    top_conf: float
    second: str | None
    second_conf: float
    en_conf: float


@dataclass(frozen=True, slots=True)
class SecondaryScore:
    lang: str | None
    conf: float


@dataclass(frozen=True, slots=True)
class LanguageRules:
    primary_accept_en_min_conf: float = 0.99
    short_text_words: int = 20
    secondary_min_conf: float = 0.50


class Detector(Protocol):
    name: str
    version: str

    def score_many(self, texts: Sequence[str]) -> list[LanguageScores]: ...


class SecondaryDetector(Protocol):
    name: str
    version: str

    def classify(self, text: str) -> SecondaryScore: ...


class LinguaDetector:
    name = PRIMARY_NAME

    def __init__(self, low_accuracy: bool = False) -> None:
        from lingua import Language, LanguageDetectorBuilder

        builder = LanguageDetectorBuilder.from_all_languages().with_preloaded_language_models()
        if low_accuracy:
            builder = builder.with_low_accuracy_mode()
        self._detector = builder.build()
        self._english = Language.ENGLISH
        self.version = importlib.metadata.version("lingua-language-detector")
        self.mode = "low_accuracy" if low_accuracy else "high_accuracy"

    def score_many(self, texts: Sequence[str]) -> list[LanguageScores]:
        results = self._detector.compute_language_confidence_values_in_parallel(list(texts))
        out: list[LanguageScores] = []
        for values in results:
            if not values or values[0].value <= 0:
                out.append(LanguageScores(None, 0.0, None, 0.0, 0.0))
                continue
            en = next((v.value for v in values if v.language == self._english), 0.0)
            first = values[0]
            second = values[1] if len(values) > 1 else None
            out.append(LanguageScores(
                top=first.language.iso_code_639_1.name.lower(),
                top_conf=float(first.value),
                second=second.language.iso_code_639_1.name.lower() if second else None,
                second_conf=float(second.value) if second else 0.0,
                en_conf=float(en),
            ))
        return out


class LangidDetector:
    name = SECONDARY_NAME

    def __init__(self) -> None:
        from py3langid.langid import MODEL_FILE, LanguageIdentifier

        self._identifier = LanguageIdentifier.from_model_file(MODEL_FILE, norm_probs=True)
        self.version = importlib.metadata.version("py3langid")

    def classify(self, text: str) -> SecondaryScore:
        if not text.strip():
            return SecondaryScore(None, 0.0)
        lang, prob = self._identifier.classify(text)
        return SecondaryScore(str(lang), float(prob))


def needs_secondary(scores: LanguageScores, n_words: int, rules: LanguageRules) -> bool:
    return not (scores.top == "en" and scores.en_conf >= rules.primary_accept_en_min_conf
                and n_words >= rules.short_text_words)


def decide(scores: LanguageScores, n_words: int, rules: LanguageRules,
           secondary: SecondaryScore | None = None) -> tuple[str, str]:
    """Return ``(language_status, reason)``: ``en`` accepted, ``non_en`` excluded,
    ``uncertain`` kept for review."""
    if not needs_secondary(scores, n_words, rules):
        return "en", "primary_en_high_conf"
    if secondary is None:
        raise ValueError("Se requiere el detector secundario para este registro")
    if scores.top is None:
        return "uncertain", "primary_undetectable"
    sec_ok = secondary.lang is not None and secondary.conf >= rules.secondary_min_conf
    if scores.top == "en":
        if sec_ok and secondary.lang == "en":
            return "en", "both_detectors_en"
        return "uncertain", "primary_en_secondary_not_en"
    # primary says another language
    if sec_ok and secondary.lang == "en":
        return "uncertain", "primary_not_en_secondary_en"
    if sec_ok and secondary.lang == scores.top:
        if n_words < rules.short_text_words:
            return "uncertain", "short_text_both_non_en"
        return "non_en", f"both_detectors_{scores.top}"
    return "uncertain", "detectors_disagree_non_en"
