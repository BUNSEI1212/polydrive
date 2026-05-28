# PolyDrive

[![CI](https://github.com/BUNSEI1212/polydrive/actions/workflows/test.yml/badge.svg)](https://github.com/BUNSEI1212/polydrive/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-BSL%201.1-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](pyproject.toml)

**[English](README.md)** | [中文](README.zh-CN.md) | [日本語](README.ja.md)

> Language governance toolkit for multinational automotive testing teams.

PolyDrive makes language-related friction **visible, measurable, and actionable** in your testing workflow. It's a CLI-first toolkit for terminology consistency, defect quality, i18n guarding, translation orchestration, and compliance traceability.

## Why PolyDrive?

In multinational automotive testing, language isn't a "translation efficiency" problem — it's a **defect amplifier** that impacts:

- **Requirements traceability** when terms drift across languages
- **Defect reproduction rates** when descriptions lose meaning in translation
- **CI pipelines** when encoding issues cause ghost bugs
- **Compliance** when HMI text doesn't meet regional regulations

Existing tools solve parts of the problem, but few open-source tools connect terminology, defect quality, i18n checks, and traceability specifically for automotive testing workflows. PolyDrive fills this gap.

## Six Modules

| Module | CLI Command | Purpose |
|--------|-------------|---------|
| `glossary` | `polydrive glossary` | TBX/CSV terminology import, consistency checking, export |
| `i18n` | `polydrive i18n` | Encoding checks, hardcoded CJK detection, pseudo-localization, Qt validation |
| `defect` | `polydrive defect` | Defect report quality scoring, template validation, language detection |
| `mt` | `polydrive mt` | Multi-engine translation with glossary enforcement and caching |
| `trace` | `polydrive trace` | Gherkin multi-language sync, UNECE R121 compliance, ASPICE evidence |
| `metrics` | `polydrive metrics` | Quality metrics summary, Prometheus export, HTML reports |

Plus `polydrive serve` to start the REST API server.

## Quick Start

```bash
# Install from source
git clone https://github.com/BUNSEI1212/polydrive.git
cd polydrive
pip install -e .

# Check file encodings
polydrive i18n check-encoding examples/bad_encoding/ --require-utf8

# Detect hardcoded CJK in C/C++ source
polydrive i18n detect-hardcoded examples/cpp_project/ --lang cpp

# Import a multilingual glossary
polydrive glossary import examples/automotive_terms.csv

# Generate pseudo-localized resources
polydrive i18n pseudo-localize examples/locales/en.json --mode expand+cjk

# Analyze a defect report
polydrive defect analyze --input examples/bug_report_zh.json

# Start REST API server
polydrive serve --port 8080
```

See [examples/README.md](examples/README.md) for detailed demo instructions.

## More Commands

```bash
# Terminology consistency check (requires TBX format)
polydrive glossary check terms.tbx --lang-pair en:zh

# Translate with glossary enforcement
polydrive mt translate --text "Bremsfehler erkannt" --from de --to en --glossary terms.tbx

# Validate Qt translations
polydrive i18n validate-qt translations/app_zh_CN.ts

# Check Gherkin feature sync across languages
polydrive trace sync-gherkin --base en --compare zh,de --features tests/

# Check UNECE R121 HMI compliance
polydrive trace unece-check --manifest hmi_manifest.json

# Collect ASPICE language evidence
polydrive trace aspice-evidence --project .

# View quality metrics
polydrive metrics summary --input metrics.json
```

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      PolyDrive Platform                        │
├──────────┬──────────┬──────────┬───────────┬─────────────────┤
│ glossary │ defect   │ i18n     │ mt        │ trace / metrics │
│ 术语引擎  │ 质检器    │ 国际化守卫 │ 翻译编排   │ 追溯 / 度量     │
├──────────┴──────────┴──────────┴───────────┴─────────────────┤
│            core (terminology / encoding / models)               │
├──────────────────────────────────────────────────────────────┤
│   CLI (Typer)   │   API (FastAPI)   │   Plugins              │
└──────────────────────────────────────────────────────────────┘
```

## Standards Support

- **TBX (ISO 30042)** — Terminology exchange
- **TMX** — Translation memory exchange
- **BCP 47** — Language tag identification
- **Automotive SPICE 4.0** — Process compliance evidence (SWE.1–SWE.6, MAN.6)
- **UNECE R121** — HMI tell-tale and indicator requirements
- **Gherkin** — Multi-language BDD scenario management (70+ languages)

## Development

```bash
git clone https://github.com/BUNSEI1212/polydrive.git
cd polydrive

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest -v

# Lint
ruff check .
ruff format --check .
```

## License

PolyDrive is available under the **Business Source License 1.1**.

- **Non-commercial use**: Free (academic, personal, open source projects)
- **Commercial use**: Requires a commercial license
- **Change Date**: Each version converts to **Apache License 2.0** 36 months after release

See [LICENSE](LICENSE) for details.
