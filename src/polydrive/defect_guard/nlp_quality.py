"""NLP-enhanced text quality analysis for defect reports."""

from __future__ import annotations

import re
from dataclasses import dataclass

_SPACY_AVAILABLE: bool | None = None
_nlp = None


def _is_available() -> bool:
    global _SPACY_AVAILABLE
    if _SPACY_AVAILABLE is None:
        try:
            import spacy  # noqa: F401

            _SPACY_AVAILABLE = True
        except ImportError:
            _SPACY_AVAILABLE = False
    return _SPACY_AVAILABLE


def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy

        _nlp = spacy.load("en_core_web_sm")
    return _nlp


@dataclass
class TextQualityResult:
    """NLP-based text quality assessment."""

    score: float  # 0-100
    issues: list[str]
    vagueness_score: float  # 0-1 (higher = more vague)
    completeness_score: float  # 0-1 (higher = more complete)
    has_placeholder_text: bool
    sentence_count: int


# Vague phrases that indicate incomplete descriptions
_VAGUE_PHRASES = [
    r"\bsee attachment\b",
    r"\bsee attached\b",
    r"\bsee below\b",
    r"\bTBD\b",
    r"\bTODO\b",
    r"\bFIXME\b",
    r"\bN/?A\b",
    r"\bnot sure\b",
    r"\bsomething wrong\b",
    r"\bdoesn'?t work\b",
    r"\bnot working\b",
    r"\bbroken\b",
    r"\bjust\b.{0,20}broken",
    r"\bno idea\b",
    r"\bfigure it out\b",
]

# Placeholder patterns that indicate missing information
_PLACEHOLDER_PATTERNS = [
    r"\[.*?\]",  # [placeholder]
    r"<.*?>",  # <placeholder>
    r"\.{3,}",  # ...
    r"etc\.\s*$",  # ending with etc.
]


def analyze_text_quality(title: str, description: str) -> TextQualityResult:
    """Analyze text quality of a defect report using NLP.

    When spaCy is not available, falls back to rule-based analysis.
    """
    text = f"{title} {description}".strip()
    if not text:
        return TextQualityResult(
            score=0.0,
            issues=["Empty text"],
            vagueness_score=1.0,
            completeness_score=0.0,
            has_placeholder_text=True,
            sentence_count=0,
        )

    issues: list[str] = []
    vagueness_score = 0.0
    completeness_score = 1.0

    # Check for placeholder text
    has_placeholder = False
    for pat in _PLACEHOLDER_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            has_placeholder = True
            issues.append("Contains placeholder text")
            completeness_score -= 0.2
            break

    # Check for vague phrases
    vague_count = 0
    for pat in _VAGUE_PHRASES:
        matches = re.findall(pat, text, re.IGNORECASE)
        vague_count += len(matches)
    if vague_count > 0:
        vagueness_score = min(1.0, vague_count * 0.3)
        issues.append(f"Contains {vague_count} vague phrase(s)")
        completeness_score -= 0.15 * vague_count

    if _is_available():
        nlp = _get_nlp()
        doc = nlp(text)
        sentences = list(doc.sents)
        sentence_count = len(sentences)
    else:
        sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
        sentence_count = len(sentences)

    # Sentence-level checks
    if sentence_count == 0:
        issues.append("No complete sentences found")
        completeness_score -= 0.3
    elif sentence_count == 1 and len(description) > 20:
        issues.append("Description is a single sentence — add more detail")

    # Check for technical specificity
    has_technical_terms = bool(re.search(r"\b[A-Z]{2,}\b", text))  # acronyms
    has_version_info = bool(re.search(r"\bv?\d+\.\d+", text))  # version numbers
    has_steps = bool(
        re.search(r"\b(step|first|then|next|after)\b", text, re.IGNORECASE)
    )

    if not has_technical_terms and len(text) > 50:
        issues.append("No technical terms or acronyms detected")
        completeness_score -= 0.1

    if not has_version_info and len(text) > 100:
        issues.append("No version numbers mentioned")

    if not has_steps:
        completeness_score -= 0.05

    # Clamp scores
    completeness_score = max(0.0, min(1.0, completeness_score))
    vagueness_score = max(0.0, min(1.0, vagueness_score))

    # Compute final score
    score = (completeness_score * 60) + ((1 - vagueness_score) * 40)

    return TextQualityResult(
        score=round(score, 1),
        issues=issues,
        vagueness_score=round(vagueness_score, 2),
        completeness_score=round(completeness_score, 2),
        has_placeholder_text=has_placeholder,
        sentence_count=sentence_count,
    )
