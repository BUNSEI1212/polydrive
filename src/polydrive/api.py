"""PolyDrive FastAPI server — REST API for all modules."""

from __future__ import annotations

import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi import File
from fastapi import HTTPException
from fastapi import Query
from fastapi import UploadFile
from fastapi.responses import PlainTextResponse

from polydrive import __version__
from polydrive.core.models import DefectReport
from polydrive.core.models import LangPair
from polydrive.defect_guard import DefectAnalyzer
from polydrive.defect_guard.template import load_template
from polydrive.defect_guard.template import validate_report
from polydrive.glossary import import_csv
from polydrive.glossary import parse_tbx
from polydrive.i18n_guard import check_encoding
from polydrive.i18n_guard import detect_hardcoded
from polydrive.i18n_guard import pseudo_localize
from polydrive.metrics.collector import load_collector_from_json
from polydrive.mt_gateway import MTGateway
from polydrive.trace import check_unece_r121
from polydrive.trace import collect_aspice_evidence
from polydrive.trace import sync_features

app = FastAPI(
    title="PolyDrive API",
    description="Language governance toolkit for multinational automotive testing.",
    version=__version__,
)


# ── Health ─────────────────────────────────────────────────────────


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


# ── Glossary endpoints ─────────────────────────────────────────────


@app.post("/glossary/import")
async def glossary_import(
    file: UploadFile = File(...),  # noqa: B008
    domain: str = "automotive",
    format: str | None = None,
) -> dict[str, Any]:
    """Import a glossary file (TBX or CSV)."""
    content = await file.read()
    suffix = Path(file.filename or "").suffix.lower()

    fmt = format or ("tbx" if suffix in (".tbx", ".xml") else "csv")

    tmp = Path(tempfile.mktemp(suffix=suffix, prefix="polydrive_upload_"))
    tmp.write_bytes(content)

    try:
        if fmt == "tbx":
            glossary = parse_tbx(tmp)
        elif fmt == "csv":
            glossary = import_csv(tmp, domain=domain)
        else:
            raise HTTPException(400, f"Unsupported format: {fmt}")
    finally:
        tmp.unlink(missing_ok=True)

    return {
        "id": glossary.id,
        "title": glossary.title,
        "domain": glossary.domain,
        "entry_count": len(glossary.entries),
        "source_lang": glossary.source_lang,
    }


@app.post("/glossary/check")
async def glossary_check(
    file: UploadFile = File(...),  # noqa: B008
    lang_pair: str = "en:zh",
) -> dict[str, Any]:
    """Check terminology consistency in a glossary."""
    content = await file.read()
    tmp = Path(tempfile.mktemp(suffix=".tbx", prefix="polydrive_check_"))
    tmp.write_bytes(content)

    try:
        glossary = parse_tbx(tmp)
        parts = lang_pair.split(":")
        if len(parts) != 2:
            raise HTTPException(400, "Invalid lang_pair. Use 'en:zh'.")
        pair = LangPair(source=parts[0], target=parts[1])
        issues = glossary.check_consistency(pair)
    finally:
        tmp.unlink(missing_ok=True)

    return {
        "total_entries": len(glossary.entries),
        "issues_found": len(issues),
        "issues": [i.model_dump(mode="json") for i in issues],
    }


# ── i18n-guard endpoints ───────────────────────────────────────────


@app.post("/i18n/check-encoding")
async def i18n_check_encoding(
    path: str,
    require_utf8: bool = False,
    fail_on_bom: bool = False,
) -> dict[str, Any]:
    """Check file encodings in a path."""
    target = Path(path)
    if not target.exists():
        raise HTTPException(404, f"Path not found: {path}")

    issues = check_encoding(target, require_utf8=require_utf8, fail_on_bom=fail_on_bom)
    return {
        "path": path,
        "issues_found": len(issues),
        "issues": [i.model_dump(mode="json") for i in issues],
    }


@app.post("/i18n/detect-hardcoded")
async def i18n_detect_hardcoded(
    path: str,
    language: str = "cpp",
    exclude: str | None = None,
) -> dict[str, Any]:
    """Detect hardcoded non-ASCII strings in source code."""
    target = Path(path)
    if not target.exists():
        raise HTTPException(404, f"Path not found: {path}")

    issues = detect_hardcoded(target, language=language, exclude_pattern=exclude)
    return {
        "path": path,
        "issues_found": len(issues),
        "issues": [i.model_dump(mode="json") for i in issues],
    }


@app.post("/i18n/pseudo-localize")
async def i18n_pseudo_localize(
    file: UploadFile = File(...),  # noqa: B008
    mode: str = "expand",
) -> dict[str, Any]:
    """Generate pseudo-localized resources."""
    content = await file.read()
    suffix = Path(file.filename or "").suffix.lower()
    tmp = Path(tempfile.mktemp(suffix=suffix, prefix="polydrive_pseudo_"))
    tmp.write_bytes(content)

    try:
        result = pseudo_localize(tmp, mode=mode)
    finally:
        tmp.unlink(missing_ok=True)

    return {
        "mode": mode,
        "keys_processed": len(result) if isinstance(result, dict) else 0,
    }


