"""YAML-based configuration for PolyDrive."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel
from pydantic import Field

DEFAULT_CONFIG_FILENAME = ".polydrive.yaml"


class PolyDriveConfig(BaseModel):
    """PolyDrive configuration model."""

    default_source_lang: str = "en"
    default_target_langs: list[str] = Field(default_factory=lambda: ["zh", "de"])
    glossary_path: str | None = None
    mt_engine: str = "libretranslate"
    mt_engines_config: dict[str, dict[str, str]] = Field(default_factory=dict)
    encoding_require_utf8: bool = False
    encoding_fail_on_bom: bool = False
    encoding_exclude: list[str] = Field(default_factory=list)
    defect_min_score: float = 40.0
    terminology_min_frequency: int = 2
    trace_similarity_threshold: float = 0.5
    output_format: str = "text"  # "text", "json"


def _search_paths() -> list[Path]:
    """Return config file search paths in priority order."""
    return [
        Path.cwd() / DEFAULT_CONFIG_FILENAME,
        Path.home() / DEFAULT_CONFIG_FILENAME,
    ]


def load_config(path: str | Path | None = None) -> PolyDriveConfig:
    """Load configuration from a YAML file.

    If *path* is given, read from that file only.  Otherwise search for
    ``.polydrive.yaml`` in the current directory, then ``~/.polydrive.yaml``.
    Falls back to defaults when no file is found.
    """
    candidates = [Path(path)] if path is not None else _search_paths()

    for candidate in candidates:
        if candidate.is_file():
            data = yaml.safe_load(candidate.read_text(encoding="utf-8"))
            if data is None:
                data = {}
            return PolyDriveConfig.model_validate(data)

    return PolyDriveConfig()


def save_config(config: PolyDriveConfig, path: str | Path) -> None:
    """Write *config* to a YAML file at *path*."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        yaml.dump(config.model_dump(), default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
