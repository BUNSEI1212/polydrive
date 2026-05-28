"""Integration tests using example data from the examples/ directory."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from polydrive.core.models import DefectReport
from polydrive.defect_guard.analyzer import DefectAnalyzer
from polydrive.glossary.csv_adapter import import_csv
from polydrive.i18n_guard.hardcoded import detect_hardcoded

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


class TestDefectAnalyzeExample:
    """Test defect analysis with the example bug report."""

    def test_parse_bug_report(self) -> None:
        data = json.loads((EXAMPLES / "bug_report_zh.json").read_text(encoding="utf-8"))
        report = DefectReport.model_validate(data)
        assert report.id == "BUG-2024-0158"
        assert report.expected_behavior is not None
        assert report.actual_behavior is not None
        assert len(report.steps_to_reproduce) == 4
        assert report.severity == "high"

    def test_analyze_bug_report(self) -> None:
        data = json.loads((EXAMPLES / "bug_report_zh.json").read_text(encoding="utf-8"))
        report = DefectReport.model_validate(data)
        analyzer = DefectAnalyzer()
        result = analyzer.analyze(report)
        assert 0 <= result.composite_score <= 100
        assert 0 <= result.field_completeness <= 100
        assert 0 <= result.reproducibility <= 100
        assert result.report_id == "BUG-2024-0158"
        assert result.detected_language is not None


class TestGlossaryImportExample:
    """Test glossary import with the example CSV."""

    def test_import_automotive_terms(self) -> None:
        glossary = import_csv(EXAMPLES / "automotive_terms.csv")
        assert glossary.id == "automotive_terms"
        assert len(glossary.entries) >= 10

    def test_term_has_multilingual_translations(self) -> None:
        glossary = import_csv(EXAMPLES / "automotive_terms.csv")
        brake = next(
            (e for e in glossary.entries if e.id == "brake_energy_recovery"), None
        )
        assert brake is not None
        langs = {t.lang for t in brake.translations}
        assert "en" in langs
        assert "zh" in langs
        assert "de" in langs
        assert "ja" in langs

    def test_tell_tale_is_regulatory(self) -> None:
        glossary = import_csv(EXAMPLES / "automotive_terms.csv")
        tt = next((e for e in glossary.entries if e.id == "tell_tale"), None)
        assert tt is not None
        assert tt.category.value == "regulatory"


class TestI18nDetectHardcodedExample:
    """Test hardcoded string detection with example C++ files."""

    def test_detect_chinese_strings(self) -> None:
        issues = detect_hardcoded(EXAMPLES / "cpp_project" / "dashboard.cpp")
        assert len(issues) > 0
        texts = [i.text for i in issues]
        # Should detect Chinese strings like braking warnings
        has_chinese = any(any("一" <= c <= "鿿" for c in t) for t in texts)
        assert has_chinese

    def test_detect_japanese_strings(self) -> None:
        issues = detect_hardcoded(EXAMPLES / "cpp_project" / "instrument_cluster.cpp")
        assert len(issues) > 0
        texts = [i.text for i in issues]
        has_japanese = any(any("぀" <= c <= "ヿ" for c in t) for t in texts)
        assert has_japanese

    def test_detect_across_directory(self) -> None:
        issues = detect_hardcoded(EXAMPLES / "cpp_project", language="cpp")
        assert len(issues) >= 9  # 5 Chinese + 4 Japanese


class TestExampleFilesExist:
    """Verify all example files referenced in README exist."""

    @pytest.mark.parametrize(
        "path",
        [
            "bug_report_zh.json",
            "automotive_terms.csv",
            "bad_encoding/shift_jis_file.cpp",
            "bad_encoding/gb2312_file.cpp",
            "bad_encoding/utf8_with_bom.cpp",
            "cpp_project/dashboard.cpp",
            "cpp_project/instrument_cluster.cpp",
            "locales/en.json",
        ],
    )
    def test_file_exists(self, path: str) -> None:
        assert (EXAMPLES / path).is_file(), f"Missing example file: {path}"

    def test_bug_report_is_valid_json(self) -> None:
        data = json.loads((EXAMPLES / "bug_report_zh.json").read_text(encoding="utf-8"))
        assert "id" in data
        assert "title" in data
        assert "expected_behavior" in data
        assert "actual_behavior" in data

    def test_locale_json_is_valid(self) -> None:
        data = json.loads(
            (EXAMPLES / "locales" / "en.json").read_text(encoding="utf-8")
        )
        assert "dashboard" in data
        assert "warnings" in data
        assert "navigation" in data

    def test_csv_has_correct_headers(self) -> None:
        text = (EXAMPLES / "automotive_terms.csv").read_text(encoding="utf-8")
        header = text.split("\n")[0]
        assert "id" in header
        assert "source_term" in header
        assert "source_lang" in header
        assert "target_term" in header
        assert "target_lang" in header
