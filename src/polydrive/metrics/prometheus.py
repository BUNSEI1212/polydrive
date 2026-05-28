"""Prometheus text exposition format exporter for PolyDrive metrics."""

from __future__ import annotations

from polydrive.metrics.collector import MetricsSummary

# Each metric: (name, help_text, value_extractor)
_METRICS = [
    ("polydrive_total_events", "Total metric events collected", lambda s: s.total_events),
    ("polydrive_encoding_checks_total", "Total encoding checks run", lambda s: s.encoding_checks_run),
    ("polydrive_encoding_issues_total", "Total encoding issues found", lambda s: s.encoding_issues_found),
    ("polydrive_encoding_issue_rate", "Encoding issue rate (issues per file)", lambda s: s.encoding_issue_rate),
    ("polydrive_glossary_checks_total", "Total glossary checks run", lambda s: s.glossary_checks_run),
    (
        "polydrive_glossary_consistency_issues_total",
        "Total glossary consistency issues",
        lambda s: s.glossary_consistency_issues,
    ),
    (
        "polydrive_glossary_term_coverage",
        "Glossary term translation coverage percentage",
        lambda s: s.glossary_term_coverage,
    ),
    ("polydrive_defects_analyzed_total", "Total defect reports analyzed", lambda s: s.defects_analyzed),
    (
        "polydrive_defect_quality_score_avg",
        "Average defect quality score",
        lambda s: s.avg_defect_quality_score,
    ),
    (
        "polydrive_low_quality_defects_total",
        "Defect reports with quality score below 50",
        lambda s: s.low_quality_defects,
    ),
    ("polydrive_translations_total", "Total translations made", lambda s: s.translations_made),
    (
        "polydrive_characters_translated_total",
        "Total characters translated",
        lambda s: s.total_characters_translated,
    ),
    (
        "polydrive_translation_latency_ms_avg",
        "Average translation latency in milliseconds",
        lambda s: s.avg_translation_latency_ms,
    ),
    (
        "polydrive_glossary_hit_rate",
        "Percentage of translations where glossary was applied",
        lambda s: s.glossary_hit_rate,
    ),
    ("polydrive_i18n_health_score", "Composite i18n health score", lambda s: s.i18n_health_score),
    (
        "polydrive_terminology_maturity",
        "Terminology maturity score",
        lambda s: s.terminology_maturity,
    ),
]


def format_prometheus(summary: MetricsSummary) -> str:
    """Format metrics as Prometheus text exposition format."""
    lines: list[str] = []

    for name, help_text, extractor in _METRICS:
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name} {extractor(summary)}")

    # Language pair breakdown
    for pair, count in sorted(summary.translations_by_language_pair.items()):
        safe_label = pair.replace(":", "_").replace("-", "_")
        lines.append(f'# HELP polydrive_translations_by_pair "Translations by language pair"')
        lines.append(f'# TYPE polydrive_translations_by_pair counter')
        lines.append(f'polydrive_translations_by_pair{{pair="{pair}"}} {count}')

    # Quality distribution
    for bucket, count in sorted(summary.defect_quality_distribution.items()):
        safe_bucket = bucket.replace("-", "_")
        lines.append(f'# HELP polydrive_defect_quality_bucket "Defect quality score distribution"')
        lines.append(f'# TYPE polydrive_defect_quality_bucket counter')
        lines.append(f'polydrive_defect_quality_bucket{{bucket="{bucket}"}} {count}')

    return "\n".join(lines) + "\n"
