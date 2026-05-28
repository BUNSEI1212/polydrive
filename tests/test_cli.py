"""Tests for the PolyDrive CLI."""

import re

from typer.testing import CliRunner

from polydrive.cli import app

runner = CliRunner()


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_no_args_shows_help() -> None:
    result = runner.invoke(app)
    assert result.exit_code != 0  # Typer no_args_is_help exits with 2
    assert "Language governance" in result.stdout


def test_glossary_help() -> None:
    result = runner.invoke(app, ["glossary", "--help"])
    assert result.exit_code == 0
    assert "import" in result.stdout
    assert "check" in result.stdout
    assert "export" in result.stdout


def test_i18n_help() -> None:
    result = runner.invoke(app, ["i18n", "--help"])
    assert result.exit_code == 0
    assert "check-encoding" in result.stdout
    assert "detect-hardcoded" in result.stdout
    assert "pseudo-localize" in result.stdout
    assert "validate-qt" in result.stdout


def test_serve_help() -> None:
    result = runner.invoke(app, ["serve", "--help"])
    output = _strip_ansi(result.stdout)
    assert result.exit_code == 0
    assert "REST API" in output
    assert "--port" in output


def test_defect_help() -> None:
    result = runner.invoke(app, ["defect", "--help"])
    assert result.exit_code == 0
    assert "analyze" in result.stdout


def test_glossary_help_detailed() -> None:
    result = runner.invoke(app, ["glossary", "import", "--help"])
    output = _strip_ansi(result.stdout)
    assert result.exit_code == 0
    assert "--format" in output or "format" in output


def test_mt_help() -> None:
    result = runner.invoke(app, ["mt", "--help"])
    assert result.exit_code == 0
    assert "translate" in result.stdout


def test_trace_help() -> None:
    result = runner.invoke(app, ["trace", "--help"])
    assert result.exit_code == 0
    assert "sync-gherkin" in result.stdout
