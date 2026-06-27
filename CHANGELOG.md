# Changelog

All notable changes to PolyDrive will be documented in this file.

## [Unreleased]

### Added
- `i18n` composite GitHub Action (`.github/actions/i18n-check`) — runs
  `check-encoding` and `detect-hardcoded` as a reusable PR gate. Installable
  from PyPI by default, or from a source checkout via inputs.
- `i18n-guard` workflow that dogfoods the Action on this repository.

### Fixed
- `polydrive i18n detect-hardcoded` now exits non-zero when hardcoded strings
  are found, so it can gate CI (previously it printed issues but exited 0).

## [0.1.0] - 2026-05-28

### Added
- Initial project structure with Hatch build system
- CLI framework with Typer and Rich output
- `glossary` module: TBX v3 parser, CSV adapter, terminology import/check/export/list
- `i18n` module: encoding checker, C/C++ hardcoded CJK detector, pseudo-localization (expand/cjk/rtl), Qt .ts validator
- `defect` module: defect report quality analyzer (field completeness, text quality, reproducibility, terminology), YAML template validation
- `mt` module: multi-engine MT gateway (LibreTranslate, Google Cloud, DeepL, Amazon Translate), SQLite cache, glossary enforcement, usage tracking
- `trace` module: Gherkin multi-language sync checker, UNECE R121 HMI compliance, ASPICE evidence collector
- `metrics` module: quality metrics collector, Prometheus export, HTML report generation
- REST API server with FastAPI (glossary, i18n, health endpoints)
- BSL 1.1 license with 36-month conversion to Apache 2.0
- CI/CD: GitHub Actions (test matrix: 3 OS × 4 Python versions), PyPI trusted publishing
- 139 tests across all modules
