"""Metrics collector for PolyDrive operations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from polydrive.core.models import ConsistencyIssue
from polydrive.core.models import DefectQualityResult
from polydrive.core.models import EncodingIssue
from polydrive.core.models import MTResult


@dataclass
class MetricEvent:
    """A single metric event record."""

    timestamp: datetime
    event_type: (
        str  # "encoding_check", "glossary_check", "defect_analysis", "translation"
    )
    module: str  # "i18n_guard", "glossary", "defect_guard", "mt_gateway"
    data: dict


class MetricsSummary(BaseModel):
    """Summary of all collected metrics."""

    period_start: str | None = None
    period_end: str | None = None
    total_events: int = 0

    # Encoding metrics
    encoding_checks_run: int = 0
    encoding_issues_found: int = 0
    encoding_issue_rate: float = 0.0  # issues / total_files

    # Glossary metrics
    glossary_checks_run: int = 0
    glossary_consistency_issues: int = 0
    glossary_term_coverage: float = 0.0  # % of terms with translations

    # Defect quality metrics
    defects_analyzed: int = 0
    avg_defect_quality_score: float = 0.0
    low_quality_defects: int = 0  # score < 50
    defect_quality_distribution: dict[str, int] = {}

    # Translation metrics
    translations_made: int = 0
    total_characters_translated: int = 0
    avg_translation_latency_ms: float = 0.0
    glossary_hit_rate: float = 0.0  # % of translations where glossary was applied
    translations_by_language_pair: dict[str, int] = {}

    # Computed overall metrics
    i18n_health_score: float = 0.0  # composite: 100 - (weighted issues)
    terminology_maturity: float = 0.0  # based on glossary coverage


class MetricsCollector:
    """Collects and computes language quality metrics from PolyDrive operations."""

    def __init__(self) -> None:
        self._events: list[MetricEvent] = []

    def record(self, event: MetricEvent) -> None:
        """Record a raw metric event."""
        self._events.append(event)

    def record_encoding_check(
        self, issues: list[EncodingIssue], total_files: int
    ) -> None:
        """Record results of an encoding check."""
        self._events.append(
            MetricEvent(
                timestamp=datetime.now(),
                event_type="encoding_check",
                module="i18n_guard",
                data={
                    "issues_count": len(issues),
                    "total_files": total_files,
                    "issue_types": [i.issue_type for i in issues],
                },
            )
        )

    def record_glossary_check(
        self, issues: list[ConsistencyIssue], total_entries: int
    ) -> None:
        """Record results of a glossary consistency check."""
        missing = sum(1 for i in issues if i.issue_type == "missing_translation")
        self._events.append(
            MetricEvent(
                timestamp=datetime.now(),
                event_type="glossary_check",
                module="glossary",
                data={
                    "issues_count": len(issues),
                    "total_entries": total_entries,
                    "missing_translations": missing,
                    "inconsistent_translations": len(issues) - missing,
                },
            )
        )

    def record_defect_analysis(self, result: DefectQualityResult) -> None:
        """Record results of a defect quality analysis."""
        bucket = _score_bucket(result.composite_score)
        self._events.append(
            MetricEvent(
                timestamp=datetime.now(),
                event_type="defect_analysis",
                module="defect_guard",
                data={
                    "report_id": result.report_id,
                    "composite_score": result.composite_score,
                    "score_bucket": bucket,
                    "detected_language": result.detected_language,
                },
            )
        )

    def record_translation(
        self, result: MTResult, source_lang: str, target_lang: str
    ) -> None:
        """Record results of a machine translation."""
        pair = f"{source_lang}:{target_lang}"
        self._events.append(
            MetricEvent(
                timestamp=datetime.now(),
                event_type="translation",
                module="mt_gateway",
                data={
                    "engine": result.engine,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "language_pair": pair,
                    "character_count": result.character_count,
                    "latency_ms": result.latency_ms,
                    "glossary_applied": result.glossary_applied,
                    "applied_terms_count": len(result.applied_terms),
                },
            )
        )

    def compute_summary(self) -> MetricsSummary:
        """Compute a summary from all collected events."""
        summary = MetricsSummary()

        if not self._events:
            return summary

        timestamps = [e.timestamp for e in self._events]
        summary.period_start = min(timestamps).isoformat()
        summary.period_end = max(timestamps).isoformat()
        summary.total_events = len(self._events)

        # Accumulators
        total_files_checked = 0
        total_entries_checked = 0
        total_missing = 0
        total_inconsistent = 0
        defect_scores: list[float] = []
        total_latency = 0.0
        total_chars = 0
        glossary_hits = 0

        for event in self._events:
            if event.event_type == "encoding_check":
                summary.encoding_checks_run += 1
                summary.encoding_issues_found += event.data["issues_count"]
                total_files_checked += event.data["total_files"]

            elif event.event_type == "glossary_check":
                summary.glossary_checks_run += 1
                summary.glossary_consistency_issues += event.data["issues_count"]
                total_entries_checked += event.data["total_entries"]
                total_missing += event.data["missing_translations"]
                total_inconsistent += event.data["inconsistent_translations"]

            elif event.event_type == "defect_analysis":
                summary.defects_analyzed += 1
                score = event.data["composite_score"]
                defect_scores.append(score)
                bucket = event.data["score_bucket"]
                summary.defect_quality_distribution[bucket] = (
                    summary.defect_quality_distribution.get(bucket, 0) + 1
                )

            elif event.event_type == "translation":
                summary.translations_made += 1
                total_chars += event.data["character_count"]
                total_latency += event.data["latency_ms"]
                if event.data["glossary_applied"]:
                    glossary_hits += 1
                pair = event.data["language_pair"]
                summary.translations_by_language_pair[pair] = (
                    summary.translations_by_language_pair.get(pair, 0) + 1
                )

        # Derived metrics
        if total_files_checked > 0:
            summary.encoding_issue_rate = round(
                summary.encoding_issues_found / total_files_checked, 4
            )

        if total_entries_checked > 0:
            coverage_pct = (
                (total_entries_checked - total_missing) / total_entries_checked * 100
            )
            summary.glossary_term_coverage = round(coverage_pct, 2)
            summary.terminology_maturity = round(
                min(
                    100.0,
                    coverage_pct * 0.9
                    + (1 - total_inconsistent / max(total_entries_checked, 1)) * 10,
                ),
                2,
            )

        if defect_scores:
            summary.avg_defect_quality_score = round(
                sum(defect_scores) / len(defect_scores), 2
            )
            summary.low_quality_defects = sum(1 for s in defect_scores if s < 50)

        if summary.translations_made > 0:
            summary.total_characters_translated = total_chars
            summary.avg_translation_latency_ms = round(
                total_latency / summary.translations_made, 2
            )
            summary.glossary_hit_rate = round(
                glossary_hits / summary.translations_made * 100, 2
            )

        # Composite i18n health score
        penalty = 0.0
        penalty += summary.encoding_issue_rate * 25  # up to 25 points
        if total_entries_checked > 0:
            penalty += (1 - summary.glossary_term_coverage / 100) * 25  # up to 25
        if summary.defects_analyzed > 0:
            low_ratio = summary.low_quality_defects / summary.defects_analyzed
            penalty += low_ratio * 25  # up to 25
        if summary.translations_made > 0:
            penalty += (1 - summary.glossary_hit_rate / 100) * 25  # up to 25
        summary.i18n_health_score = round(max(0.0, 100.0 - penalty), 2)

        return summary

    def export_json(self, path: Path) -> None:
        """Export collected events and summary to a JSON file."""
        summary = self.compute_summary()
        payload = {
            "summary": summary.model_dump(),
            "events": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "event_type": e.event_type,
                    "module": e.module,
                    "data": e.data,
                }
                for e in self._events
            ],
        }
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def export_prometheus(self) -> str:
        """Export metrics as Prometheus text exposition format."""
        from polydrive.metrics.prometheus import format_prometheus

        return format_prometheus(self.compute_summary())


def compute_metrics(events: list[MetricEvent]) -> MetricsSummary:
    """Compute a metrics summary from a list of events."""
    collector = MetricsCollector()
    for event in events:
        collector.record(event)
    return collector.compute_summary()


def _score_bucket(score: float) -> str:
    """Map a 0-100 score to a bucket label."""
    if score <= 20:
        return "0-20"
    if score <= 40:
        return "21-40"
    if score <= 60:
        return "41-60"
    if score <= 80:
        return "61-80"
    return "81-100"


def load_collector_from_json(path: Path) -> MetricsCollector:
    """Load a MetricsCollector from a previously exported JSON file."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    collector = MetricsCollector()
    for evt in raw.get("events", []):
        collector.record(
            MetricEvent(
                timestamp=datetime.fromisoformat(evt["timestamp"]),
                event_type=evt["event_type"],
                module=evt["module"],
                data=evt["data"],
            )
        )
    return collector
