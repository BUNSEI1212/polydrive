"""Glossary module — TBX and CSV terminology management."""

from __future__ import annotations

from polydrive.glossary.csv_adapter import import_csv
from polydrive.glossary.tbx_parser import parse_tbx
from polydrive.glossary.tbx_parser import write_tbx

__all__ = ["import_csv", "parse_tbx", "write_tbx"]
