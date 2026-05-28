"""Tests for the defect_guard analyzer."""

from __future__ import annotations

import pytest

from polydrive.core.models import DefectReport
from polydrive.core.models import Glossary
from polydrive.core.models import LocalizedTerm
from polydrive.core.models import TermEntry
from polydrive.defect_guard import DefectAnalyzer


@pytest.fixture
def analyzer() -> DefectAnalyzer:
    return DefectAnalyzer()


def _perfect_report() -> DefectReport:
    return DefectReport(
        id="BUG-001",
        title="Crash when submitting invalid CAN signal ID 0x1FFF in diagnostic tool v2.3.1",
        description=(
            "The diagnostic tool crashes with a segfault when a user submits "
            "an invalid CAN signal identifier 0x1FFF. This occurs consistently "
            "on the HIL test bench when running automated test suite. "
            "The error log shows SIGSEGV at address 0x00007ffa12345678."
        ),
        steps_to_reproduce=[
            "1. Launch diagnostic tool v2.3.1 on HIL bench",
            "2. Connect to ECU via CAN bus at 500kbps",
            "3. Enter signal ID 0x1FFF in the signal monitor",
            "4. Click 'Submit' button",
        ],
        expected_behavior="Tool should display an error message: 'Invalid signal ID'",
        actual_behavior="Application crashes with segmentation fault (SIGSEGV)",
        environment={"os": "Ubuntu 22.04", "version": "2.3.1", "platform": "HIL"},
        severity="critical",
        priority="high",
        component="diagnostic-tool",
    )


def _minimal_report() -> DefectReport:
    return DefectReport(
        id="BUG-002",
        title="bug",
        description="short",
    )


def _mixed_language_report() -> DefectReport:
    return DefectReport(
        id="BUG-003",
        title="CAN总线信号丢失导致系统崩溃",
        description=(
            "在测试过程中发现CAN总线信号丢失，导致adas系统无法正常工作。"
            "This affects the ADAS module in version 3.2.1"
        ),
        steps_to_reproduce=["1. 启动系统", "2. 发送CAN信号"],
        expected_behavior="系统应正常处理CAN信号",
        actual_behavior="系统崩溃并显示错误",
        environment={"platform": "HIL"},
        severity="major",
        component="adas",
    )


def _make_glossary() -> Glossary:
    return Glossary(
        id="auto-terms",
        title="Automotive Terms",
        entries=[
            TermEntry(
                id="T001",
                translations=[LocalizedTerm(lang="en", term="CAN bus")],
            ),
            TermEntry(
                id="T002",
                translations=[LocalizedTerm(lang="en", term="ECU")],
            ),
            TermEntry(
                id="T003",
                translations=[LocalizedTerm(lang="en", term="diagnostic")],
            ),
            TermEntry(
                id="T004",
                translations=[LocalizedTerm(lang="en", term="HIL")],
            ),
        ],
    )


class TestPerfectReport:
    def test_score_above_80(self, analyzer: DefectAnalyzer) -> None:
        result = analyzer.analyze(_perfect_report())
        assert result.composite_score > 80
        assert result.report_id == "BUG-001"

    def test_field_completeness_high(self, analyzer: DefectAnalyzer) -> None:
        result = analyzer.analyze(_perfect_report())
        assert result.field_completeness == 100.0
        assert len(result.missing_fields) == 0

    def test_reproducibility_high(self, analyzer: DefectAnalyzer) -> None:
        result = analyzer.analyze(_perfect_report())
        assert result.reproducibility == 100.0

    def test_severity_info(self, analyzer: DefectAnalyzer) -> None:
        result = analyzer.analyze(_perfect_report())
        assert result.severity == "info"


class TestMinimalReport:
    def test_score_below_40(self, analyzer: DefectAnalyzer) -> None:
        result = analyzer.analyze(_minimal_report())
        assert result.composite_score < 40

    def test_missing_fields(self, analyzer: DefectAnalyzer) -> None:
        result = (
            analyzer.analyzer(_minimal_report())
            if False
            else analyzer.analyze(_minimal_report())
        )
        assert "title" in result.missing_fields
        assert "description" in result.missing_fields
        assert "steps_to_reproduce" in result.missing_fields
        assert "expected_behavior" in result.missing_fields
        assert "actual_behavior" in result.missing_fields
        assert "environment" in result.missing_fields
        assert "severity" in result.missing_fields
        assert "component" in result.missing_fields

    def test_severity_error(self, analyzer: DefectAnalyzer) -> None:
        result = analyzer.analyze(_minimal_report())
        assert result.severity == "error"


class TestLanguageMixing:
    def test_language_mix_warning(self, analyzer: DefectAnalyzer) -> None:
        result = analyzer.analyze(_mixed_language_report())
        assert result.language_mix_warning is not None
        assert "Language mixing" in result.language_mix_warning

    def test_no_language_mix_for_english(self, analyzer: DefectAnalyzer) -> None:
        result = analyzer.analyze(_perfect_report())
        assert result.language_mix_warning is None


class TestTerminologyCompliance:
    def test_with_glossary(self, analyzer: DefectAnalyzer) -> None:
        glossary = _make_glossary()
        result = analyzer.analyze(_perfect_report(), glossary=glossary)
        # The perfect report contains CAN, ECU, diagnostic, HIL terms
        assert result.terminology_compliance > 0

    def test_without_glossary_defaults_100(self, analyzer: DefectAnalyzer) -> None:
        result = analyzer.analyze(_perfect_report())
        assert result.terminology_compliance == 100.0

    def test_no_matching_terms(self, analyzer: DefectAnalyzer) -> None:
        glossary = _make_glossary()
        # Minimal report has very little text
        result = analyzer.analyze(_minimal_report(), glossary=glossary)
        assert result.terminology_compliance < 100.0


class TestResultModel:
    def test_result_is_valid_model(self, analyzer: DefectAnalyzer) -> None:
        result = analyzer.analyze(_perfect_report())
        data = result.model_dump(mode="json")
        assert "report_id" in data
        assert "composite_score" in data
        assert isinstance(data["missing_fields"], list)
        assert isinstance(data["improvement_suggestions"], list)
