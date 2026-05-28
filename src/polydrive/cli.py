"""PolyDrive CLI - main entry point."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from polydrive import __version__
from polydrive.core.config import PolyDriveConfig
from polydrive.core.config import load_config
from polydrive.core.config import save_config
from polydrive.core.models import LangPair
from polydrive.defect_guard import DefectAnalyzer
from polydrive.defect_guard.template import load_template
from polydrive.defect_guard.template import validate_report
from polydrive.glossary import import_csv
from polydrive.glossary import parse_tbx
from polydrive.glossary import write_tbx
from polydrive.i18n_guard import check_encoding
from polydrive.i18n_guard import detect_hardcoded
from polydrive.i18n_guard import pseudo_localize
from polydrive.metrics.collector import MetricsSummary
from polydrive.metrics.collector import load_collector_from_json
from polydrive.mt_gateway import MTGateway
from polydrive.mt_gateway.engines.libretranslate import LibreTranslateEngine
from polydrive.trace.aspice import collect_aspice_evidence
from polydrive.trace.gherkin_sync import sync_features
from polydrive.trace.unece import check_unece_r121

# Ensure UTF-8 output on Windows to avoid GBK encoding errors with CJK text
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

rprint = Console().print

# Module-level output format, set by the main callback.
_output_format = "text"

app = typer.Typer(
    name="polydrive",
    help="Language governance toolkit for multinational automotive testing.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

glossary_app = typer.Typer(
    name="glossary",
    help="Terminology engine: import, check, and manage multilingual glossaries.",
    no_args_is_help=True,
)
app.add_typer(glossary_app, name="glossary")

i18n_app = typer.Typer(
    name="i18n",
    help="Internationalization guard: encoding checks, hardcoded string detection, pseudo-localization.",
    no_args_is_help=True,
)
app.add_typer(i18n_app, name="i18n")

defect_app = typer.Typer(
    name="defect",
    help="Defect report quality analysis and template validation.",
    no_args_is_help=True,
)
app.add_typer(defect_app, name="defect")

metrics_app = typer.Typer(
    name="metrics",
    help="Quality metrics: summary, Prometheus export, and HTML reports.",
    no_args_is_help=True,
)
app.add_typer(metrics_app, name="metrics")

mt_app = typer.Typer(
    name="mt",
    help="Machine translation gateway: translate text via multiple MT engines.",
    no_args_is_help=True,
)
app.add_typer(mt_app, name="mt")

trace_app = typer.Typer(
    name="trace",
    help="Cross-language traceability: Gherkin sync, UNECE compliance, ASPICE evidence.",
    no_args_is_help=True,
)
app.add_typer(trace_app, name="trace")

config_app = typer.Typer(
    name="config",
    help="Configuration management: show or initialize PolyDrive settings.",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")


def version_callback(value: bool) -> None:
    if value:
        rprint(f"polydrive {__version__}")
        raise typer.Exit()


def _output(data: Any, table_func: Callable[[], None] | None = None) -> None:
    """Output data in the configured format (text / json / quiet)."""
    if _output_format == "json":
        rprint(json.dumps(data, indent=2, ensure_ascii=False))
    elif _output_format == "quiet":
        pass
    else:
        if table_func:
            table_func()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
    output: str = typer.Option(
        "text",
        "--output",
        "-O",
        help="Output format: text, json, quiet",
    ),
) -> None:
    """PolyDrive - Language governance toolkit for multinational automotive testing."""
    global _output_format
    _output_format = output


# ── Glossary commands ──────────────────────────────────────────────


@glossary_app.command("import")
def glossary_import(
    source: str = typer.Argument(..., help="Path to glossary file (TBX/CSV)"),
    domain: str = typer.Option("automotive", help="Terminology domain"),
    format: str | None = typer.Option(
        None, "--format", "-f", help="Force format (tbx/csv)"
    ),
) -> None:
    """Import a terminology glossary from TBX or CSV."""
    src_path = Path(source)
    if not src_path.exists():
        rprint(f"[red]Error:[/red] File not found: {source}")
        raise typer.Exit(1)

    fmt = format
    if fmt is None:
        suffix = src_path.suffix.lower()
        if suffix in (".tbx", ".xml"):
            fmt = "tbx"
        elif suffix == ".csv":
            fmt = "csv"
        else:
            rprint(
                f"[red]Error:[/red] Cannot detect format from extension '{suffix}'. Use --format."
            )
            raise typer.Exit(1)

    if fmt == "tbx":
        glossary = parse_tbx(src_path)
    elif fmt == "csv":
        glossary = import_csv(src_path, domain=domain)
    else:
        rprint(f"[red]Error:[/red] Unsupported format: {fmt}")
        raise typer.Exit(1)

    def _print_table() -> None:
        rprint(
            f"[green]Imported[/green] {len(glossary.entries)} entries "
            f"from {src_path.name} (domain: {glossary.domain})"
        )
        table = Table(title="Glossary Summary")
        table.add_column("ID", style="cyan")
        table.add_column("Source Term", style="green")
        table.add_column("Target Term", style="yellow")
        table.add_column("Category")

        for entry in glossary.entries[:20]:
            src = entry.get_term(glossary.source_lang)
            tgt = (
                entry.get_term("zh")
                or entry.get_term("zh-Hans")
                or entry.get_term("de")
            )
            table.add_row(
                entry.id,
                src.term if src else "-",
                tgt.term if tgt else "[dim]missing[/dim]",
                entry.category.value,
            )
        rprint(table)
        if len(glossary.entries) > 20:
            rprint(f"[dim]... and {len(glossary.entries) - 20} more entries[/dim]")

    json_data = {
        "file": src_path.name,
        "domain": glossary.domain,
        "entry_count": len(glossary.entries),
        "entries": [
            {
                "id": e.id,
                "source_term": (
                    e.get_term(glossary.source_lang).term
                    if e.get_term(glossary.source_lang)
                    else None
                ),
                "target_term": (
                    (e.get_term("zh") or e.get_term("zh-Hans") or e.get_term("de")).term
                    if (e.get_term("zh") or e.get_term("zh-Hans") or e.get_term("de"))
                    else None
                ),
                "category": e.category.value,
            }
            for e in glossary.entries
        ],
    }
    _output(json_data, _print_table)


@glossary_app.command("check")
def glossary_check(
    source: str = typer.Argument(..., help="Path to TBX glossary file"),
    lang_pair: str = typer.Option("en:zh", help="Language pair to check (e.g. en:zh)"),
) -> None:
    """Check terminology consistency in a glossary."""
    src_path = Path(source)
    if not src_path.exists():
        rprint(f"[red]Error:[/red] File not found: {source}")
        raise typer.Exit(1)

    parts = lang_pair.split(":")
    if len(parts) != 2:
        rprint("[red]Error:[/red] Invalid lang pair format. Use 'en:zh'.")
        raise typer.Exit(1)

    pair = LangPair(source=parts[0], target=parts[1])
    glossary = parse_tbx(src_path)
    issues = glossary.check_consistency(pair)

    if not issues:
        rprint(f"[green]No consistency issues found[/green] for {lang_pair}")
        return

    rprint(f"[yellow]Found {len(issues)} issues[/yellow] for {lang_pair}:\n")
    for issue in issues:
        color = {"error": "red", "warning": "yellow", "info": "blue"}.get(
            issue.severity, "white"
        )
        rprint(
            f"  [{color}]{issue.severity.upper()}[/{color}] "
            f"[{color}]{issue.issue_type}[/{color}]: "
            f"'{issue.source_term}' - {issue.details}"
        )

    error_count = sum(1 for i in issues if i.severity == "error")
    if error_count > 0:
        raise typer.Exit(1)


@glossary_app.command("export")
def glossary_export(
    source: str = typer.Argument(..., help="Source glossary file (TBX)"),
    output: str = typer.Argument(..., help="Output file path"),
    format: str = typer.Option("tbx", "--format", "-f", help="Output format (tbx)"),
) -> None:
    """Export glossary to TBX format."""
    src_path = Path(source)
    out_path = Path(output)

    if not src_path.exists():
        rprint(f"[red]Error:[/red] File not found: {source}")
        raise typer.Exit(1)

    glossary = parse_tbx(src_path)

    if format == "tbx":
        write_tbx(glossary, out_path)
        rprint(f"[green]Exported[/green] {len(glossary.entries)} entries to {out_path}")
    else:
        rprint(f"[red]Error:[/red] Unsupported format: {format}")
        raise typer.Exit(1)


@glossary_app.command("list")
def glossary_list(
    source: str = typer.Argument(..., help="Path to glossary file"),
    lang: str | None = typer.Option(None, help="Filter by language (BCP 47 tag)"),
) -> None:
    """List terms in a glossary."""
    src_path = Path(source)
    if not src_path.exists():
        rprint(f"[red]Error:[/red] File not found: {source}")
        raise typer.Exit(1)

    glossary = parse_tbx(src_path)

    table = Table(title=f"Glossary: {glossary.title or src_path.name}")
    table.add_column("ID", style="cyan", max_width=10)
    table.add_column("Language", style="blue")
    table.add_column("Term", style="green")
    table.add_column("Category")

    for entry in glossary.entries:
        for lt in entry.translations:
            if lang and lt.lang != lang:
                continue
            table.add_row(entry.id, lt.lang, lt.term, entry.category.value)

    rprint(table)


@glossary_app.command("extract")
def glossary_extract(
    path: str = typer.Argument(..., help="Path to source files or a single text file"),
    min_frequency: int = typer.Option(
        2, "--min-frequency", "-n", help="Minimum term frequency"
    ),
    max_terms: int = typer.Option(50, "--max", help="Maximum terms to extract"),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file path (JSON)"
    ),
) -> None:
    """Extract candidate terminology from requirements or specification documents."""
    from polydrive.glossary.extractor import extract_terms

    target = Path(path)
    texts: list[str] = []

    if target.is_file():
        texts.append(target.read_text(encoding="utf-8", errors="replace"))
    elif target.is_dir():
        for ext in ("*.txt", "*.md", "*.rst", "*.feature"):
            for fp in target.rglob(ext):
                texts.append(fp.read_text(encoding="utf-8", errors="replace"))
    else:
        rprint(f"[red]Error:[/red] Path not found: {path}")
        raise typer.Exit(1)

    if not texts:
        rprint("[yellow]No text files found to extract from[/yellow]")
        return

    candidates = extract_terms(texts, min_frequency=min_frequency, max_terms=max_terms)

    if not candidates:
        rprint("[yellow]No candidate terms found[/yellow]")
        return

    table = Table(title=f"Candidate Terms (from {len(texts)} file(s))")
    table.add_column("Term", style="green")
    table.add_column("Score", justify="right")
    table.add_column("Freq", justify="right")
    table.add_column("Source", style="cyan")

    for ct in candidates:
        table.add_row(ct.term, f"{ct.score:.4f}", str(ct.frequency), ct.source)

    rprint(table)

    if output:
        import json as _json

        data = [
            {
                "term": ct.term,
                "score": ct.score,
                "frequency": ct.frequency,
                "source": ct.source,
            }
            for ct in candidates
        ]
        Path(output).write_text(
            _json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        rprint(f"\n[green]Exported[/green] {len(candidates)} candidates to {output}")


# ── i18n commands ──────────────────────────────────────────────────


@i18n_app.command("check-encoding")
def i18n_check_encoding(
    path: str = typer.Argument(..., help="Path to check (file or directory)"),
    require_utf8: bool = typer.Option(
        False, "--require-utf8", help="Fail if files are not UTF-8"
    ),
    fail_on_bom: bool = typer.Option(
        False, "--fail-on-bom", help="Fail if BOM is detected"
    ),
    output_format: str = typer.Option(
        "text", "--output", "-o", help="Output format (text/json)"
    ),
) -> None:
    """Check file encodings and detect issues."""
    target = Path(path)
    issues = check_encoding(target, require_utf8=require_utf8, fail_on_bom=fail_on_bom)

    def _print_table() -> None:
        if not issues:
            rprint(f"[green]No encoding issues found[/green] in {path}")
            return

        table = Table(title=f"Encoding Issues in {path}")
        table.add_column("File", style="cyan")
        table.add_column("Line", justify="right")
        table.add_column("Type", style="yellow")
        table.add_column("Detected", style="red")
        table.add_column("Details")

        for issue in issues:
            table.add_row(
                str(issue.file_path),
                str(issue.line) if issue.line else "-",
                issue.issue_type,
                issue.detected_encoding or "-",
                issue.details,
            )
        rprint(table)

    json_data = [issue.model_dump(mode="json") for issue in issues]
    _output(json_data, _print_table)

    has_errors = any(i.issue_type in ("non_utf8", "has_bom") for i in issues)
    if has_errors:
        raise typer.Exit(1)


@i18n_app.command("detect-hardcoded")
def i18n_detect_hardcoded(
    path: str = typer.Argument(..., help="Path to source files"),
    lang: str = typer.Option("cpp", "--lang", "-l", help="Source language (cpp/c)"),
    exclude: str | None = typer.Option(
        None, "--exclude", help="Exclude pattern (glob)"
    ),
) -> None:
    """Detect hardcoded non-ASCII strings in source code."""
    target = Path(path)
    issues = detect_hardcoded(target, language=lang, exclude_pattern=exclude)

    if not issues:
        rprint(f"[green]No hardcoded strings found[/green] in {path}")
        return

    table = Table(title=f"Hardcoded Strings in {path}")
    table.add_column("File", style="cyan")
    table.add_column("Line", justify="right")
    table.add_column("Col", justify="right")
    table.add_column("Text", style="yellow", max_width=40)

    for issue in issues:
        table.add_row(
            str(issue.file_path),
            str(issue.line),
            str(issue.column),
            issue.text[:40],
        )
    rprint(table)
    rprint(f"\n[yellow]Found {len(issues)} hardcoded non-ASCII string(s)[/yellow]")


@i18n_app.command("pseudo-localize")
def i18n_pseudo_localize(
    source: str = typer.Argument(..., help="Source locale file (JSON/Qt .ts)"),
    mode: str = typer.Option(
        "expand",
        "--mode",
        "-m",
        help="Pseudo-localization mode: expand, cjk, rtl, or expand+cjk+rtl",
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
) -> None:
    """Generate pseudo-localized resources for i18n testing."""
    src_path = Path(source)
    out_path = Path(output) if output else None

    if not src_path.exists():
        rprint(f"[red]Error:[/red] File not found: {source}")
        raise typer.Exit(1)

    result = pseudo_localize(src_path, mode=mode, output=out_path)
    out = out_path or src_path.with_stem(src_path.stem + "_pseudo")
    rprint(f"[green]Generated[/green] pseudo-localized file: {out}")
    rprint(f"  Mode: {mode}")
    rprint(f"  Keys processed: {len(result) if isinstance(result, dict) else 'N/A'}")


@i18n_app.command("validate-qt")
def i18n_validate_qt(
    ts_file: str = typer.Argument(..., help="Path to Qt .ts file"),
) -> None:
    """Validate Qt .ts translation files."""
    ts_path = Path(ts_file)
    if not ts_path.exists():
        rprint(f"[red]Error:[/red] File not found: {ts_file}")
        raise typer.Exit(1)

    from lxml import etree

    tree = etree.parse(str(ts_path))
    root = tree.getroot()

    incomplete = []
    total = 0

    for context in root.findall(".//context"):
        ctx_name = context.findtext("name", "unknown")
        for message in context.findall("message"):
            total += 1
            source_text = message.findtext("source", "")
            translation = message.find("translation")
            if translation is not None:
                trad_type = translation.get("type", "")
                if trad_type in ("unfinished", "vanished"):
                    incomplete.append((ctx_name, source_text, trad_type))

    if not incomplete:
        rprint(f"[green]All {total} translations complete[/green] in {ts_file}")
        return

    table = Table(title=f"Incomplete Translations in {ts_file}")
    table.add_column("Context", style="cyan")
    table.add_column("Source", style="yellow", max_width=50)
    table.add_column("Status", style="red")

    for ctx, src, status in incomplete:
        table.add_row(ctx, src[:50], status)

    rprint(table)
    rprint(f"\n[yellow]{len(incomplete)}/{total} translations incomplete[/yellow]")


# ── Defect commands ────────────────────────────────────────────────


@defect_app.command("analyze")
def defect_analyze(
    input: str = typer.Option(..., "--input", "-i", help="Path to defect report JSON"),
    glossary: str | None = typer.Option(
        None, "--glossary", "-g", help="Path to glossary file (TBX)"
    ),
) -> None:
    """Analyze a single defect report for quality."""
    from polydrive.core.models import DefectReport
    from polydrive.core.models import Glossary

    input_path = Path(input)
    if not input_path.exists():
        rprint(f"[red]Error:[/red] File not found: {input}")
        raise typer.Exit(1)

    report = DefectReport.model_validate_json(input_path.read_text(encoding="utf-8"))
    gl: Glossary | None = None
    if glossary:
        gl = parse_tbx(Path(glossary))

    analyzer = DefectAnalyzer()
    result = analyzer.analyze(report, glossary=gl)
    result_data = result.model_dump(mode="json")
    _output(result_data)


@defect_app.command("batch")
def defect_batch(
    input: str = typer.Option(
        ..., "--input", "-i", help="Path to JSON array of defect reports"
    ),
    output: str = typer.Option(
        ..., "--output", "-o", help="Output path for analysis results JSON"
    ),
) -> None:
    """Batch-analyze multiple defect reports."""
    from polydrive.core.models import DefectReport

    input_path = Path(input)
    output_path = Path(output)
    if not input_path.exists():
        rprint(f"[red]Error:[/red] File not found: {input}")
        raise typer.Exit(1)

    data = json.loads(input_path.read_text(encoding="utf-8"))
    reports = [DefectReport.model_validate(item) for item in data]

    analyzer = DefectAnalyzer()
    results = [analyzer.analyze(r) for r in reports]
    output_path.write_text(
        json.dumps(
            [r.model_dump(mode="json") for r in results], indent=2, ensure_ascii=False
        ),
        encoding="utf-8",
    )
    rprint(f"[green]Analyzed[/green] {len(results)} reports -> {output_path}")


@defect_app.command("validate-template")
def defect_validate_template(
    template: str = typer.Option(..., "--template", "-t", help="Path to YAML template"),
    input: str = typer.Option(..., "--input", "-i", help="Path to defect report JSON"),
) -> None:
    """Validate a defect report against a YAML template."""
    from polydrive.core.models import DefectReport

    template_path = Path(template)
    input_path = Path(input)
    if not template_path.exists():
        rprint(f"[red]Error:[/red] Template not found: {template}")
        raise typer.Exit(1)
    if not input_path.exists():
        rprint(f"[red]Error:[/red] File not found: {input}")
        raise typer.Exit(1)

    tmpl = load_template(template_path)
    report = DefectReport.model_validate_json(input_path.read_text(encoding="utf-8"))
    violations = validate_report(report, tmpl)

    if not violations:
        rprint(f"[green]Report passes template '{tmpl.name}'[/green]")
    else:
        rprint(
            f"[yellow]{len(violations)} violation(s) against template '{tmpl.name}':[/yellow]"
        )
        for v in violations:
            rprint(f"  - {v}")
        raise typer.Exit(1)


# ── Metrics commands ───────────────────────────────────────────────


@metrics_app.command("summary")
def metrics_summary(
    input: str = typer.Option(..., "--input", "-i", help="Path to metrics JSON file"),
) -> None:
    """Show metrics summary from a previously exported JSON file."""
    in_path = Path(input)
    if not in_path.exists():
        rprint(f"[red]Error:[/red] File not found: {input}")
        raise typer.Exit(1)

    collector = load_collector_from_json(in_path)
    summary = collector.compute_summary()

    def _print_tables() -> None:
        rprint("[bold]PolyDrive Metrics Summary[/bold]")
        rprint(
            f"  Period: {summary.period_start or 'N/A'} - {summary.period_end or 'N/A'}"
        )
        rprint(f"  Total events: {summary.total_events}")

        table = Table(title="Encoding")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        table.add_row("Checks run", str(summary.encoding_checks_run))
        table.add_row("Issues found", str(summary.encoding_issues_found))
        table.add_row("Issue rate", f"{summary.encoding_issue_rate:.4f}")
        rprint(table)

        table = Table(title="Glossary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        table.add_row("Checks run", str(summary.glossary_checks_run))
        table.add_row("Consistency issues", str(summary.glossary_consistency_issues))
        table.add_row("Term coverage", f"{summary.glossary_term_coverage:.1f}%")
        rprint(table)

        table = Table(title="Defect Quality")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        table.add_row("Defects analyzed", str(summary.defects_analyzed))
        table.add_row("Avg quality score", f"{summary.avg_defect_quality_score:.1f}")
        table.add_row("Low quality (<50)", str(summary.low_quality_defects))
        rprint(table)

        table = Table(title="Translations")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        table.add_row("Translations", str(summary.translations_made))
        table.add_row("Characters translated", str(summary.total_characters_translated))
        table.add_row("Avg latency (ms)", f"{summary.avg_translation_latency_ms:.1f}")
        table.add_row("Glossary hit rate", f"{summary.glossary_hit_rate:.1f}%")
        rprint(table)

        rprint(
            f"\n[bold green]i18n Health Score:[/bold green] {summary.i18n_health_score:.1f}"
        )
        rprint(
            f"[bold green]Terminology Maturity:[/bold green] {summary.terminology_maturity:.1f}"
        )

    json_data = summary.model_dump(mode="json")
    _output(json_data, _print_tables)


@metrics_app.command("prometheus")
def metrics_prometheus(
    input: str = typer.Option(..., "--input", "-i", help="Path to metrics JSON file"),
) -> None:
    """Export metrics in Prometheus text exposition format."""
    in_path = Path(input)
    if not in_path.exists():
        rprint(f"[red]Error:[/red] File not found: {input}")
        raise typer.Exit(1)

    collector = load_collector_from_json(in_path)
    rprint(collector.export_prometheus())


@metrics_app.command("report")
def metrics_report(
    input: str = typer.Option(..., "--input", "-i", help="Path to metrics JSON file"),
    output: str = typer.Option(
        "report.html", "--output", "-o", help="Output HTML file path"
    ),
) -> None:
    """Generate an HTML report from metrics data."""
    in_path = Path(input)
    out_path = Path(output)

    if not in_path.exists():
        rprint(f"[red]Error:[/red] File not found: {input}")
        raise typer.Exit(1)

    collector = load_collector_from_json(in_path)
    summary = collector.compute_summary()

    html = _render_html_report(summary)
    out_path.write_text(html, encoding="utf-8")
    rprint(f"[green]Report written to[/green] {out_path}")


def _render_html_report(summary: MetricsSummary) -> str:
    """Render a simple HTML metrics report."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>PolyDrive Metrics Report</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 2rem; background: #f8f9fa; }}
