"""Core data models — re-exported from models.py module."""

from __future__ import annotations

import polydrive.core._models as _m  # noqa: F401

# Re-export all public names
ConsistencyIssue = _m.ConsistencyIssue
DefectQualityResult = _m.DefectQualityResult
DefectReport = _m.DefectReport
EncodingIssue = _m.EncodingIssue
Glossary = _m.Glossary
HardcodedStringIssue = _m.HardcodedStringIssue
LangPair = _m.LangPair
LocalizedTerm = _m.LocalizedTerm
MTResult = _m.MTResult
MTUsageStats = _m.MTUsageStats
TermCategory = _m.TermCategory
TermEntry = _m.TermEntry
TermStatus = _m.TermStatus

__all__ = [
    "ConsistencyIssue",
    "DefectQualityResult",
    "DefectReport",
    "EncodingIssue",
    "Glossary",
    "HardcodedStringIssue",
    "LangPair",
    "LocalizedTerm",
    "MTResult",
    "MTUsageStats",
    "TermCategory",
    "TermEntry",
    "TermStatus",
]
