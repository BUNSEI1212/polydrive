"""CSV adapter for importing glossary terminology."""

from __future__ import annotations

import csv
from pathlib import Path

from polydrive.core.models import Glossary
from polydrive.core.models import LocalizedTerm
from polydrive.core.models import TermCategory
from polydrive.core.models import TermEntry


def import_csv(file_path: Path, domain: str = "automotive") -> Glossary:
    """Import a CSV file into a Glossary model.

    Expected columns: id, source_term, source_lang, target_term, target_lang,
    category, definition, note
    """
    entries_map: dict[str, TermEntry] = {}

    with open(file_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry_id = row.get("id", "").strip()
            if not entry_id:
                continue

            src_lang = row.get("source_lang", "en").strip()
            src_term = row.get("source_term", "").strip()
            tgt_lang = row.get("target_lang", "").strip()
            tgt_term = row.get("target_term", "").strip()
            category_raw = row.get("category", "general").strip()
            definition = row.get("definition", "").strip() or None
            note = row.get("note", "").strip() or None

            try:
                category = TermCategory(category_raw)
            except ValueError:
                category = TermCategory.GENERAL

            translations: list[LocalizedTerm] = []
            if src_term:
                translations.append(
                    LocalizedTerm(
                        lang=src_lang,
                        term=src_term,
                        definition=definition,
                    )
                )
            if tgt_term and tgt_lang:
                translations.append(
                    LocalizedTerm(
                        lang=tgt_lang,
                        term=tgt_term,
                    )
                )

            if entry_id in entries_map:
                existing = entries_map[entry_id]
                for t in translations:
                    if t not in existing.translations:
                        existing.translations.append(t)
            else:
                entries_map[entry_id] = TermEntry(
                    id=entry_id,
                    category=category,
                    note=note,
                    translations=translations,
                )

    return Glossary(
        id=file_path.stem,
        title=file_path.stem,
        domain=domain,
        entries=list(entries_map.values()),
    )
