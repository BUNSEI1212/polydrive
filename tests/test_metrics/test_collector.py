"""Tests for the metrics collector."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from polydrive.core.models import ConsistencyIssue
from polydrive.core.models import DefectQualityResult
from polydrive.core.models import EncodingIssue
from polydrive.core.models import MTResult
from polydrive.metrics.collector import MetricEvent
from polydrive.metrics.collector import MetricsCollector
from polydrive.metrics.collector import MetricsSummary
from polydrive.metrics.collector import compute_metrics
from polydrive.metrics.collector import load_collector_from_json
from polydrive.metrics.prometheus import format_prometheus


def _encoding_issue(**kwargs: object) -> EncodingIssue:
    defaults = {
        "file_path": Path("test.txt"),
        "issue_type": "non_utf8",
        "details": "test issue",
    }
    defaults.update(kwargs)
    return EncodingIssue(**defaults)  # type: ignore[arg-type]


def _consistency_issue(**kwargs: object) -> ConsistencyIssue:
    defaults = {
        "severity": "warning",
        "issue_type": "inconsistent_translation",
        "source_lang": "en",
        "target_lang": "zh",
        "source_term": "brake",
        "details": "Inconsistent",
    }
    defaults.update(kwargs)
    return ConsistencyIssue(**defaults)  # type: ignore[arg-type]


def _defect_result(**kwargs: object) -> DefectQualityResult:
    defaults = {
        "report_id": "BUG-001",
        "composite_score": 75.0,
        "field_completeness": 80.0,
        "text_quality": 70.0,
        "reproducibility": 75.0,
    }
    defaults.update(kwargs)
    return DefectQualityResult(**defaults)  # type: ignore[arg-type]


def _mt_result(**kwargs: object) -> MTResult:
    defaults = {
        "translated_text": "Bremspedal",
        "engine": "test-engine",
        "glossary_applied": True,
        "applied_terms": [("brake", "Bremspedal")],
        "character_count": 50,
        "latency_ms": 120.0,
    }
    defaults.update(kwargs)
    return MTResult(**defaults)  # type: ignore[arg-type]


class TestMetricsCollector:
    def test_empty_collector(self) -> None:
        collector = MetricsCollector()
        summary = collector.compute_summary()
        assert summary.total_events == 0
        assert summary.i18n_health_score == 0.0

    def test_record_encoding_check(self) -> None:
        collector = MetricsCollector()
        issues = [
            _encoding_issue(),
            _encoding_issue(issue_type="has_bom", details="BOM found"),
        ]
        collector.record_encoding_check(issues, total_files=10)
        summary = collector.compute_summary()

        assert summary.encoding_checks_run == 1
        assert summary.encoding_issues_found == 2
        assert summary.encoding_issue_rate == 0.2

    def test_record_glossary_check(self) -> None:
        collector = MetricsCollector()
        issues = [
            _consistency_issue(issue_type="missing_translation"),
            _consistency_issue(issue_type="inconsistent_translation"),
        ]
        collector.record_glossary_check(issues, total_entries=100)
        summary = collector.compute_summary()

        assert summary.glossary_checks_run == 1
        assert summary.glossary_consistency_issues == 2
        assert summary.glossary_term_coverage == 99.0

    def test_record_defect_analysis(self) -> None:
        collector = MetricsCollector()
        collector.record_defect_analysis(_defect_result(composite_score=30.0))
        collector.record_defect_analysis(_defect_result(composite_score=70.0))
        summary = collector.compute_summary()

        assert summary.defects_analyzed == 2
        assert summary.avg_defect_quality_score == 50.0
        assert summary.low_quality_defects == 1
        assert "0-20" not in summary.defect_quality_distribution
        assert summary.defect_quality_distribution.get("21-40") == 1
        assert summary.defect_quality_distribution.get("61-80") == 1

    def test_record_translation(self) -> None:
        collector = MetricsCollector()
        collector.record_translation(_mt_result(glossary_applied=True), "en", "de")
        collector.record_translation(
            _mt_result(
                glossary_applied=False,
                character_count=100,
                latency_ms=200.0,
            ),
            "en",
            "zh",
        )
        summary = collector.compute_summary()

        assert summary.translations_made == 2
        assert summary.total_characters_translated == 150
        assert summary.avg_translation_latency_ms == 160.0
        assert summary.glossary_hit_rate == 50.0
        assert summary.translations_by_language_pair.get("en:de") == 1
        assert summary.translations_by_language_pair.get("en:zh") == 1

    def test_mixed_events_compute_summary(self) -> None:
        collector = MetricsCollector()
        collector.record_encoding_check([_encoding_issue()], total_files=5)
        collector.record_glossary_check(
            [_consistency_issue(issue_type="missing_translation")],
            total_entries=50,
        )
        collector.record_defect_analysis(_defect_result())
        collector.record_translation(_mt_result(), "en", "de")

        summary = collector.compute_summary()
        assert summary.total_events == 4
        assert summary.period_start is not None
        assert summary.period_end is not None
        assert 0 <= summary.i18n_health_score <= 100

    def test_score_bucket_boundaries(self) -> None:
        collector = MetricsCollector()
        for score in [10, 30, 50, 70, 90]:
            collector.record_defect_analysis(
                _defect_result(composite_score=score, report_id=f"BUG-{score}")
            )
        summary = collector.compute_summary()
        assert summary.defect_quality_distribution == {
            "0-20": 1,
            "21-40": 1,
            "41-60": 1,
            "61-80": 1,
            "81-100": 1,
        }

    def test_record_raw_event(self) -> None:
        collector = MetricsCollector()
        event = MetricEvent(
            timestamp=datetime.now(),
            event_type="custom",
            module="test",
            data={"key": "value"},
        )
        collector.record(event)
        summary = collector.compute_summary()
        assert summary.total_events == 1


class TestComputeMetrics:
    def test_compute_metrics_function(self) -> None:
        events = [
            MetricEvent(
                timestamp=datetime.now(),
                event_type="encoding_check",
                module="i18n_guard",
                data={
                    "issues_count": 3,
                    "total_files": 10,
                    "issue_types": ["non_utf8"],
                },
            ),
        ]
        summary = compute_metrics(events)
        assert summary.encoding_checks_run == 1
        assert summary.encoding_issues_found == 3


class TestExportJson:
    def test_export_and_load_json(self, tmp_path: Path) -> None:
        collector = MetricsCollector()
        collector.record_encoding_check([_encoding_issue()], total_files=5)
        collector.record_translation(_mt_result(), "en", "de")

        json_path = tmp_path / "metrics.json"
        collector.export_json(json_path)

        assert json_path.exists()
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert "summary" in data
        assert "events" in data
        assert len(data["events"]) == 2
        assert data["summary"]["encoding_checks_run"] == 1

        # Round-trip: load back
        loaded = load_collector_from_json(json_path)
        loaded_summary = loaded.compute_summary()
        original_summary = collector.compute_summary()
        assert loaded_summary.total_events == original_summary.total_events
        assert (
            loaded_summary.encoding_issues_found
            == original_summary.encoding_issues_found
        )


class TestPrometheusExport:
    def test_prometheus_format(self) -> None:
        collector = MetricsCollector()
        collector.record_encoding_check(
            [_encoding_issue(), _encoding_issue()], total_files=10
        )
        collector.record_translation(_mt_result(), "en", "de")

        output = collector.export_prometheus()
        assert "# HELP polydrive_encoding_checks_total" in output
        assert "# TYPE polydrive_encoding_checks_total gauge" in output
        assert "polydrive_encoding_checks_total 1" in output
        assert "polydrive_encoding_issues_total 2" in output
        assert "polydrive_translations_by_pair" in output
        assert 'pair="en:de"' in output

    def test_prometheus_empty_summary(self) -> None:
        summary = MetricsSummary()
        output = format_prometheus(summary)
        assert "polydrive_total_events 0" in output
        assert "polydrive_encoding_checks_total 0" in output

    def test_prometheus_defect_distribution(self) -> None:
        collector = MetricsCollector()
        collector.record_defect_analysis(_defect_result(composite_score=35.0))
        output = collector.export_prometheus()
        assert "polydrive_defect_quality_bucket" in output
        assert 'bucket="21-40"' in output
