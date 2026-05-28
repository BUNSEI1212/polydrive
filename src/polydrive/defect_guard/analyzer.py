"""Defect report quality analyzer."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

from langdetect import detect as detect_language

from polydrive.core.models import DefectQualityResult
from polydrive.core.models import DefectReport
from polydrive.core.models import Glossary

_VALID_SEVERITIES = {
    "blocker",
    "critical",
    "high",
    "major",
    "medium",
    "minor",
    "low",
    "trivial",
}

_ACTION_VERBS = {
    "fix",
    "add",
    "remove",
    "update",
    "change",
    "create",
    "delete",
    "rename",
    "move",
    "refactor",
    "replace",
    "correct",
    "adjust",
    "enable",
    "disable",
    "implement",
    "resolve",
    "prevent",
    "handle",
    "support",
    "improve",
    "migrate",
    "upgrade",
    "downgrade",
    "restore",
    "crash",
    "fail",
    "break",
    "hang",
    "freeze",
    "leak",
    "block",
    "overflow",
    "underflow",
    "regress",
    "skip",
    "ignore",
    "missing",
    "wrong",
    "incorrect",
    "unexpected",
    "invalid",
    "corrupt",
}

_VAGUE_PHRASES = {
    "doesn't work",
    "does not work",
    "not working",
    "broken",
    "it fails",
    "it crashes",
    "something wrong",
    "doesn't work properly",
}

_SPECIFIC_PATTERN = re.compile(
    r"\b(v?\d+\.\d+[\w.\-]*|0x[0-9a-fA-F]+|ERR_\w+|E\d{3,}|BSOD|segfault|SIG\w+|NaN|null|undefined)\b"
)

_NUMBERED_STEP = re.compile(r"^\s*(\d+[\.\):]|\[[\d]+\]|step\s*\d+)", re.IGNORECASE)


class DefectAnalyzer:
    """Analyzes defect/bug report quality across multiple dimensions."""

    def analyze(
        self, report: DefectReport, glossary: Glossary | None = None
    ) -> DefectQualityResult:
        field_score, missing = self._field_completeness(report)
        text_score = self._text_quality(report)
        repro_score = self._reproducibility(report)
        term_score = self._terminology_compliance(report, glossary)

        composite = (
            field_score * 0.40
            + text_score * 0.25
            + repro_score * 0.25
            + term_score * 0.10
        )

        detected_lang = self._detect_language(report)
        lang_warning = self._check_language_mix(report, detected_lang)

        suggestions = self._suggestions(report, missing)

        # Add NLP-based suggestions
        from polydrive.defect_guard.nlp_quality import analyze_text_quality

        nlp_result = analyze_text_quality(report.title, report.description)
        for nlp_issue in nlp_result.issues:
            if nlp_issue not in suggestions:
                suggestions.append(nlp_issue)

        if composite < 40:
            sev = "error"
        elif composite < 70:
            sev = "warning"
        else:
            sev = "info"

        return DefectQualityResult(
            report_id=report.id,
            composite_score=round(composite, 1),
            field_completeness=round(field_score, 1),
            text_quality=round(text_score, 1),
            reproducibility=round(repro_score, 1),
            terminology_compliance=round(term_score, 1),
            missing_fields=missing,
            improvement_suggestions=suggestions,
            detected_language=detected_lang,
            language_mix_warning=lang_warning,
            severity=sev,
        )

    def _field_completeness(self, report: DefectReport) -> tuple[float, list[str]]:
        checks: list[tuple[str, bool]] = [
            ("title", len(report.title.strip()) > 10),
            ("description", len(report.description.strip()) > 20),
            ("steps_to_reproduce", len(report.steps_to_reproduce) >= 1),
            (
                "expected_behavior",
                report.expected_behavior is not None
                and len(report.expected_behavior.strip()) > 0,
            ),
            (
                "actual_behavior",
                report.actual_behavior is not None
                and len(report.actual_behavior.strip()) > 0,
            ),
            ("environment", len(report.environment) >= 1),
            (
                "severity",
                report.severity is not None
                and report.severity.lower() in _VALID_SEVERITIES,
            ),
            (
                "component",
                report.component is not None and len(report.component.strip()) > 0,
            ),
        ]
        passed = sum(1 for _, ok in checks if ok)
        missing = [name for name, ok in checks if not ok]
        score = (passed / len(checks)) * 100.0
        return score, missing

    def _text_quality(self, report: DefectReport) -> float:
        from polydrive.defect_guard.nlp_quality import analyze_text_quality

        nlp_result = analyze_text_quality(report.title, report.description)

        # Blend rule-based scoring with NLP scoring
        points = 0.0
        max_points = 4.0

        first_word = (
            report.title.strip().split()[0].lower().rstrip(":")
            if report.title.strip()
            else ""
        )
        if first_word in _ACTION_VERBS or len(report.title.strip()) > 20:
            points += 1.0

        if report.steps_to_reproduce:
            numbered = sum(
                1 for s in report.steps_to_reproduce if _NUMBERED_STEP.match(s)
            )
            if numbered >= len(report.steps_to_reproduce) * 0.5:
                points += 1.0

        all_text = (
            f"{report.title} {report.description} {' '.join(report.steps_to_reproduce)}"
        )
        if _SPECIFIC_PATTERN.search(all_text):
            points += 1.0

        if len(report.description.strip()) > 50:
            points += 1.0

        rule_score = (points / max_points) * 100.0

        # Weighted blend: 60% rules + 40% NLP
        blended = rule_score * 0.6 + nlp_result.score * 0.4
        return blended

    def _reproducibility(self, report: DefectReport) -> float:
        points = 0.0
        max_points = 4.0

        # Has steps_to_reproduce
        if report.steps_to_reproduce:
            points += 1.0

            # Steps are specific (not vague)
            vague_count = 0
            for step in report.steps_to_reproduce:
                step_lower = step.lower()
                if any(vp in step_lower for vp in _VAGUE_PHRASES):
                    vague_count += 1
            if vague_count == 0 and len(report.steps_to_reproduce) >= 2:
                points += 1.0

        # Has expected vs actual behavior
        if report.expected_behavior and report.actual_behavior:
            points += 1.0

        # Has environment details
        if report.environment:
            points += 1.0

        return (points / max_points) * 100.0

    def _terminology_compliance(
        self, report: DefectReport, glossary: Glossary | None
    ) -> float:
        if glossary is None:
            return 100.0

        # Extract all glossary terms
        all_terms: set[str] = set()
        for entry in glossary.entries:
            for lt in entry.translations:
                all_terms.add(lt.term.lower())

        if not all_terms:
            return 100.0

        # Find words in description that look like domain terms
        desc_words = set(re.findall(r"[a-zA-Z]{3,}", report.description.lower()))
        # Also check title and steps
        desc_words.update(re.findall(r"[a-zA-Z]{3,}", report.title.lower()))
        for step in report.steps_to_reproduce:
            desc_words.update(re.findall(r"[a-zA-Z]{3,}", step.lower()))

        # Count how many glossary terms appear
        matched = sum(1 for t in all_terms if t in desc_words)

        # Fraction of glossary terms present
        if not desc_words:
            return 50.0

        compliance = (matched / len(all_terms)) * 100.0
        # If some terms match, give at least partial credit
        return min(compliance, 100.0)

    def _detect_language(self, report: DefectReport) -> str | None:
        text = report.description.strip()
        if not text or len(text) < 10:
            return None
        try:
            return detect_language(text)
        except Exception:
            return None

    def _check_language_mix(
        self, report: DefectReport, dominant_lang: str | None
    ) -> str | None:
        text = f"{report.title} {report.description}"
        if not text.strip():
            return None

        # Count character scripts
        script_counts: Counter[str] = Counter()
        for ch in text:
            if ch.isspace() or unicodedata.category(ch).startswith("P"):
                continue
            name = unicodedata.name(ch, "")
            if "CJK" in name or "HIRAGANA" in name or "KATAKANA" in name:
                script_counts["cjk"] += 1
            elif "CYRILLIC" in name:
                script_counts["cyrillic"] += 1
            elif "ARABIC" in name:
                script_counts["arabic"] += 1
            elif "LATIN" in name or ch.isascii():
                script_counts["latin"] += 1
            else:
                script_counts["other"] += 1

        total = sum(script_counts.values())
        if total == 0:
            return None

        dominant_script = script_counts.most_common(1)[0][0]
        non_dominant = total - script_counts[dominant_script]
        ratio = non_dominant / total

        if ratio > 0.05:
            return (
                f"Language mixing detected: {ratio:.0%} non-dominant script "
                f"(dominant: {dominant_script})"
            )
        return None

    def _suggestions(self, report: DefectReport, missing: list[str]) -> list[str]:
        suggestions: list[str] = []
        if "title" in missing:
            suggestions.append(
                "Title should be more descriptive (at least 10 characters)"
            )
        if "description" in missing:
            suggestions.append("Description needs more detail (at least 20 characters)")
        if "steps_to_reproduce" in missing:
            suggestions.append("Add steps to reproduce the defect")
        if "expected_behavior" in missing:
            suggestions.append("Specify the expected behavior")
        if "actual_behavior" in missing:
            suggestions.append("Specify the actual behavior observed")
        if "environment" in missing:
            suggestions.append("Add environment details (OS, version, platform, etc.)")
        if "severity" in missing:
            suggestions.append(
                "Set severity to one of: critical, major, minor, trivial"
            )
        if "component" in missing:
            suggestions.append("Specify the affected component")

        if len(report.description.strip()) <= 50 and "description" not in missing:
            suggestions.append(
                "Description could be more detailed (>50 characters recommended)"
            )

        if report.steps_to_reproduce:
            vague = [
                s
                for s in report.steps_to_reproduce
                if any(vp in s.lower() for vp in _VAGUE_PHRASES)
            ]
            if vague:
                suggestions.append(
                    "Some reproduction steps are too vague — add specific actions"
                )

        return suggestions
