"""Auto-extract candidate terminology from documents."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

# Stopwords to filter from extracted terms — these are not valid term components.
_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "has",
        "have",
        "had",
        "does",
        "do",
        "can",
        "will",
        "shall",
        "should",
        "would",
        "could",
        "may",
        "might",
        "must",
        "and",
        "or",
        "but",
        "not",
        "no",
        "of",
        "in",
        "on",
        "at",
        "to",
        "for",
        "with",
        "from",
        "by",
        "as",
        "into",
        "through",
        "after",
        "before",
        "above",
        "below",
        "between",
        "out",
        "off",
        "over",
        "under",
        "again",
        "then",
        "once",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "all",
        "each",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "than",
        "too",
        "very",
    }
)

# Function-word fragments that indicate KeyBERT artifacts rather than real terms.
_FRAGMENT_PREFIXES = frozenset(
    {
        "uses",
        "detects",
        "prevents",
        "builds",
        "based",
        "upon",
    }
)
_FRAGMENT_SUFFIXES = frozenset(
    {
        "uses",
        "detects",
        "prevents",
        "builds",
        "based",
        "upon",
    }
)

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
    frequency-based noun chunk extraction.  Results are post-processed to
    remove stopword noise, fragments, and redundant sub-terms.
    """
    all_text = "\n".join(texts)
    if not all_text.strip():
        return []

    results: list[CandidateTerm] = []

    if _is_available():
        results = _keybert_extract(all_text, max_terms)
    else:
        results = _frequency_extract(all_text, min_frequency, max_terms)

    results = _postprocess(results, all_text)

    # Deduplicate and sort by score
    seen: dict[str, CandidateTerm] = {}
    for ct in results:
        key = ct.term.lower().strip()
        if key not in seen or ct.score > seen[key].score:
            seen[key] = ct

    return sorted(seen.values(), key=lambda x: (-x.score, -x.frequency))[:max_terms]


def _postprocess(
    candidates: list[CandidateTerm],
    source_text: str,
) -> list[CandidateTerm]:
    """Apply noise-reduction filters to raw extracted terms.

    Filters applied in order:
    1. Stopword filtering — drop terms containing stopwords in any word position.
    2. Length filter — drop terms shorter than 3 or longer than 50 characters.
    3. Fragment detection — drop terms starting/ending with function-word verbs.
    4. Duplicate containment — if a shorter term is a substring of a longer
       term with a higher score, remove the shorter one.
    5. Frequency bonus — boost scores for terms that appear more often.
    """
    # --- 1. Stopword filter ---
    filtered: list[CandidateTerm] = []
    for ct in candidates:
        words = ct.term.lower().split()
        if any(w in _STOPWORDS for w in words):
            continue
        filtered.append(ct)
    candidates = filtered

    # --- 2. Length filter ---
    candidates = [ct for ct in candidates if 3 <= len(ct.term) <= 50]

    # --- 3. Fragment detection ---
    cleaned: list[CandidateTerm] = []
    for ct in candidates:
        words = ct.term.lower().split()
        if any(w in _FRAGMENT_PREFIXES for w in words):
            continue
        cleaned.append(ct)
    candidates = cleaned

    # --- 4. Duplicate containment ---
    # Sort by score descending so higher-scored terms are kept.
    candidates_sorted = sorted(candidates, key=lambda c: -c.score)
    kept: list[CandidateTerm] = []
    for ct in candidates_sorted:
        term_lower = ct.term.lower()
        dominated = False
        for better in kept:
            better_lower = better.term.lower()
            if term_lower in better_lower and term_lower != better_lower:
                dominated = True
                break
        if not dominated:
            kept.append(ct)
    candidates = kept

    # --- 5. Frequency bonus ---
    text_lower = source_text.lower()
    freqs: dict[str, int] = {}
    for ct in candidates:
        freqs[ct.term.lower()] = text_lower.count(ct.term.lower())
    max_freq = max(freqs.values()) if freqs else 1

    adjusted: list[CandidateTerm] = []
    for ct in candidates:
        freq = freqs[ct.term.lower()]
        new_score = ct.score * 0.7 + (freq / max_freq) * 0.3
        adjusted.append(
            CandidateTerm(
                term=ct.term,
                score=round(new_score, 4),
                frequency=freq,
                source=ct.source,
            )
        )
    return adjusted


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
        CandidateTerm(
            term=phrase, score=round(score, 4), frequency=freq[phrase], source="keybert"
        )
        for phrase, score in keywords
    ]


def _frequency_extract(
    text: str, min_frequency: int, max_terms: int
) -> list[CandidateTerm]:
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
            if len(phrase) >= 3 and not phrase.lower().startswith(
                ("the ", "this ", "that ")
            ):
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
                CandidateTerm(
                    term=phrase,
                    score=round(score, 4),
                    frequency=count,
                    source="frequency",
                )
            )

    return results
