"""YAML-based defect report template validation."""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from polydrive.core.models import DefectReport


class FieldRule(BaseModel):
    """Validation rule for a defect report field."""

    min_length: int = 0
    max_length: int = 10000
    pattern: str | None = None
    allowed_values: list[str] | None = None


class DefectTemplate(BaseModel):
    """YAML-defined defect report template."""

    name: str
    required_fields: list[str]
    field_rules: dict[str, FieldRule] = {}


def load_template(path: Path) -> DefectTemplate:
    """Load a defect template from a YAML file."""
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    return DefectTemplate.model_validate(data)


def validate_report(report: DefectReport, template: DefectTemplate) -> list[str]:
    """Validate a defect report against a template. Returns a list of violation messages."""
    violations: list[str] = []

    for field_name in template.required_fields:
        value = getattr(report, field_name, None)
        if value is None or value == "" or value == []:
            violations.append(f"Missing required field: {field_name}")
            continue

        rule = template.field_rules.get(field_name)
        if rule is None:
            continue

        # Get string value for length checks
        if isinstance(value, str):
            str_val = value
        elif isinstance(value, list):
            str_val = " ".join(str(v) for v in value)
        elif isinstance(value, dict):
            str_val = " ".join(f"{k}:{v}" for k, v in value.items())
        else:
            str_val = str(value)

        if len(str_val) < rule.min_length:
            violations.append(
                f"Field '{field_name}' too short: {len(str_val)} < {rule.min_length}"
            )
        if len(str_val) > rule.max_length:
            violations.append(
                f"Field '{field_name}' too long: {len(str_val)} > {rule.max_length}"
            )
        if rule.pattern and isinstance(value, str):
            if not re.search(rule.pattern, value):
                violations.append(
                    f"Field '{field_name}' does not match pattern: {rule.pattern}"
                )
        if rule.allowed_values and isinstance(value, str):
            if value.lower() not in [v.lower() for v in rule.allowed_values]:
                violations.append(
                    f"Field '{field_name}' value '{value}' not in allowed values: {rule.allowed_values}"
                )

    return violations