# ── Defect-guard endpoints ──────────────────────────────────────────


@app.post("/defect/analyze")
async def defect_analyze(report: DefectReport) -> dict[str, Any]:
    """Analyze defect/bug report quality."""
    analyzer = DefectAnalyzer()
    result = analyzer.analyze(report)
    return result.model_dump(mode="json")


@app.post("/defect/validate-template")
async def defect_validate_template(
    template_path: str,
    report: DefectReport,
) -> dict[str, Any]:
    """Validate a defect report against a YAML template."""
    tpl = Path(template_path)
    if not tpl.exists():
        raise HTTPException(404, f"Template not found: {template_path}")

    try:
        template = load_template(tpl)
    except Exception as exc:
        raise HTTPException(400, f"Invalid template: {exc}") from exc

    violations = validate_report(report, template)
    return {
        "template_name": template.name,
        "violations_found": len(violations),
        "violations": violations,
    }


# ── MT-gateway endpoints ────────────────────────────────────────────

_gateway = MTGateway()


@app.post("/mt/translate")
async def mt_translate(
    text: str,
    source_lang: str,
    target_lang: str,
    engine: str | None = None,
    glossary_path: str | None = None,
) -> dict[str, Any]:
    """Translate text through the MT gateway."""
    glossary = None
    if glossary_path:
        gp = Path(glossary_path)
        if not gp.exists():
            raise HTTPException(404, f"Glossary not found: {glossary_path}")
        try:
            glossary = parse_tbx(gp)
        except Exception as exc:
            raise HTTPException(400, f"Invalid glossary: {exc}") from exc

    try:
        result = _gateway.translate(
            text,
            source_lang,
            target_lang,
            engine=engine,
            glossary=glossary,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(400, str(exc)) from exc

    return result.model_dump(mode="json")


@app.get("/mt/usage")
async def mt_usage() -> dict[str, Any]:
    """Return MT gateway usage statistics."""
    stats = _gateway.usage_stats()
    return stats.model_dump(mode="json")


# ── Trace endpoints ─────────────────────────────────────────────────


@app.post("/trace/sync-gherkin")
async def trace_sync_gherkin(
    features_path: str,
    base_lang: str,
    compare_langs: list[str],
) -> dict[str, Any]:
    """Compare Gherkin feature files across languages."""
    target = Path(features_path)
    if not target.exists():
        raise HTTPException(404, f"Path not found: {features_path}")

    issues = sync_features(target, base_lang, compare_langs)
    return {
        "features_path": features_path,
        "base_lang": base_lang,
        "issues_found": len(issues),
        "issues": [asdict(i) for i in issues],
    }


@app.post("/trace/unece-check")
async def trace_unece_check(hmi_manifest: dict[str, Any]) -> dict[str, Any]:
    """Check HMI manifest against UNECE R121 requirements."""
    issues = check_unece_r121(hmi_manifest)
    return {
        "issues_found": len(issues),
        "issues": [asdict(i) for i in issues],
    }


@app.post("/trace/aspice-evidence")
async def trace_aspice_evidence(project_path: str) -> dict[str, Any]:
    """Scan project directory for ASPICE language-related evidence."""
    target = Path(project_path)
    if not target.exists():
        raise HTTPException(404, f"Path not found: {project_path}")

    evidence = collect_aspice_evidence(target)
    items = []
    for e in evidence:
        item = asdict(e)
        item["file_path"] = str(item["file_path"]) if item["file_path"] else None
        items.append(item)
    return {
        "project_path": project_path,
        "evidence_found": len(evidence),
        "evidence": items,
    }


# ── Metrics endpoints ───────────────────────────────────────────────


@app.post("/metrics/summary")
async def metrics_summary(metrics_json_path: str) -> dict[str, Any]:
    """Compute a metrics summary from an exported JSON file."""
    target = Path(metrics_json_path)
    if not target.exists():
        raise HTTPException(404, f"Metrics file not found: {metrics_json_path}")

    try:
        collector = load_collector_from_json(target)
    except Exception as exc:
        raise HTTPException(400, f"Invalid metrics file: {exc}") from exc

    summary = collector.compute_summary()
    return summary.model_dump(mode="json")


@app.get("/metrics/prometheus")
async def metrics_prometheus(
    input: str = Query(..., description="Path to metrics JSON file"),
) -> PlainTextResponse:
    """Export metrics as Prometheus text exposition format."""
    target = Path(input)
    if not target.exists():
        raise HTTPException(404, f"Metrics file not found: {input}")

    try:
        collector = load_collector_from_json(target)
    except Exception as exc:
        raise HTTPException(400, f"Invalid metrics file: {exc}") from exc

    text = collector.export_prometheus()
    return PlainTextResponse(content=text, media_type="text/plain")
