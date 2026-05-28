"""Core data models for PolyDrive."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel
from pydantic import Field


class TermCategory(str, Enum):
    """Classification of terminology entries."""

    BRAND = "brand"
    REGULATORY = "regulatory"
    TECHNICAL = "technical"
    DO_NOT_TRANSLATE = "do_not_translate"
    GENERAL = "general"


class TermStatus(str, Enum):
    """Status of a terminology entry."""

    DRAFT = "draft"
    APPROVED = "approved"
    DEPRECATED = "deprecated"
    FORBIDDEN = "forbidden"


class LangPair(BaseModel):
    """A source-target language pair using BCP 47 tags."""

    source: str = Field(..., description="Source language tag (BCP 47, e.g. 'en')")
    target: str = Field(..., description="Target language tag (BCP 47, e.g. 'zh-Hans')")

    def __str__(self) -> str:
        return f"{self.source}:{self.target}"


class LocalizedTerm(BaseModel):
    """A term in a specific language."""

    lang: str = Field(..., description="BCP 47 language tag")
    term: str = Field(..., description="The term text")
    definition: str | None = Field(None, description="Definition in this language")
    usage_example: str | None = Field(None, description="Usage example")
    part_of_speech: str | None = Field(
        None, description="Part of speech (noun, verb, etc.)"
    )
    forbidden: bool = Field(False, description="This form is forbidden/deprecated")

    def __hash__(self) -> int:
        return hash((self.lang, self.term))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LocalizedTerm):
            return NotImplemented
        return self.lang == other.lang and self.term == other.term


class TermEntry(BaseModel):
    """A single terminology entry with translations across languages."""

    id: str = Field(..., description="Unique identifier")
    subject: str = Field("", description="Subject field / domain")
    category: TermCategory = Field(TermCategory.GENERAL, description="Term category")
    status: TermStatus = Field(TermStatus.APPROVED, description="Term status")
    note: str | None = Field(None, description="Administrative note")
    translations: list[LocalizedTerm] = Field(
        default_factory=list, description="Localized term variants"
    )

    def get_term(self, lang: str) -> LocalizedTerm | None:
        """Get the localized term for a specific language."""
        for t in self.translations:
            if t.lang == lang and not t.forbidden:
                return t
        return None

    def get_all_terms(self, lang: str) -> list[LocalizedTerm]:
        """Get all localized terms for a language (including forbidden)."""
        return [t for t in self.translations if t.lang == lang]


class Glossary(BaseModel):
    """A collection of terminology entries."""

    id: str = Field(..., description="Glossary identifier")
    title: str = Field("", description="Human-readable title")
    source_lang: str = Field("en", description="Default source language")
    domain: str = Field("automotive", description="Subject domain")
    entries: list[TermEntry] = Field(default_factory=list, description="Term entries")

    def find_by_term(self, term_text: str, lang: str) -> list[TermEntry]:
        """Find all entries containing a specific term in a given language."""
        results = []
        for entry in self.entries:
            for lt in entry.translations:
                if lt.lang == lang and lt.term.lower() == term_text.lower():
                    results.append(entry)
                    break
        return results

    def check_consistency(self, lang_pair: LangPair) -> list[ConsistencyIssue]:
        """Check for terminology consistency issues between two languages."""
        issues: list[ConsistencyIssue] = []

        # Group entries by source term
        source_terms: dict[str, list[TermEntry]] = {}
        for entry in self.entries:
            st = entry.get_term(lang_pair.source)
            if st:
                key = st.term.lower()
                source_terms.setdefault(key, []).append(entry)

        # Check: same source term maps to different target terms
        for src_term, entries in source_terms.items():
            if len(entries) <= 1:
                continue
            target_terms = set()
            for entry in entries:
                tt = entry.get_term(lang_pair.target)
                if tt:
                    target_terms.add(tt.term)
            if len(target_terms) > 1:
                issues.append(
                    ConsistencyIssue(
                        severity="warning",
                        issue_type="inconsistent_translation",
                        source_lang=lang_pair.source,
                        target_lang=lang_pair.target,
                        source_term=src_term,
                        details=f"Same source term translated differently: {target_terms}",
                        entry_ids=[e.id for e in entries],
                    )
                )

        # Check: missing translations
        for entry in self.entries:
            src = entry.get_term(lang_pair.source)
            tgt = entry.get_term(lang_pair.target)
            if src and not tgt:
                issues.append(
                    ConsistencyIssue(
                        severity="info",
                        issue_type="missing_translation",
                        source_lang=lang_pair.source,
                        target_lang=lang_pair.target,
                        source_term=src.term,
                        details=f"Missing {lang_pair.target} translation for entry {entry.id}",
                        entry_ids=[entry.id],
                    )
                )

        return issues


class ConsistencyIssue(BaseModel):
    """A terminology consistency issue found during checking."""

    severity: str = Field(..., description="Issue severity: error, warning, info")
    issue_type: str = Field(
        ...,
        description="Type of issue: inconsistent_translation, missing_translation, etc.",
    )
    source_lang: str = Field(..., description="Source language")
    target_lang: str = Field(..., description="Target language")
    source_term: str = Field(..., description="The source term that has the issue")
    details: str = Field(..., description="Human-readable description")
    entry_ids: list[str] = Field(default_factory=list, description="Affected entry IDs")


class EncodingIssue(BaseModel):
    """An encoding issue found in a file."""

    file_path: Path = Field(..., description="Path to the file with the issue")
    line: int | None = Field(None, description="Line number (1-based), if applicable")
    issue_type: str = Field(
        ..., description="Type: non_utf8, has_bom, invalid_chars, mixed_encoding"
    )
    detected_encoding: str | None = Field(None, description="Detected encoding")
    expected_encoding: str = Field("utf-8", description="Expected encoding")
    details: str = Field(..., description="Human-readable description")


class HardcodedStringIssue(BaseModel):
    """A hardcoded non-ASCII string found in source code."""

    file_path: Path = Field(..., description="Path to the source file")
    line: int = Field(..., description="Line number (1-based)")
    column: int = Field(..., description="Column number (1-based)")
    text: str = Field(..., description="The detected hardcoded string")
    language: str = Field(..., description="Source file language (cpp, c, etc.)")


class MTResult(BaseModel):
    """Result from a machine translation."""

    translated_text: str
    detected_source_lang: str | None = None
    engine: str
    glossary_applied: bool = False
    applied_terms: list[tuple[str, str]] = Field(default_factory=list)
    character_count: int = 0
    latency_ms: float = 0.0
    metadata: dict[str, str] = Field(default_factory=dict)


class MTUsageStats(BaseModel):
    """Translation usage statistics."""

    total_requests: int = 0
    total_characters: int = 0
    by_engine: dict[str, int] = Field(default_factory=dict)
    by_language_pair: dict[str, int] = Field(default_factory=dict)


class DefectReport(BaseModel):
    """A structured defect/bug report."""

    id: str
    title: str
    description: str
    steps_to_reproduce: list[str] = Field(default_factory=list)
    expected_behavior: str | None = None
    actual_behavior: str | None = None
    environment: dict[str, str] = Field(default_factory=dict)
    severity: str | None = None
    priority: str | None = None
    component: str | None = None
    attachments: list[str] = Field(default_factory=list)
    language: str | None = Field(None, description="Auto-detected language (BCP 47)")
    source_system: str = "jira"
    metadata: dict[str, str] = Field(default_factory=dict)


class DefectQualityResult(BaseModel):
    """Quality analysis result for a defect report."""

    report_id: str
    composite_score: float = Field(..., description="Overall quality score 0-100")
    field_completeness: float = Field(
        ..., description="Required fields completeness 0-100"
    )
    text_quality: float = Field(..., description="Text clarity score 0-100")
    reproducibility: float = Field(..., description="Reproducibility score 0-100")
    terminology_compliance: float = Field(
        default=100.0, description="Terminology compliance 0-100"
    )
    missing_fields: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)
    detected_language: str | None = None
    language_mix_warning: str | None = None
    severity: str = "info"
