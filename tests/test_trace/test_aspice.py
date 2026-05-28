"""Tests for ASPICE evidence collection."""

from __future__ import annotations

from pathlib import Path

from polydrive.trace.aspice import collect_aspice_evidence

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestCollectAspiceEvidence:
    def test_finds_gherkin_feature_files(self) -> None:
        evidence = collect_aspice_evidence(FIXTURES_DIR)
        feature_evidence = [
            e
            for e in evidence
            if "BDD feature" in e.description or e.process_id == "SWE.6"
        ]
        assert len(feature_evidence) > 0

    def test_evidence_has_required_fields(self) -> None:
        evidence = collect_aspice_evidence(FIXTURES_DIR)
        for e in evidence:
            assert e.process_id
            assert e.process_name
            assert e.evidence_type in ("artifact", "metric", "process")
            assert e.status in ("found", "missing", "partial")

    def test_missing_project_returns_empty(self) -> None:
        evidence = collect_aspice_evidence(Path("/nonexistent/path"))
        assert evidence == []

    def test_terminology_files_detected(self) -> None:
        evidence = collect_aspice_evidence(FIXTURES_DIR)
        term_evidence = [
            e for e in evidence if "Terminology management" in e.description
        ]
        assert len(term_evidence) > 0

    def test_missing_processes_reported(self) -> None:
        evidence = collect_aspice_evidence(FIXTURES_DIR)
        missing = [e for e in evidence if e.status == "missing"]
        # Some processes will be missing in a small fixtures directory
        assert len(missing) > 0
        for m in missing:
            assert m.process_id.startswith(("SWE", "SUP", "MAN"))
