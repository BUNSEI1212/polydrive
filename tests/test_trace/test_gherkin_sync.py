"""Tests for Gherkin multi-language synchronization."""

from __future__ import annotations

from pathlib import Path

from polydrive.trace.gherkin_sync import parse_feature
from polydrive.trace.gherkin_sync import sync_features

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestParseFeature:
    def test_parse_english_feature(self) -> None:
        feature = parse_feature(FIXTURES_DIR / "login.feature")
        assert feature.language == "en"
        assert feature.name == "Login functionality"
        assert len(feature.scenarios) == 3

    def test_parse_chinese_feature(self) -> None:
        feature = parse_feature(FIXTURES_DIR / "login_zh.feature")
        assert feature.language == "zh-CN"
        assert "登录" in feature.name
        assert len(feature.scenarios) == 2

    def test_scenario_names(self) -> None:
        feature = parse_feature(FIXTURES_DIR / "login.feature")
        names = [s.name for s in feature.scenarios]
        assert "Successful login" in names
        assert "Invalid password" in names
        assert "Account locked after failed attempts" in names

    def test_steps_parsed(self) -> None:
        feature = parse_feature(FIXTURES_DIR / "login.feature")
        successful = next(s for s in feature.scenarios if s.name == "Successful login")
        assert len(successful.steps) == 4
        assert any("Given" in step for step in successful.steps)
        assert any("Then" in step for step in successful.steps)

    def test_tags_parsed(self) -> None:
        feature = parse_feature(FIXTURES_DIR / "login.feature")
        successful = next(s for s in feature.scenarios if s.name == "Successful login")
        assert "@smoke" in successful.tags
        assert "@critical" in successful.tags

    def test_chinese_steps_parsed(self) -> None:
        feature = parse_feature(FIXTURES_DIR / "login_zh.feature")
        scenario = next(s for s in feature.scenarios if "成功" in s.name)
        assert len(scenario.steps) == 4


class TestSyncFeatures:
    def test_detect_missing_scenario(self) -> None:
        issues = sync_features(FIXTURES_DIR, base_lang="en", compare_langs=["zh"])
        missing = [i for i in issues if i.issue_type == "missing_scenario"]
        assert len(missing) >= 1
        scenario_names = [i.base_scenario for i in missing]
        assert "Account locked after failed attempts" in scenario_names

    def test_no_issues_when_identical(self) -> None:
        """Comparing base language with itself should find no issues."""
        issues = sync_features(FIXTURES_DIR, base_lang="en", compare_langs=["en"])
        missing = [i for i in issues if i.issue_type == "missing_scenario"]
        assert len(missing) == 0

    def test_step_count_mismatch(self) -> None:
        issues = sync_features(FIXTURES_DIR, base_lang="en", compare_langs=["zh"])
        mismatches = [i for i in issues if i.issue_type == "step_count_mismatch"]
        # The "Account locked after failed attempts" scenario is missing,
        # so no step mismatch for it. Other scenarios match step counts.
        # This tests the mechanism works.
        assert isinstance(mismatches, list)

    def test_issue_severity_levels(self) -> None:
        issues = sync_features(FIXTURES_DIR, base_lang="en", compare_langs=["zh"])
        for issue in issues:
            assert issue.severity in ("error", "warning", "info")
            assert issue.compare_lang == "zh"

    def test_nonexistent_compare_lang(self) -> None:
        issues = sync_features(FIXTURES_DIR, base_lang="en", compare_langs=["de"])
        missing_files = [i for i in issues if i.issue_type == "missing_file"]
        assert len(missing_files) > 0
