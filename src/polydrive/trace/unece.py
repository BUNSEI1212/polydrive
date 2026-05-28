"""UNECE R121 HMI compliance checker."""

from __future__ import annotations

from dataclasses import dataclass

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

# Alias mapping: common variant names -> canonical R121 tell-tale IDs
_R121_ALIASES: dict[str, str] = {
    "brake_system_warning": "brake_warning",
    "brake": "brake_warning",
    "abs": "ABS_warning",
    "abs_warning": "ABS_warning",
    "airbag": "airbag_warning",
    "air_bag_warning": "airbag_warning",
    "srs_warning": "airbag_warning",
    "seatbelt_warning": "seat_belt_warning",
    "seat_belt": "seat_belt_warning",
    "oil_pressure": "oil_pressure_warning",
    "oil_warning": "oil_pressure_warning",
    "engine": "engine_warning",
    "check_engine": "engine_warning",
    "check_engine_warning": "engine_warning",
    "battery": "battery_warning",
    "battery_charging": "battery_warning",
    "charging_warning": "battery_warning",
    "temperature": "temperature_warning",
    "coolant_warning": "temperature_warning",
    "tpms": "TPMS_warning",
    "tire_pressure": "TPMS_warning",
    "tire_pressure_warning": "TPMS_warning",
    "fuel_warning": "low_fuel_warning",
    "low_fuel": "low_fuel_warning",
}


@dataclass
class HMIComplianceIssue:
    severity: str  # error, warning
    regulation: str  # "R121", "R125"
    check_type: str  # missing_symbol, wrong_text, missing_warning
    details: str
    item_id: str | None = None


def _resolve_id(raw_id: str) -> str | None:
    """Resolve a manifest tell-tale ID to a canonical R121 ID.

    Tries: exact match -> alias match -> keyword containment match.
    """
    if raw_id in R121_TELL_TALES:
        return raw_id
    lower = raw_id.lower().replace("-", "_").replace(" ", "_")
    if lower in _R121_ALIASES:
        return _R121_ALIASES[lower]
    # Keyword containment: check if any R121 key is contained in the input
    for r121_id in R121_TELL_TALES:
        core = r121_id.replace("_warning", "")
        if core in lower:
            return r121_id
    return None


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

    # Build resolved mapping: canonical R121 ID -> manifest entry
    resolved: dict[str, dict] = {}
    unresolved_ids: list[str] = []

    for entry in tell_tales_list:
        entry_id = entry.get("id", "")
        canonical = _resolve_id(entry_id)
        if canonical:
            resolved[canonical] = entry
        else:
            unresolved_ids.append(entry_id)

    # Check each mandatory R121 tell-tale
    for tt_id, spec in R121_TELL_TALES.items():
        required = spec.get("required", False)
        if not required:
            continue

        if tt_id not in resolved:
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

        entry = resolved[tt_id]

        # Check symbol reference
        entry_symbol = entry.get("symbol", "") or entry.get("symbol_ref", "")
        expected_symbol = spec.get("symbol") or ""
        if expected_symbol and entry_symbol and entry_symbol != expected_symbol:
            issues.append(
                HMIComplianceIssue(
                    severity="warning",
                    regulation=regulation,
                    check_type="wrong_text",
                    details=(
                        f"Tell-tale '{entry.get('id', tt_id)}' symbol mismatch: "
                        f"expected '{expected_symbol}', got '{entry_symbol}'"
                    ),
                    item_id=entry.get("id", tt_id),
                )
            )
        elif not entry_symbol and expected_symbol:
            issues.append(
                HMIComplianceIssue(
                    severity="warning",
                    regulation=regulation,
                    check_type="missing_symbol",
                    details=f"Tell-tale '{entry.get('id', tt_id)}' missing symbol reference (expected '{expected_symbol}')",
                    item_id=entry.get("id", tt_id),
                ),
            )

    # Warn about truly unrecognized tell-tales
    for uid in unresolved_ids:
        issues.append(
            HMIComplianceIssue(
                severity="warning",
                regulation=regulation,
                check_type="wrong_text",
                details=f"Tell-tale '{uid}' is not a standard R121 tell-tale",
                item_id=uid,
            )
        )

    return issues
