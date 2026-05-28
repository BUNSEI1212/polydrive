"""Tests for the PolyDrive API server."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from polydrive.api import app

client = TestClient(app)

FIXTURES = Path(__file__).parent / "fixtures"


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_openapi_docs() -> None:
    response = client.get("/docs")
    assert response.status_code == 200


def test_glossary_import_tbx() -> None:
    tbx_path = FIXTURES / "automotive_sample.tbx"
    with open(tbx_path, "rb") as f:
        response = client.post(
            "/glossary/import",
            files={"file": ("automotive_sample.tbx", f, "application/xml")},
            data={"domain": "automotive"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["entry_count"] == 6


def test_glossary_check() -> None:
    tbx_path = FIXTURES / "automotive_sample.tbx"
    with open(tbx_path, "rb") as f:
        response = client.post(
            "/glossary/check",
            files={"file": ("automotive_sample.tbx", f, "application/xml")},
            data={"lang_pair": "en:zh"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "issues_found" in data
    assert "issues" in data


def test_i18n_check_encoding() -> None:
    response = client.post(
        "/i18n/check-encoding",
        params={"path": str(FIXTURES), "require_utf8": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert "issues_found" in data


def test_i18n_check_encoding_not_found() -> None:
    response = client.post(
        "/i18n/check-encoding",
        params={"path": "/nonexistent/path"},
    )
    assert response.status_code == 404


def test_i18n_detect_hardcoded() -> None:
    cpp_path = FIXTURES / "hardcoded_sample.cpp"
    response = client.post(
        "/i18n/detect-hardcoded",
        params={"path": str(cpp_path), "language": "cpp"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["issues_found"] >= 1


def test_i18n_pseudo_localize() -> None:
    json_path = FIXTURES / "locale_en.json"
    with open(json_path, "rb") as f:
        response = client.post(
            "/i18n/pseudo-localize",
            files={"file": ("locale_en.json", f, "application/json")},
            data={"mode": "expand"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "expand"