h1 {{ color: #2c3e50; }}
h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 0.3rem; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 1.5rem; background: white; }}
th, td {{ border: 1px solid #dee2e6; padding: 0.6rem 1rem; text-align: left; }}
th {{ background: #3498db; color: white; }}
.score {{ font-size: 2rem; font-weight: bold; }}
.good {{ color: #27ae60; }}
.warn {{ color: #f39c12; }}
.bad {{ color: #e74c3c; }}
</style>
</head>
<body>
<h1>PolyDrive Metrics Report</h1>
<p>Period: {summary.period_start or "N/A"} &mdash; {summary.period_end or "N/A"}</p>

<h2>i18n Health Score</h2>
<p class="score {"good" if summary.i18n_health_score >= 75 else "warn" if summary.i18n_health_score >= 50 else "bad"}">{summary.i18n_health_score:.1f} / 100</p>
<p>Terminology Maturity: {summary.terminology_maturity:.1f}%</p>

<h2>Encoding</h2>
<table><tr><th>Metric</th><th>Value</th></tr>
<tr><td>Checks run</td><td>{summary.encoding_checks_run}</td></tr>
<tr><td>Issues found</td><td>{summary.encoding_issues_found}</td></tr>
<tr><td>Issue rate</td><td>{summary.encoding_issue_rate:.4f}</td></tr>
</table>

<h2>Glossary</h2>
<table><tr><th>Metric</th><th>Value</th></tr>
<tr><td>Checks run</td><td>{summary.glossary_checks_run}</td></tr>
<tr><td>Consistency issues</td><td>{summary.glossary_consistency_issues}</td></tr>
<tr><td>Term coverage</td><td>{summary.glossary_term_coverage:.1f}%</td></tr>
</table>

<h2>Defect Quality</h2>
<table><tr><th>Metric</th><th>Value</th></tr>
<tr><td>Defects analyzed</td><td>{summary.defects_analyzed}</td></tr>
<tr><td>Avg quality score</td><td>{summary.avg_defect_quality_score:.1f}</td></tr>
<tr><td>Low quality (&lt;50)</td><td>{summary.low_quality_defects}</td></tr>
</table>

<h2>Translations</h2>
<table><tr><th>Metric</th><th>Value</th></tr>
<tr><td>Translations</td><td>{summary.translations_made}</td></tr>
<tr><td>Characters translated</td><td>{summary.total_characters_translated}</td></tr>
<tr><td>Avg latency (ms)</td><td>{summary.avg_translation_latency_ms:.1f}</td></tr>
<tr><td>Glossary hit rate</td><td>{summary.glossary_hit_rate:.1f}%</td></tr>
</table>

<h2>Translation Language Pairs</h2>
<table><tr><th>Language Pair</th><th>Count</th></tr>
{"".join(f"<tr><td>{p}</td><td>{c}</td></tr>" for p, c in sorted(summary.translations_by_language_pair.items()))}
</table>

<h2>Defect Quality Distribution</h2>
<table><tr><th>Score Range</th><th>Count</th></tr>
{"".join(f"<tr><td>{b}</td><td>{c}</td></tr>" for b, c in sorted(summary.defect_quality_distribution.items()))}
</table>

</body>
</html>"""


# ── MT commands ─────────────────────────────────────────────────────


def _build_gateway(engine: str | None) -> MTGateway:
    """Build an MTGateway with the requested engine."""
    gw = MTGateway()
    if engine == "libretranslate" or engine is None:
        gw.register(LibreTranslateEngine())
    else:
        rprint(
            f"[red]Error:[/red] Unknown engine '{engine}'. Available: libretranslate"
        )
        raise typer.Exit(1)
    return gw


@mt_app.command("translate")
def mt_translate(
    text: str = typer.Option(..., "--text", "-t", help="Text to translate"),
    source_lang: str = typer.Option(..., "--from", help="Source language (BCP 47)"),
    target_lang: str = typer.Option(..., "--to", help="Target language (BCP 47)"),
    engine: str | None = typer.Option(None, "--engine", "-e", help="MT engine to use"),
    glossary_path: str | None = typer.Option(
        None, "--glossary", "-g", help="TBX glossary for term enforcement"
    ),
) -> None:
    """Translate text using an MT engine."""
    glossary = None
    if glossary_path:
        gpath = Path(glossary_path)
        if not gpath.exists():
            rprint(f"[red]Error:[/red] Glossary file not found: {glossary_path}")
            raise typer.Exit(1)
        glossary = parse_tbx(gpath)

    gw = _build_gateway(engine)
    try:
        result = gw.translate(text, source_lang, target_lang, glossary=glossary)
    except Exception as exc:
        rprint(f"[red]Translation failed:[/red] {exc}")
        raise typer.Exit(1) from None
    finally:
        gw.close()

    rprint(result.translated_text)
    if result.applied_terms:
        rprint(f"[dim]Glossary terms applied: {result.applied_terms}[/dim]")
    rprint(
        f"[dim]Engine: {result.engine} | "
        f"{result.latency_ms:.1f}ms | "
        f"{result.character_count} chars[/dim]"
    )


@mt_app.command("batch")
def mt_batch(
    input_file: str = typer.Option(
        ..., "--input", "-i", help="JSON file with texts to translate"
    ),
    source_lang: str = typer.Option(..., "--from", help="Source language (BCP 47)"),
    target_lang: str = typer.Option(..., "--to", help="Target language (BCP 47)"),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output JSON file path"
    ),
    engine: str | None = typer.Option(None, "--engine", "-e", help="MT engine to use"),
) -> None:
    """Batch translate texts from a JSON file."""
    in_path = Path(input_file)
    if not in_path.exists():
        rprint(f"[red]Error:[/red] File not found: {input_file}")
        raise typer.Exit(1)

    with in_path.open(encoding="utf-8") as f:
        data = json.load(f)

    texts: list[str] = data if isinstance(data, list) else data.get("texts", [])

    if not texts:
        rprint("[red]Error:[/red] No texts found in input file")
        raise typer.Exit(1)

    gw = _build_gateway(engine)
    try:
        results = gw.translate_batch(texts, source_lang, target_lang)
    except Exception as exc:
        rprint(f"[red]Batch translation failed:[/red] {exc}")
        raise typer.Exit(1) from None
    finally:
        gw.close()

    translations = [
        {"source": src, "translated": res.translated_text, "engine": res.engine}
        for src, res in zip(texts, results, strict=True)
    ]

    out_path = (
        Path(output) if output else in_path.with_stem(in_path.stem + "_translated")
    )
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(translations, f, indent=2, ensure_ascii=False)

    rprint(f"[green]Translated[/green] {len(translations)} texts -> {out_path}")

    table = Table(title="Batch Translation Summary")
    table.add_column("Source", style="cyan", max_width=40)
    table.add_column("Translation", style="green", max_width=40)
    table.add_column("Engine")
    for item in translations:
        table.add_row(item["source"][:40], item["translation"][:40], item["engine"])
    rprint(table)


@mt_app.command("usage")
def mt_usage() -> None:
    """Show translation usage statistics."""
    rprint("[dim]No active gateway session. Usage stats are per-session.[/dim]")
    rprint("Register an engine and use `gateway.usage_stats()` programmatically.")


# ── Trace commands ──────────────────────────────────────────────────


@trace_app.command("sync-gherkin")
def trace_sync_gherkin(
    features: str = typer.Argument(..., help="Path to features directory"),
    base: str = typer.Option("en", "--base", help="Base language (BCP 47)"),
    compare: str = typer.Option(
        ..., "--compare", help="Comma-separated compare languages"
    ),
) -> None:
    """Check Gherkin feature files for cross-language synchronization issues."""
    features_dir = Path(features)
    if not features_dir.exists():
        rprint(f"[red]Error:[/red] Directory not found: {features}")
        raise typer.Exit(1)

    compare_langs = [lang.strip() for lang in compare.split(",")]
    issues = sync_features(features_dir, base_lang=base, compare_langs=compare_langs)

    def _print_table() -> None:
        if not issues:
            rprint(f"[green]No sync issues found[/green] across {base}/{compare}")
            return

        rprint(f"[yellow]Found {len(issues)} sync issue(s)[/yellow]:\n")
        for issue in issues:
            color = {"error": "red", "warning": "yellow", "info": "blue"}.get(
                issue.severity, "white"
            )
            rprint(
                f"  [{color}]{issue.severity.upper()}[/{color}] "
                f"[{color}]{issue.issue_type}[/{color}]: "
                f"{issue.details}"
            )

    json_data = [
        {"severity": i.severity, "issue_type": i.issue_type, "details": i.details}
        for i in issues
    ]
    _output(json_data, _print_table)

    error_count = sum(1 for i in issues if i.severity == "error")
    if error_count > 0:
        raise typer.Exit(1)


@trace_app.command("unece-check")
def trace_unece_check(
    manifest: str = typer.Argument(..., help="Path to HMI manifest JSON file"),
    regulation: str = typer.Option(
        "R121", "--regulation", help="Regulation to check (R121)"
    ),
) -> None:
    """Check HMI manifest against UNECE R121 requirements."""
    manifest_path = Path(manifest)
    if not manifest_path.exists():
        rprint(f"[red]Error:[/red] File not found: {manifest}")
        raise typer.Exit(1)

    with open(manifest_path, encoding="utf-8") as f:
        hmi_manifest = json.load(f)

    issues = check_unece_r121(hmi_manifest)

    def _print_table() -> None:
        if not issues:
            rprint(f"[green]No compliance issues found[/green] for {regulation}")
            return

        rprint(
            f"[yellow]Found {len(issues)} compliance issue(s)[/yellow] for {regulation}:\n"
        )

        table = Table(title=f"UNECE {regulation} Compliance Issues")
        table.add_column("Severity", style="red")
        table.add_column("Check", style="cyan")
        table.add_column("Item", style="yellow")
        table.add_column("Details")

        for issue in issues:
            table.add_row(
                issue.severity.upper(),
                issue.check_type,
                issue.item_id or "-",
                issue.details,
            )
        rprint(table)

    json_data = [
        {
            "severity": i.severity,
            "check_type": i.check_type,
            "item_id": i.item_id,
            "details": i.details,
        }
        for i in issues
    ]
    _output(json_data, _print_table)

    error_count = sum(1 for i in issues if i.severity == "error")
    if error_count > 0:
        raise typer.Exit(1)


@trace_app.command("aspice-evidence")
def trace_aspice_evidence(
    project: str = typer.Argument(..., help="Path to project directory"),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output JSON file path"
    ),
) -> None:
    """Scan project directory for ASPICE language-related evidence."""
    project_dir = Path(project)
    if not project_dir.is_dir():
        rprint(f"[red]Error:[/red] Directory not found: {project}")
        raise typer.Exit(1)

    evidence = collect_aspice_evidence(project_dir)

    if output:
        data = [
            {
                "process_id": e.process_id,
                "process_name": e.process_name,
                "evidence_type": e.evidence_type,
                "description": e.description,
                "file_path": str(e.file_path) if e.file_path else None,
                "status": e.status,
            }
            for e in evidence
        ]
        out_path = Path(output)
        out_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        rprint(f"[green]Written[/green] {len(evidence)} evidence items to {out_path}")
    else:
        table = Table(title="ASPICE Evidence")
        table.add_column("Process", style="cyan")
        table.add_column("Type", style="blue")
        table.add_column("Status")
        table.add_column("Description")

        for e in evidence:
            status_color = {
                "found": "green",
                "missing": "red",
                "partial": "yellow",
            }.get(e.status, "white")
            table.add_row(
                f"{e.process_id} ({e.process_name})",
                e.evidence_type,
                f"[{status_color}]{e.status}[/{status_color}]",
                e.description,
            )
        rprint(table)


# ── Config commands ─────────────────────────────────────────────────


@config_app.command("show")
def config_show() -> None:
    """Display current PolyDrive configuration as a Rich table."""
    cfg = load_config()

    table = Table(title="PolyDrive Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("default_source_lang", cfg.default_source_lang)
    table.add_row("default_target_langs", ", ".join(cfg.default_target_langs))
    table.add_row("glossary_path", cfg.glossary_path or "(none)")
    table.add_row("mt_engine", cfg.mt_engine)
    table.add_row(
        "mt_engines_config",
        json.dumps(cfg.mt_engines_config) if cfg.mt_engines_config else "(empty)",
    )
    table.add_row("encoding_require_utf8", str(cfg.encoding_require_utf8))
    table.add_row("encoding_fail_on_bom", str(cfg.encoding_fail_on_bom))
    table.add_row(
        "encoding_exclude",
        ", ".join(cfg.encoding_exclude) if cfg.encoding_exclude else "(none)",
    )
    table.add_row("defect_min_score", str(cfg.defect_min_score))
    table.add_row("terminology_min_frequency", str(cfg.terminology_min_frequency))
    table.add_row("trace_similarity_threshold", str(cfg.trace_similarity_threshold))
    table.add_row("output_format", cfg.output_format)

    rprint(table)


@config_app.command("init")
def config_init() -> None:
    """Create a default .polydrive.yaml in the current directory."""
    dest = Path.cwd() / ".polydrive.yaml"
    if dest.exists():
        rprint(f"[yellow]Config file already exists:[/yellow] {dest}")
        rprint("Remove it first or edit manually to update.")
        raise typer.Exit(1)

    cfg = PolyDriveConfig()
    save_config(cfg, dest)
    rprint(f"[green]Created[/green] default config at {dest}")


# ── Serve command ──────────────────────────────────────────────────


@app.command("serve")
def serve(
    host: str = typer.Option("0.0.0.0", help="Bind host"),
    port: int = typer.Option(8080, help="Bind port"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
) -> None:
    """Start the PolyDrive REST API server."""
    import uvicorn

    rprint(f"[green]Starting PolyDrive API[/green] at http://{host}:{port}")
    rprint(f"  Docs: http://{host}:{port}/docs")
    uvicorn.run("polydrive.api:app", host=host, port=port, reload=reload)
