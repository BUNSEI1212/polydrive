"""PolyDrive FastAPI server — REST API for all modules."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from polydrive import __version__
from polydrive.core.models import LangPair
from polydrive.glossary import import_csv, parse_tbx, write_tbx
from polydrive.i18n_guard import check_encoding, detect_hardcoded, pseudo_localize

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
    file: UploadFile = File(...),
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
    file: UploadFile = File(...),
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
    file: UploadFile = File(...),
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

    return {"mode": mode, "keys_processed": len(result) if isinstance(result, dict) else 0}
