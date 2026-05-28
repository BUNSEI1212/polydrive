"""Tests for the pseudo-localization module."""

from __future__ import annotations

import json
from pathlib import Path

from polydrive.i18n_guard.pseudolocal import _cjk_text
from polydrive.i18n_guard.pseudolocal import _expand_text
from polydrive.i18n_guard.pseudolocal import _rtl_wrap
from polydrive.i18n_guard.pseudolocal import pseudo_localize

FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestPseudoLocalizeExpand:
    """Tests for expand mode."""

    def test_expand_basic(self) -> None:
        """Expand mode should add brackets and filler."""
        result = _expand_text("Hello")
        assert result.startswith("[")
        assert result.endswith("]")
        assert "H" in result or "Ä" in result

    def test_expand_lengthens_text(self) -> None:
        """Expand mode should produce longer output."""
        result = _expand_text("Hi")
        assert len(result) > len("Hi")

    def test_expand_json_file(self, tmp_path: Path) -> None:
        """Should pseudo-localize a JSON locale file in expand mode."""
        out = tmp_path / "pseudo.json"
        result = pseudo_localize(
            FIXTURES / "locale_en.json",
            mode="expand",
            output=out,
        )
        assert result["strings_transformed"] >= 0
        assert out.exists()

        data = json.loads(out.read_text(encoding="utf-8"))
        title = data["app"]["title"]
        assert "[" in title
        assert "]" in title


class TestPseudoLocalizeCJK:
    """Tests for CJK mode."""

    def test_cjk_basic(self) -> None:
        """CJK mode should replace Latin chars with CJK lookalikes."""
        result = _cjk_text("ABC")
        assert result != "ABC"
        assert all(ord(ch) > 0x4E00 for ch in result if ch.strip())

    def test_cjk_preserves_non_latin(self) -> None:
        """CJK mode should preserve digits and punctuation."""
        result = _cjk_text("123!@#")
        assert "123" in result
        assert "!@#" in result

    def test_cjk_json_file(self, tmp_path: Path) -> None:
        """Should pseudo-localize a JSON locale file in CJK mode."""
        out = tmp_path / "pseudo_cjk.json"
        _result = pseudo_localize(
            FIXTURES / "locale_en.json",
            mode="cjk",
            output=out,
        )
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        title = data["app"]["title"]
        # Should contain CJK characters now
        assert any(ord(ch) > 0x4E00 for ch in title)


class TestPseudoLocalizeRTL:
    """Tests for RTL mode."""

    def test_rtl_basic(self) -> None:
        """RTL mode should wrap text with RTL markers."""
        result = _rtl_wrap("Hello")
        assert result.startswith("‫")
        assert result.endswith("‬")

    def test_rtl_json_file(self, tmp_path: Path) -> None:
        """Should pseudo-localize a JSON locale file in RTL mode."""
        out = tmp_path / "pseudo_rtl.json"
        _result = pseudo_localize(
            FIXTURES / "locale_en.json",
            mode="rtl",
            output=out,
        )
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        title = data["app"]["title"]
        assert title.startswith("‫")


class TestPseudoLocalizeCombined:
    """Tests for combined modes."""

    def test_expand_plus_cjk(self, tmp_path: Path) -> None:
        """Should combine expand and CJK modes."""
        out = tmp_path / "pseudo_both.json"
        _result = pseudo_localize(
            FIXTURES / "locale_en.json",
            mode="expand+cjk",
            output=out,
        )
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        title = data["app"]["title"]
        assert "[" in title

    def test_comma_separated_modes(self, tmp_path: Path) -> None:
        """Should accept comma-separated modes."""
        out = tmp_path / "pseudo_comma.json"
        _result = pseudo_localize(
            FIXTURES / "locale_en.json",
            mode="expand,cjk",
            output=out,
        )
        assert out.exists()


class TestPseudoLocalizeQt:
    """Tests for Qt .ts file pseudo-localization."""

    def test_qt_ts_file(self, tmp_path: Path) -> None:
        """Should pseudo-localize a Qt .ts file."""
        out = tmp_path / "pseudo.ts"
        result = pseudo_localize(
            FIXTURES / "sample_qt.ts",
            mode="expand",
            output=out,
        )
        assert result["strings_transformed"] >= 1
        assert out.exists()


class TestPseudoLocalizeEdgeCases:
    """Edge case tests."""

    def test_default_output_path(self, tmp_path: Path) -> None:
        """Should generate default output path when none specified."""
        # Copy fixture to tmp_path to avoid polluting fixtures dir
        src = tmp_path / "locale.json"
        src.write_text('{"key": "value"}', encoding="utf-8")
        _result = pseudo_localize(src, mode="expand")
        expected = tmp_path / "locale.pseudo.json"
        assert expected.exists()

    def test_nested_json(self, tmp_path: Path) -> None:
        """Should handle nested JSON structures."""
        data = {"a": {"b": {"c": "deep value"}}}
        src = tmp_path / "nested.json"
        src.write_text(json.dumps(data), encoding="utf-8")
        out = tmp_path / "out.json"
        pseudo_localize(src, mode="expand", output=out)
        result = json.loads(out.read_text(encoding="utf-8"))
        assert "[" in result["a"]["b"]["c"]

    def test_preserves_non_string_values(self, tmp_path: Path) -> None:
        """Should preserve numeric and boolean values."""
        data = {"count": 42, "flag": True, "name": "test"}
        src = tmp_path / "mixed.json"
        src.write_text(json.dumps(data), encoding="utf-8")
        out = tmp_path / "out.json"
        pseudo_localize(src, mode="expand", output=out)
        result = json.loads(out.read_text(encoding="utf-8"))
        assert result["count"] == 42
        assert result["flag"] is True
        assert "[" in result["name"]
