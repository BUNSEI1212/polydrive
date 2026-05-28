# Contributing to PolyDrive

Thank you for your interest in contributing to PolyDrive!

## Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `python -m pytest -v`
5. Run linting: `ruff check . && ruff format --check .`
6. Submit a pull request

## Code Style

- Python 3.10+ with type hints throughout
- `from __future__ import annotations` in all files
- Line length: 88 characters (handled by ruff)
- Follow existing patterns in the codebase

## Project Structure

```
src/polydrive/
  cli.py              # CLI entry points (Typer)
  api.py              # REST API (FastAPI)
  core/               # Shared models and utilities
  glossary/           # Terminology engine
  i18n_guard/         # Encoding and i18n checks
  defect_guard/       # Defect report quality
  mt_gateway/         # Translation orchestration
  trace/              # Traceability and compliance
  metrics/            # Quality metrics
```

## Adding a New Module

1. Create a new directory under `src/polydrive/`
2. Add models to `src/polydrive/core/_models.py` if needed
3. Implement the module logic
4. Add CLI commands in `src/polydrive/cli.py`
5. Add API endpoints in `src/polydrive/api.py` if applicable
6. Write tests in `tests/test_module_name/`
7. Update README.md

## Testing

- All tests go in `tests/`
- Use pytest fixtures from `tests/conftest.py`
- Test fixtures go in `tests/fixtures/`
- Aim for >80% code coverage on new code

## License

By contributing, you agree that your contributions will be licensed under the same BSL 1.1 license as the project.
