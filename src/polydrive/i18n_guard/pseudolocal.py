"""Pseudo-localization generator for i18n testing."""

from __future__ import annotations

import json
from pathlib import Path

from lxml import etree

# RTL markers
_RLM = "‫"  # Right-to-Left Mark
_PDF = "‬"  # Pop Directional Formatting

# Character mapping for CJK visual substitution
_CJK_MAP = {
    "A": "乃",
    "B": "刀",
    "C": "可",
    "D": "丁",
    "E": "叮",
    "F": "叭",
    "G": "咔",
    "H": "周",
    "I": "口",
    "J": "己",
    "K": "叽",
    "L": "叩",
    "M": "山",
    "N": "巴",
    "O": "口",
    "P": "巳",
    "Q": "句",
    "R": "尺",
    "S": "双",
    "T": "七",
    "U": "凵",
    "V": "丟",
    "W": "穴",
    "X": "义",
    "Y": "丁",
    "Z": "九",
    "a": "丨",
    "b": "丿",
    "c": "尸",
    "d": "己",
    "e": "工",
    "f": "干",
    "g": "夕",
    "h": "千",
    "i": "口",
    "j": "小",
    "k": "力",
    "l": "叩",
    "m": "山",
    "n": "巴",
    "o": "口",
    "p": "巳",
    "q": "句",
    "r": "尺",
    "s": "双",
    "t": "七",
    "u": "凵",
    "v": "丟",
    "w": "穴",
    "x": "义",
    "y": "丁",
    "z": "九",
}


def _expand_text(text: str) -> str:
    """Expand text by ~40% using bracket wrapping and filler.

    Example: "Hello" -> "[Ĥêļļõ ----]"
    """
    # Basic diacritic mapping for visual pseudo-localization
    accents = {
        "a": "ä",
        "e": "ê",
        "i": "ï",
        "o": "õ",
        "u": "û",
        "n": "ñ",
        "A": "Ä",
        "E": "Ê",
        "I": "Ï",
        "O": "Õ",
        "U": "Û",
        "N": "Ñ",
    }
    expanded = "".join(accents.get(ch, ch) for ch in text)
    # Add ~40% filler
    extra = max(1, len(text) * 2 // 5)
    filler = " " + "-" * extra
    return f"[{expanded}{filler}]"


def _cjk_text(text: str) -> str:
    """Replace Latin characters with CJK lookalikes."""
    return "".join(_CJK_MAP.get(ch, ch) for ch in text)


def _rtl_wrap(text: str) -> str:
    """Wrap text with RTL markers."""
    return f"{_RLM}{text}{_PDF}"


def _transform_value(value: str, modes: list[str]) -> str:
    """Apply pseudo-localization transforms to a string value."""
    result = value
    for mode in modes:
        if mode == "expand":
            result = _expand_text(result)
        elif mode == "cjk":
            result = _cjk_text(result)
        elif mode == "rtl":
            result = _rtl_wrap(result)
    return result


def _transform_dict(data: dict, modes: list[str]) -> dict:
    """Recursively transform all string values in a dict."""
    result: dict = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = _transform_value(value, modes)
        elif isinstance(value, dict):
            result[key] = _transform_dict(value, modes)
        elif isinstance(value, list):
            result[key] = _transform_list(value, modes)
        else:
            result[key] = value
    return result


def _transform_list(data: list, modes: list[str]) -> list:
    """Recursively transform all string values in a list."""
    result: list = []
    for item in data:
        if isinstance(item, str):
            result.append(_transform_value(item, modes))
        elif isinstance(item, dict):
            result.append(_transform_dict(item, modes))
        elif isinstance(item, list):
            result.append(_transform_list(item, modes))
        else:
            result.append(item)
    return result


def _is_qt_ts(source: Path) -> bool:
    """Check if the file is a Qt .ts XML file."""
    return source.suffix.lower() == ".ts"


def _transform_qt_ts(source: Path, modes: list[str], output: Path | None) -> dict:
    """Pseudo-localize a Qt .ts XML file."""
    tree = etree.parse(str(source))
    root = tree.getroot()

    count = 0
    for message in root.iter("message"):
        source_elem = message.find("source")
        translation_elem = message.find("translation")
        if source_elem is None or translation_elem is None:
            continue
        if source_elem.text:
            translation_elem.text = _transform_value(source_elem.text, modes)
            # Remove type attribute (e.g., "unfinished")
            if "type" in translation_elem.attrib:
                del translation_elem.attrib["type"]
            count += 1

    out_path = output or source.with_suffix(".pseudo.ts")
    tree.write(
        str(out_path),
        xml_declaration=True,
        encoding="utf-8",
        pretty_print=True,
    )

    return {
        "source": str(source),
        "output": str(out_path),
        "mode": "+".join(modes),
        "strings_transformed": count,
    }


def pseudo_localize(
    source: Path,
    mode: str = "expand",
    output: Path | None = None,
) -> dict:
    """Generate pseudo-localized resources.

    Args:
        source: Source locale file (JSON or Qt .ts).
        mode: Comma or plus-separated modes: expand, cjk, rtl.
        output: Optional output file path.

    Returns:
        Dict with metadata about the transformation.
    """
    modes = [m.strip() for m in mode.replace(",", "+").split("+") if m.strip()]

    if _is_qt_ts(source):
        return _transform_qt_ts(source, modes, output)

    # JSON locale file
    data = json.loads(source.read_text(encoding="utf-8"))
    transformed = _transform_dict(data, modes)

    out_path = output or source.with_name(source.stem + ".pseudo" + source.suffix)
    out_path.write_text(
        json.dumps(transformed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Count transformed strings
    count = _count_strings(transformed) - _count_strings(data)

    return {
        "source": str(source),
        "output": str(out_path),
        "mode": "+".join(modes),
        "strings_transformed": abs(count),
    }


def _count_strings(data: dict | list) -> int:
    """Count string leaf values in a nested structure."""
    count = 0
    items = data.values() if isinstance(data, dict) else data
    for v in items:
        if isinstance(v, str):
            count += 1
        elif isinstance(v, (dict, list)):
            count += _count_strings(v)
    return count
