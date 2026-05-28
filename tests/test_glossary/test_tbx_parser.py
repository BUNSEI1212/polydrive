"""Tests for the TBX parser."""

from __future__ import annotations

from pathlib import Path

from polydrive.core.models import TermCategory
from polydrive.glossary.tbx_parser import parse_tbx
from polydrive.glossary.tbx_parser import write_tbx

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_TBX = FIXTURES_DIR / "automotive_sample.tbx"


class TestParseTbx:
    def test_parse_sample_file(self) -> None:
        glossary = parse_tbx(SAMPLE_TBX)
        assert glossary.id == "automotive_sample"
        assert glossary.source_lang == "en"
        assert len(glossary.entries) == 6

    def test_entry_has_translations(self) -> None:
        glossary = parse_tbx(SAMPLE_TBX)
        brake = glossary.find_by_term("brake", "en")
        assert len(brake) == 1
        entry = brake[0]
        assert entry.id == "c1"

        zh = entry.get_term("zh")
        assert zh is not None
        assert zh.term == "制动器"

    def test_subject_field(self) -> None:
        glossary = parse_tbx(SAMPLE_TBX)
        brake = glossary.find_by_term("brake", "en")[0]
        assert brake.subject == "braking system"

    def test_category_parsed(self) -> None:
        glossary = parse_tbx(SAMPLE_TBX)
        brake = glossary.find_by_term("brake", "en")[0]
        assert brake.category == TermCategory.TECHNICAL

    def test_do_not_translate_category(self) -> None:
        glossary = parse_tbx(SAMPLE_TBX)
        euro_ncap = glossary.find_by_term("Euro NCAP", "en")[0]
        assert euro_ncap.category == TermCategory.DO_NOT_TRANSLATE

    def test_definition_parsed(self) -> None:
        glossary = parse_tbx(SAMPLE_TBX)
        brake = glossary.find_by_term("brake", "en")[0]
        en = brake.get_term("en")
        assert en is not None
        assert en.definition is not None
        assert "slowing" in en.definition

    def test_part_of_speech(self) -> None:
        glossary = parse_tbx(SAMPLE_TBX)
        brake = glossary.find_by_term("brake", "en")[0]
        en = brake.get_term("en")
        assert en is not None
        assert en.part_of_speech == "noun"

    def test_all_entries_have_two_languages(self) -> None:
        glossary = parse_tbx(SAMPLE_TBX)
        for entry in glossary.entries:
            assert len(entry.translations) == 2, (
                f"Entry {entry.id} should have 2 translations"
            )

    def test_missing_term_returns_none(self) -> None:
        glossary = parse_tbx(SAMPLE_TBX)
        result = glossary.find_by_term("nonexistent", "en")
        assert result == []


class TestWriteTbx:
    def test_round_trip(self, tmp_path: Path) -> None:
        original = parse_tbx(SAMPLE_TBX)
        out_path = tmp_path / "output.tbx"
        write_tbx(original, out_path)

        assert out_path.exists()
        roundtripped = parse_tbx(out_path)

        assert len(roundtripped.entries) == len(original.entries)
        for orig, rt in zip(original.entries, roundtripped.entries, strict=True):
            assert orig.id == rt.id
            assert orig.category == rt.category
            assert orig.subject == rt.subject
            assert len(orig.translations) == len(rt.translations)
            for o_t, r_t in zip(orig.translations, rt.translations, strict=True):
                assert o_t.term == r_t.term
                assert o_t.lang == r_t.lang

    def test_output_is_valid_xml(self, tmp_path: Path) -> None:
        from lxml import etree

        original = parse_tbx(SAMPLE_TBX)
        out_path = tmp_path / "output.tbx"
        write_tbx(original, out_path)

        tree = etree.parse(str(out_path))
        root = tree.getroot()
        assert root.tag.endswith("}tbx")
        concepts = root.findall(".//{urn:iso:std:iso:30042:ed-2}conceptEntry")
        assert len(concepts) == 6
