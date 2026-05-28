"""Tests for the hardcoded string detector module."""

from __future__ import annotations

from pathlib import Path

import pytest

from polydrive.core.models import HardcodedStringIssue
from polydrive.i18n_guard.hardcoded import detect_hardcoded

FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestDetectHardcoded:
    """Tests for detect_hardcoded function."""

    def test_detects_cjk_strings(self) -> None:
        """Should detect CJK string literals."""
        issues = detect_hardcoded(FIXTURES / "hardcoded_sample.cpp")
        cjk_texts = [i.text for i in issues]
        assert any("你好世界" in t for t in cjk_texts)

    def test_detects_japanese_strings(self) -> None:
        """Should detect Japanese katakana string literals."""
        issues = detect_hardcoded(FIXTURES / "hardcoded_sample.cpp")
        texts = [i.text for i in issues]
        assert any("エラー" in t for t in texts)

    def test_detects_korean_strings(self) -> None:
        """Should detect Korean hangul string literals."""
        issues = detect_hardcoded(FIXTURES / "hardcoded_sample.cpp")
        texts = [i.text for i in issues]
        assert any("안녕하세요" in t for t in texts)

    def test_skips_ascii_strings(self) -> None:
        """Should not flag ASCII-only strings."""
        issues = detect_hardcoded(FIXTURES / "hardcoded_sample.cpp")
        texts = [i.text for i in issues]
        assert "ASCII only" not in texts

    def test_skips_commented_strings(self) -> None:
        """Should not flag strings inside comments."""
        issues = detect_hardcoded(FIXTURES / "hardcoded_sample.cpp")
        texts = [i.text for i in issues]
        # "注释" is inside a comment and should NOT appear
        assert "注释" not in texts

    def test_returns_correct_model_type(self) -> None:
        """Should return HardcodedStringIssue instances."""
        issues = detect_hardcoded(FIXTURES / "hardcoded_sample.cpp")
        assert len(issues) >= 1
        assert all(isinstance(i, HardcodedStringIssue) for i in issues)

    def test_issue_has_line_and_column(self) -> None:
        """Issues should have valid line and column numbers."""
        issues = detect_hardcoded(FIXTURES / "hardcoded_sample.cpp")
        assert len(issues) >= 1
        for issue in issues:
            assert issue.line >= 1
            assert issue.column >= 1

    def test_issue_language_field(self) -> None:
        """Issues should have the specified language."""
        issues = detect_hardcoded(FIXTURES / "hardcoded_sample.cpp", language="c")
        for issue in issues:
            assert issue.language == "c"

    def test_directory_scan(self) -> None:
        """Should scan a directory for C++ files."""
        issues = detect_hardcoded(FIXTURES)
        assert any("hardcoded_sample.cpp" in str(i.file_path) for i in issues)

    def test_nonexistent_path(self) -> None:
        """Should return empty list for nonexistent path."""
        issues = detect_hardcoded(Path("/nonexistent/path"))
        assert len(issues) == 0

    def test_non_cpp_file_skipped(self) -> None:
        """Should skip non-C/C++ files."""
        issues = detect_hardcoded(FIXTURES / "utf8_clean_sample.txt")
        assert len(issues) == 0

    def test_exclude_pattern(self) -> None:
        """Should exclude files matching the pattern."""
        issues = detect_hardcoded(
            FIXTURES,
            exclude_pattern=r"hardcoded",
        )
        assert not any("hardcoded" in str(i.file_path) for i in issues)

    def test_empty_cpp_file(self) -> None:
        """Should handle empty C++ files gracefully."""
        empty_cpp = FIXTURES / "empty_sample.cpp"
        empty_cpp.write_text("", encoding="utf-8")
        try:
            issues = detect_hardcoded(empty_cpp)
            assert len(issues) == 0
        finally:
            empty_cpp.unlink(missing_ok=True)
