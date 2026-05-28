"""Tests for PolyDrive configuration loading and persistence."""

from __future__ import annotations

from pathlib import Path

import yaml

from polydrive.core.config import PolyDriveConfig
from polydrive.core.config import load_config
from polydrive.core.config import save_config


class TestPolyDriveConfigDefaults:
    """Test default values of PolyDriveConfig."""

    def test_default_values(self) -> None:
        cfg = PolyDriveConfig()
        assert cfg.default_source_lang == "en"
        assert cfg.default_target_langs == ["zh", "de"]
        assert cfg.glossary_path is None
        assert cfg.mt_engine == "libretranslate"
        assert cfg.mt_engines_config == {}
        assert cfg.encoding_require_utf8 is False
        assert cfg.encoding_fail_on_bom is False
        assert cfg.encoding_exclude == []
        assert cfg.defect_min_score == 40.0
        assert cfg.terminology_min_frequency == 2
        assert cfg.trace_similarity_threshold == 0.5
        assert cfg.output_format == "text"

    def test_custom_values(self) -> None:
        cfg = PolyDriveConfig(
            default_source_lang="de",
            default_target_langs=["en", "fr"],
            mt_engine="google",
            defect_min_score=60.0,
        )
        assert cfg.default_source_lang == "de"
        assert cfg.default_target_langs == ["en", "fr"]
        assert cfg.mt_engine == "google"
        assert cfg.defect_min_score == 60.0


class TestLoadConfig:
    """Test load_config with various file scenarios."""

    def test_load_from_explicit_path(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".polydrive.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "default_source_lang": "ja",
                    "default_target_langs": ["en", "ko"],
                    "defect_min_score": 55.0,
                }
            ),
            encoding="utf-8",
        )

        cfg = load_config(config_file)
        assert cfg.default_source_lang == "ja"
        assert cfg.default_target_langs == ["en", "ko"]
        assert cfg.defect_min_score == 55.0
        # Unset fields keep defaults
        assert cfg.mt_engine == "libretranslate"

    def test_load_empty_yaml_file(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".polydrive.yaml"
        config_file.write_text("", encoding="utf-8")

        cfg = load_config(config_file)
        assert cfg == PolyDriveConfig()

    def test_missing_config_file_falls_back_to_defaults(self, tmp_path: Path) -> None:
        nonexistent = tmp_path / "does_not_exist.yaml"
        cfg = load_config(nonexistent)
        assert cfg == PolyDriveConfig()

    def test_load_partial_config_keeps_defaults(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".polydrive.yaml"
        config_file.write_text(
            yaml.dump({"mt_engine": "deepl", "output_format": "json"}),
            encoding="utf-8",
        )

        cfg = load_config(config_file)
        assert cfg.mt_engine == "deepl"
        assert cfg.output_format == "json"
        assert cfg.default_source_lang == "en"  # default preserved


class TestSaveConfig:
    """Test save_config and save/load roundtrip."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        cfg = PolyDriveConfig()
        dest = tmp_path / "output.yaml"
        save_config(cfg, dest)
        assert dest.exists()

    def test_roundtrip(self, tmp_path: Path) -> None:
        original = PolyDriveConfig(
            default_source_lang="fr",
            default_target_langs=["en", "es", "it"],
            glossary_path="/path/to/glossary.tbx",
            mt_engine="deepl",
            mt_engines_config={
                "deepl": {"api_key": "key123", "endpoint": "https://api.deepl.com"}
            },
            encoding_require_utf8=True,
            encoding_fail_on_bom=True,
            encoding_exclude=["*.bin", "*.exe"],
            defect_min_score=65.5,
            terminology_min_frequency=5,
            trace_similarity_threshold=0.85,
            output_format="json",
        )

        dest = tmp_path / "roundtrip.yaml"
        save_config(original, dest)
        loaded = load_config(dest)

        assert loaded == original

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        cfg = PolyDriveConfig()
        dest = tmp_path / "nested" / "dir" / "config.yaml"
        save_config(cfg, dest)
        assert dest.exists()

    def test_saved_file_is_valid_yaml(self, tmp_path: Path) -> None:
        cfg = PolyDriveConfig(mt_engine="google", output_format="json")
        dest = tmp_path / "check.yaml"
        save_config(cfg, dest)

        with dest.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert isinstance(data, dict)
        assert data["mt_engine"] == "google"
        assert data["output_format"] == "json"
