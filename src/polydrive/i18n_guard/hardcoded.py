"""Hardcoded non-ASCII string detector for C/C++ source files."""

from __future__ import annotations

import re
from pathlib import Path

from polydrive.core.models import HardcodedStringIssue

# C/C++ file extensions
_CPP_EXTENSIONS = frozenset({".c", ".cpp", ".h", ".hpp", ".cc", ".cxx", ".hxx"})

# Unicode ranges for CJK and related scripts
_CJK_RANGES = (
    ("一", "鿿"),   # CJK Unified Ideographs
    ("぀", "ゟ"),   # Hiragana
    ("゠", "ヿ"),   # Katakana
    ("가", "힯"),   # Hangul Syllables
)


def _has_cjk(text: str) -> bool:
    """Return True if text contains CJK/Hangul characters."""
    for ch in text:
        for lo, hi in _CJK_RANGES:
            if lo <= ch <= hi:
                return True
    return False


def _has_non_ascii(text: str) -> bool:
    """Return True if text contains non-ASCII characters."""
    return any(ord(ch) > 127 for ch in text)


# Regex to strip C and C++ comments from source text.
# Handles // line comments and /* block comments */.
_STRIP_COMMENTS_RE = re.compile(
    r'//.*?$ | /\* .*? \*/',
    re.MULTILINE | re.DOTALL | re.VERBOSE,
)

# Regex to match C/C++ string literals (double-quoted).
# Handles escaped quotes and other escape sequences.
_STRING_LITERAL_RE = re.compile(
    r'"((?:[^"\\]|\\.)*)"',
    re.DOTALL,
)

# Raw string literal: R"delimiter(...)delimiter"
_RAW_STRING_RE = re.compile(
    r'R"([a-zA-Z_0-9]*)\((.*?)\)\1"',
    re.DOTALL,
)


def _strip_comments(source: str) -> str:
    """Remove C/C++ comments from source text."""
    return _STRIP_COMMENTS_RE.sub("", source)


def _find_string_literals(
    source: str, original_source: str,
) -> list[tuple[int, int, str]]:
    """Find string literals and their positions.

    Returns list of (line, column, string_content).
    """
    results: list[tuple[int, int, str]] = []

    # Handle raw string literals first
    for m in _RAW_STRING_RE.finditer(source):
        content = m.group(2)
        _add_position(m.start(), original_source, content, results)

    # Handle regular string literals (skip inside raw strings)
    for m in _STRING_LITERAL_RE.finditer(source):
        content = m.group(1)
        _add_position(m.start(), original_source, content, results)

    return results


def _add_position(
    offset: int,
    original_source: str,
    content: str,
    results: list[tuple[int, int, str]],
) -> None:
    """Calculate line/column from offset and append to results."""
    line = original_source[:offset].count("\n") + 1
    last_nl = original_source.rfind("\n", 0, offset)
    col = offset - last_nl  # 1-based column
    results.append((line, col, content))


def detect_hardcoded(
    path: Path,
    language: str = "cpp",
    exclude_pattern: str | None = None,
) -> list[HardcodedStringIssue]:
    """Detect hardcoded non-ASCII strings in C/C++ source files.

    Args:
        path: File or directory to scan.
        language: Source language identifier (cpp, c, etc.).
        exclude_pattern: Optional glob pattern for files to exclude.

    Returns:
        List of HardcodedStringIssue objects found.
    """
    issues: list[HardcodedStringIssue] = []
    exclude_re = re.compile(exclude_pattern) if exclude_pattern else None

    if path.is_file():
        if path.suffix.lower() in _CPP_EXTENSIONS:
            if not exclude_re or not exclude_re.search(str(path)):
                _scan_file(path, language, issues)
    elif path.is_dir():
        for root, _dirs, files in path.walk():  # type: ignore[attr-defined]
            for fname in files:
                filepath = root / fname
                if filepath.suffix.lower() not in _CPP_EXTENSIONS:
                    continue
                if exclude_re and exclude_re.search(str(filepath)):
                    continue
                _scan_file(filepath, language, issues)

    return issues


def _scan_file(
    filepath: Path,
    language: str,
    issues: list[HardcodedStringIssue],
) -> None:
    """Scan a single source file for hardcoded strings."""
    try:
        raw = filepath.read_bytes()
    except (OSError, PermissionError):
        return

    # Try UTF-8 first, then latin-1 as fallback
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError:
        source = raw.decode("latin-1")

    original = source
    cleaned = _strip_comments(source)

    for line, col, content in _find_string_literals(cleaned, original):
        if not content:
            continue
        if _has_cjk(content) or _has_non_ascii(content):
            issues.append(
                HardcodedStringIssue(
                    file_path=filepath,
                    line=line,
                    column=col,
                    text=content,
                    language=language,
                )
            )
