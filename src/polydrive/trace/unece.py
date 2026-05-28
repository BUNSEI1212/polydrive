"""UNECE R121 HMI compliance checker."""

from __future__ import annotations

from dataclasses import dataclass, field

R121_TELL_TALES: dict[str, dict[str, str | bool | None]] = {
    "brake_warning": {"symbol": "ISO 7000-0239", "text": None, "required": True},
    "ABS_warning": {"symbol": "ISO 7000-0645", "text": None, "required": True},
    "airbag_warning": {"symbol": "ISO 7000-2441", "text": None, "required": True},
    "seat_belt_warning": {"symbol": "ISO 7000-0238", "text": None, "required": True},
    "low_fuel_warning": {"symbol": "ISO 7000-0245", "text": None, "required": False},
    "engine_warning": {"symbol": "ISO 7000-0427", "text": None, "required": True},
    "oil_pressure_warning": {"symbol": "ISO 7000-0240", "text": None, "required": True},
    "battery_warning": {"symbol": "ISO 7000-0241", "text": None, "required": True},
    "temperature_warning": {"symbol": "ISO 7000-0246", "text": None, "required": True},
    "TPMS_warning": {"symbol": "ISO 7000-2580", "text": None, "required": True},
}


@dataclass
class HMIComplianceIssue:
    severity: str  # error, warning
    regulation: str  # "R121", "R125"
    check_type: str  # missing_symbol, wrong_text, missing_warning
    details: str
    item_id: str | None = None


def check_unece_r121(hmi_manifest: dict) -> list[HMIComplianceIssue]:
    """Check HMI manifest against UNECE R121 requirements.

    Parameters
    ----------
    hmi_manifest:
        A dict with keys ``tell_tales``, ``controls``, ``warnings``.
        Each tell-tale entry should have ``id`` and optionally ``symbol``.
    """
    issues: list[HMIComplianceIssue] = []
    regulation = "R121"

    tell_tales_list: list[dict] = hmi_manifest.get("tell_tales", [])
    manifest_ids: set[str] = {tt.get("id", "") for tt in tell_tales_list}

    # Check each mandatory R121 tell-tale
    for tt_id, spec in R121_TELL_TALES.items():
        required = spec.get("required", False)
        if not required:
            continue

        if tt_id not in manifest_ids:
            issues.append(
                HMIComplianceIssue(
                    severity="error",
                    regulation=regulation,
                    check_type="missing_warning",
                    details=f"Required tell-tale '{tt_id}' (symbol: {spec['symbol']}) is missing",
                    item_id=tt_id,
                )
            )
            continue

        # Find the manifest entry
        entry = next((tt for tt in tell_tales_list if tt.get("id") == tt_id), None)
        if entry is None:
            continue

        # Check symbol reference
        entry_symbol = entry.get("symbol", "")
        expected_symbol = spec.get("symbol") or ""
        if expected_symbol and entry_symbol and entry_symbol != expected_symbol:
            issues.append(
                HMIComplianceIssue(
                    severity="warning",
                    regulation=regulation,
                    check_type="wrong_text",
                    details=(
                        f"Tell-tale '{tt_id}' symbol mismatch: "
                        f"expected '{expected_symbol}', got '{entry_symbol}'"
                    ),
                    item_id=tt_id,
                )
            )
        elif not entry_symbol and expected_symbol:
            issues.append(
                HMIComplianceIssue(
                    severity="warning",
                    regulation=regulation,
                    check_type="missing_symbol",
                    details=f"Tell-tale '{tt_id}' missing symbol reference (expected '{expected_symbol}')",
                    item_id=tt_id,
                ),
            )

    # Check for non-standard tell-tales (info-level via details only)
    for entry in tell_tales_list:
        entry_id = entry.get("id", "")
        if entry_id and entry_id not in R121_TELL_TALES:
            issues.append(
                HMIComplianceIssue(
                    severity="warning",
                    regulation=regulation,
                    check_type="wrong_text",
                    details=f"Tell-tale '{entry_id}' is not a standard R121 tell-tale",
                    item_id=entry_id,
                )
            )

    return issues
