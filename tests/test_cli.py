"""Tests for the PolyDrive CLI."""

from typer.testing import CliRunner

from polydrive.cli import app

runner = CliRunner()


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
