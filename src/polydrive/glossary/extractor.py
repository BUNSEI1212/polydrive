"""Auto-extract candidate terminology from documents."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

_KEYBERT_AVAILABLE: bool | None = None


def _is_available() -> bool:
    global _KEYBERT_AVAILABLE
    if _KEYBERT_AVAILABLE is None:
        try:
            import keybert  # noqa: F401

            _KEYBERT_AVAILABLE = True
        except ImportError:
            _KEYBERT_AVAILABLE = False
    return _KEYBERT_AVAILABLE


@dataclass
class CandidateTerm:
    """A candidate term extracted from text."""

    term: str
    score: float
    frequency: int
    source: str  # "keybert", "noun_chunks", "frequency"


def extract_terms(
    texts: list[str],
    min_frequency: int = 2,
    max_terms: int = 50,
    domain: str = "automotive",
) -> list[CandidateTerm]:
    """Extract candidate terminology from a list of texts.

    Uses KeyBERT for semantic extraction when available, falls back to
    frequency-based noun chunk extraction.
    """
    all_text = "\n".join(texts)
    if not all_text.strip():
        return []

    results: list[CandidateTerm] = []

    if _is_available():
        results = _keybert_extract(all_text, max_terms)
    else:
        results = _frequency_extract(all_text, min_frequency, max_terms)

    # Deduplicate and sort by score
    seen: dict[str, CandidateTerm] = {}
    for ct in results:
        key = ct.term.lower().strip()
        if key not in seen or ct.score > seen[key].score:
            seen[key] = ct

    return sorted(seen.values(), key=lambda x: (-x.score, -x.frequency))[:max_terms]


def _keybert_extract(text: str, max_terms: int) -> list[CandidateTerm]:
    import keybert

    kw_model = keybert.KeyBERT()
    keywords = kw_model.extract_keywords(
        text,
        keyphrase_ngram_range=(1, 3),
        stop_words="english",
        top_n=max_terms,
    )

    # Count frequencies
    freq = Counter()
    for phrase, _ in keywords:
        freq[phrase] = text.lower().count(phrase.lower())

    return [
        CandidateTerm(term=phrase, score=round(score, 4), frequency=freq[phrase], source="keybert")
        for phrase, score in keywords
    ]


def _frequency_extract(text: str, min_frequency: int, max_terms: int) -> list[CandidateTerm]:
    """Rule-based extraction using regex noun phrase patterns."""
    # Extract potential technical terms: 2-4 word phrases with capitalization or technical suffixes
    patterns = [
        r"\b[A-Z][a-z]+(?:\s+[A-Z]?[a-z]+){1,3}\b",  # Capitalized phrases
        r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})*\b",  # Acronyms
    ]

    candidates: Counter[str] = Counter()
    for pat in patterns:
        for match in re.findall(pat, text):
            phrase = match.strip()
            if len(phrase) >= 3 and not phrase.lower().startswith(("the ", "this ", "that ")):
                candidates[phrase] += 1

    # Also extract hyphenated compounds
    for match in re.findall(r"\b[a-z]+(?:-[a-z]+)+\b", text):
        candidates[match] += 1

    results: list[CandidateTerm] = []
    total = sum(candidates.values())
    for phrase, count in candidates.most_common(max_terms):
        if count >= min_frequency:
            score = count / total if total > 0 else 0
            results.append(
                CandidateTerm(term=phrase, score=round(score, 4), frequency=count, source="frequency")
            )

    return results
