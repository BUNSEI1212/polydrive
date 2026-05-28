"""Client-side glossary enforcement for engines without server-side support."""

from __future__ import annotations

import re

from polydrive.core.models import Glossary


def enforce_glossary(
    text: str,
    glossary: Glossary,
    source_lang: str,
    target_lang: str,
) -> tuple[str, list[tuple[str, str]]]:
    """Post-process translation to enforce glossary terms.

    For each entry that has both source and target terms matching the language pair,
    replace any occurrence of the target-side translated term with the glossary-approved
    term.

    Returns:
        (enforced_text, list_of_applied_terms) where each tuple is (original, approved).
    """
    applied: list[tuple[str, str]] = []
    enforced = text

    for entry in glossary.entries:
        src_term = entry.get_term(source_lang)
        tgt_term = entry.get_term(target_lang)
        if src_term is None or tgt_term is None:
            continue

        approved = tgt_term.term
        # Case-insensitive replacement: match the approved term in the translated text
        # only when it differs from what's already there (catch variant spellings/casing).
        pattern = re.compile(re.escape(approved), re.IGNORECASE)
        if pattern.search(enforced):
            # Bind loop variable to avoid closure issue (B023).
            _approved = approved

            def _replace(match: re.Match[str], _a: str = _approved) -> str:
                if match.group(0) != _a:
                    applied.append((match.group(0), _a))
                    return _a
                return match.group(0)

            enforced = pattern.sub(_replace, enforced)

    return enforced, applied
