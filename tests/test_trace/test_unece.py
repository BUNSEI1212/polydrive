"""Tests for UNECE R121 HMI compliance checker."""

from __future__ import annotations

from polydrive.trace.unece import check_unece_r121


class TestCheckUneceR121:
    def test_fully_compliant_manifest(self) -> None:
        manifest = {
            "tell_tales": [
                {"id": "brake_warning", "symbol": "ISO 7000-0239"},
                {"id": "ABS_warning", "symbol": "ISO 7000-0645"},
                {"id": "airbag_warning", "symbol": "ISO 7000-2441"},
                {"id": "seat_belt_warning", "symbol": "ISO 7000-0238"},
                {"id": "low_fuel_warning", "symbol": "ISO 7000-0245"},
                {"id": "engine_warning", "symbol": "ISO 7000-0427"},
                {"id": "oil_pressure_warning", "symbol": "ISO 7000-0240"},
                {"id": "battery_warning", "symbol": "ISO 7000-0241"},
                {"id": "temperature_warning", "symbol": "ISO 7000-0246"},
                {"id": "TPMS_warning", "symbol": "ISO 7000-2580"},
            ],
        }
        issues = check_unece_r121(manifest)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_missing_required_tell_tale(self) -> None:
        manifest = {
            "tell_tales": [
                {"id": "brake_warning", "symbol": "ISO 7000-0239"},
                # Missing all other required tell-tales
            ],
        }
        issues = check_unece_r121(manifest)
        missing = [i for i in issues if i.check_type == "missing_warning"]
        assert len(missing) > 0
        missing_ids = {i.item_id for i in missing}
        assert "ABS_warning" in missing_ids
        assert "airbag_warning" in missing_ids

    def test_empty_manifest(self) -> None:
        manifest = {"tell_tales": []}
        issues = check_unece_r121(manifest)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) > 0

    def test_non_standard_tell_tale(self) -> None:
        manifest = {
            "tell_tales": [
                {"id": "brake_warning", "symbol": "ISO 7000-0239"},
                {"id": "ABS_warning", "symbol": "ISO 7000-0645"},
                {"id": "airbag_warning", "symbol": "ISO 7000-2441"},
                {"id": "seat_belt_warning", "symbol": "ISO 7000-0238"},
                {"id": "engine_warning", "symbol": "ISO 7000-0427"},
                {"id": "oil_pressure_warning", "symbol": "ISO 7000-0240"},
                {"id": "battery_warning", "symbol": "ISO 7000-0241"},
                {"id": "temperature_warning", "symbol": "ISO 7000-0246"},
                {"id": "TPMS_warning", "symbol": "ISO 7000-2580"},
                {"id": "custom_indicator", "symbol": "CUSTOM-001"},
            ],
        }
        issues = check_unece_r121(manifest)
        non_standard = [i for i in issues if i.item_id == "custom_indicator"]
        assert len(non_standard) == 1
        assert non_standard[0].severity == "warning"

    def test_missing_symbol_reference(self) -> None:
        manifest = {
            "tell_tales": [
                {"id": "brake_warning"},  # No symbol field
                {"id": "ABS_warning", "symbol": "ISO 7000-0645"},
                {"id": "airbag_warning", "symbol": "ISO 7000-2441"},
                {"id": "seat_belt_warning", "symbol": "ISO 7000-0238"},
                {"id": "engine_warning", "symbol": "ISO 7000-0427"},
                {"id": "oil_pressure_warning", "symbol": "ISO 7000-0240"},
                {"id": "battery_warning", "symbol": "ISO 7000-0241"},
                {"id": "temperature_warning", "symbol": "ISO 7000-0246"},
                {"id": "TPMS_warning", "symbol": "ISO 7000-2580"},
            ],
        }
        issues = check_unece_r121(manifest)
        missing_sym = [
            i for i in issues if i.check_type == "missing_symbol" and i.item_id == "brake_warning"
        ]
        assert len(missing_sym) == 1

    def test_optional_not_required(self) -> None:
        """low_fuel_warning is optional — missing it should not produce errors."""
        manifest = {"tell_tales": []}
        issues = check_unece_r121(manifest)
        fuel_issues = [i for i in issues if i.item_id == "low_fuel_warning"]
        assert len(fuel_issues) == 0
