"""Tests for the encoding checker module."""

from __future__ import annotations

from pathlib import Path

from polydrive.core.models import EncodingIssue
from polydrive.i18n_guard.encoding import check_encoding

FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestCheckEncoding:
    """Tests for check_encoding function."""

    def test_detects_gb2312_file(self) -> None:
        """Should detect a non-UTF-8 GB2312 file."""
        issues = check_encoding(FIXTURES / "gb2312_sample.txt", require_utf8=True)
        assert len(issues) >= 1
        assert issues[0].issue_type == "non_utf8"
        assert issues[0].detected_encoding is not None

    def test_detects_bom(self) -> None:
        """Should detect a UTF-8 file with BOM."""
        issues = check_encoding(
            FIXTURES / "utf8_bom_sample.txt",
            fail_on_bom=True,
        )
        assert any(i.issue_type == "has_bom" for i in issues)

    def test_clean_utf8_no_issues(self) -> None:
        """Clean UTF-8 files should have no issues."""
        issues = check_encoding(FIXTURES / "utf8_clean_sample.txt")
        assert len(issues) == 0

    def test_clean_utf8_require_utf8_ok(self) -> None:
        """Clean UTF-8 files should pass even with require_utf8=True."""
        issues = check_encoding(
            FIXTURES / "utf8_clean_sample.txt",
            require_utf8=True,
        )
        assert len(issues) == 0

    def test_skip_binary_file(self) -> None:
        """Binary files should be skipped."""
        issues = check_encoding(FIXTURES / "binary_sample.bin", require_utf8=True)
        assert len(issues) == 0

    def test_skip_empty_file(self) -> None:
        """Empty files should be skipped."""
        issues = check_encoding(FIXTURES / "empty_sample.txt", require_utf8=True)
        assert len(issues) == 0

    def test_directory_scan(self) -> None:
        """Should recursively scan a directory."""
        issues = check_encoding(FIXTURES, require_utf8=True, fail_on_bom=True)
        # Should find at least the GB2312 file and the BOM file
        types = {i.issue_type for i in issues}
        assert "non_utf8" in types
        assert "has_bom" in types

    def test_nonexistent_path(self) -> None:
        """Should report an issue for nonexistent paths."""
        issues = check_encoding(Path("/nonexistent/path/file.txt"))
        assert len(issues) == 1
        assert "does not exist" in issues[0].details

    def test_no_require_utf8_gb2312_ok(self) -> None:
        """GB2312 file without require_utf8 should not be flagged."""
        issues = check_encoding(FIXTURES / "gb2312_sample.txt")
        non_utf8 = [i for i in issues if i.issue_type == "non_utf8"]
        assert len(non_utf8) == 0

    def test_no_fail_on_bom_bom_ok(self) -> None:
        """BOM file without fail_on_bom should not be flagged for BOM."""
        issues = check_encoding(FIXTURES / "utf8_bom_sample.txt")
        bom_issues = [i for i in issues if i.issue_type == "has_bom"]
        assert len(bom_issues) == 0

    def test_issue_model_fields(self) -> None:
        """Returned issues should be proper EncodingIssue instances."""
        issues = check_encoding(FIXTURES / "gb2312_sample.txt", require_utf8=True)
        assert len(issues) >= 1
        issue = issues[0]
        assert isinstance(issue, EncodingIssue)
        assert isinstance(issue.file_path, Path)
        assert issue.expected_encoding == "utf-8"
        assert issue.details != ""
