"""Encoding checker for PolyDrive i18n_guard."""

from __future__ import annotations

from pathlib import Path

from charset_normalizer import from_bytes

from polydrive.core.models import EncodingIssue

# Directories to skip during recursive walks
_SKIP_DIRS = frozenset({".git", "__pycache__", "node_modules", ".venv", "venv"})

# Binary detection threshold (bytes to read)
_PEEK_SIZE = 8192


def _is_binary(path: Path) -> bool:
    """Return True if the file appears to be binary (contains NUL byte)."""
    try:
        chunk = path.read_bytes()[:_PEEK_SIZE]
    except (OSError, PermissionError):
        return True
    return b"\x00" in chunk


def _has_bom(raw: bytes) -> bool:
    """Check for common BOM signatures."""
    return (
        raw.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
        or raw.startswith(b"\xff\xfe")  # UTF-16 LE
        or raw.startswith(b"\xfe\xff")  # UTF-16 BE
        or raw.startswith(b"\xff\xfe\x00\x00")  # UTF-32 LE
        or raw.startswith(b"\x00\x00\xfe\xff")  # UTF-32 BE
    )


def check_encoding(
    path: Path,
    require_utf8: bool = False,
    fail_on_bom: bool = False,
) -> list[EncodingIssue]:
    """Check file(s) for encoding issues.

    Args:
        path: File or directory to check.
        require_utf8: Report non-UTF-8 files as issues.
        fail_on_bom: Report files with BOM as issues.

    Returns:
        List of EncodingIssue objects found.
    """
    issues: list[EncodingIssue] = []

    if path.is_file():
        _check_single_file(path, require_utf8, fail_on_bom, issues)
    elif path.is_dir():
        for root, dirs, files in path.walk():  # type: ignore[attr-defined]
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
            for fname in files:
                filepath = root / fname
                _check_single_file(filepath, require_utf8, fail_on_bom, issues)
    else:
        issues.append(
            EncodingIssue(
                file_path=path,
                issue_type="invalid_chars",
                details=f"Path does not exist: {path}",
            )
        )

    return issues


def _check_single_file(
    filepath: Path,
    require_utf8: bool,
    fail_on_bom: bool,
    issues: list[EncodingIssue],
) -> None:
    """Check a single file for encoding issues."""
    if _is_binary(filepath):
        return

    try:
        raw = filepath.read_bytes()
    except (OSError, PermissionError) as exc:
        issues.append(
            EncodingIssue(
                file_path=filepath,
                issue_type="invalid_chars",
                details=f"Cannot read file: {exc}",
            )
        )
        return

    # Empty file - skip
    if not raw:
        return

    # BOM check
    if fail_on_bom and _has_bom(raw):
        issues.append(
            EncodingIssue(
                file_path=filepath,
                issue_type="has_bom",
                detected_encoding="utf-8-sig",
                details="File contains a Byte Order Mark (BOM)",
            )
        )

    # Detect encoding using charset-normalizer
    result = from_bytes(raw)
    best = result.best()

    if best is None:
        # Could not detect encoding — likely binary or corrupted
        if require_utf8:
            issues.append(
                EncodingIssue(
                    file_path=filepath,
                    issue_type="non_utf8",
                    details="Unable to detect file encoding",
                )
            )
        return

    detected = best.encoding  # e.g. "utf_8", "gb2312", "iso-8859-1"
    # Normalise the name for comparison
    norm = detected.lower().replace("-", "_").replace(" ", "")

    # ASCII is a valid subset of UTF-8
    if require_utf8 and norm not in ("utf_8", "utf8", "ascii"):
        issues.append(
            EncodingIssue(
                file_path=filepath,
                issue_type="non_utf8",
                detected_encoding=detected,
                details=f"File is {detected}, expected UTF-8",
            )
        )

    # Check for invalid UTF-8 sequences (only when the file claims to be UTF-8)
    if norm in ("utf_8", "utf8"):
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            issues.append(
                EncodingIssue(
                    file_path=filepath,
                    line=exc.start,
                    issue_type="invalid_chars",
                    detected_encoding="utf-8",
                    details=f"Invalid UTF-8 sequence at byte {exc.start}: {exc}",
                )
            )
