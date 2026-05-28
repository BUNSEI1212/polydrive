"""Gherkin multi-language synchronization checker."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GherkinScenario:
    name: str
    steps: list[str]
    tags: list[str] = field(default_factory=list)


@dataclass
class GherkinFeature:
    language: str  # BCP 47
    file_path: Path
    name: str
    scenarios: list[GherkinScenario]


@dataclass
class SyncIssue:
    severity: str  # error, warning, info
    issue_type: str  # missing_scenario, extra_step, different_tag, etc.
    base_scenario: str
    compare_scenario: str | None
    compare_lang: str
    details: str


def parse_feature(file_path: Path) -> GherkinFeature:
    """Parse a Gherkin .feature file.

    Handles ``# language:`` header, Feature/Scenario/Background blocks,
    Given/When/Then/And/But steps, @tags, comments, and Examples tables.
    """
    text = file_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    language = "en"
    feature_name = ""
    scenarios: list[GherkinScenario] = []
    current_tags: list[str] = []
    current_scenario: GherkinScenario | None = None
    in_examples = False

    for raw_line in lines:
        line = raw_line.strip()

        # language header
        lang_match = re.match(r"^#\s*language:\s*(\S+)", line)
        if lang_match:
            language = lang_match.group(1)
            continue

        # skip blank lines and pure comments
        if not line or line.startswith("#"):
            continue

        # tag lines
        tag_match = re.match(r"^(@[\w,@\-\.]+\s*)+$", line)
        if tag_match:
            current_tags = [t.strip() for t in line.split() if t.startswith("@")]
            continue

        # Feature line
        feat_match = re.match(r"^(?:功能|機能|フィーチャ|Feature)\s*:\s*(.+)", line)
        if feat_match:
            feature_name = feat_match.group(1).strip()
            current_tags = []
            continue

        # Scenario / Scenario Outline
        scen_match = re.match(
            r"^(?:场景|場景|シナリオ|Scenario(?:\s+Outline)?)\s*:\s*(.+)", line
        )
        if scen_match:
            if current_scenario is not None:
                scenarios.append(current_scenario)
            current_scenario = GherkinScenario(
                name=scen_match.group(1).strip(),
                steps=[],
                tags=list(current_tags),
            )
            current_tags = []
            in_examples = False
            continue

        # Background — treat as a named scenario for sync purposes
        bg_match = re.match(r"^(?:背景|Background)\s*:\s*", line)
        if bg_match:
            if current_scenario is not None:
                scenarios.append(current_scenario)
            current_scenario = GherkinScenario(
                name="Background",
                steps=[],
                tags=list(current_tags),
            )
            current_tags = []
            in_examples = False
            continue

        # Examples table header — skip until next blank line
        if re.match(r"^(?:例子|数据表格|Examples?)\s*:", line):
            in_examples = True
            continue

        # Examples table data rows
        if in_examples:
            if line.startswith("|"):
                continue
            in_examples = False

        # Steps
        step_match = re.match(
            r"^(?:假设|假如|前提|前提条件|如果|当|那么|那么就|而且|并且|同时|但是|"
            r"Given|When|Then|And|But|"
            r"ならば|もし|かつ|しかし|前提)\s+(.+)",
            line,
        )
        if step_match and current_scenario is not None:
            current_scenario.steps.append(line)

    # flush last scenario
    if current_scenario is not None:
        scenarios.append(current_scenario)

    return GherkinFeature(
        language=language,
        file_path=file_path,
        name=feature_name,
        scenarios=scenarios,
    )


def _find_matching_files(
    base_dir: Path, base_lang: str, compare_langs: list[str]
) -> dict[str, dict[str, Path]]:
    """Find feature files matching by name pattern or directory structure.

    Returns ``{feature_name: {lang: path}}``.
    """
    features: dict[str, dict[str, Path]] = {}

    # Strategy 1: suffix-based naming — login.feature, login_zh.feature
    all_feature_files = sorted(base_dir.rglob("*.feature"))
    for fp in all_feature_files:
        stem = fp.stem
        # Check for _lang suffix
        for lang in [base_lang, *compare_langs]:
            suffix = f"_{lang}"
            if stem.endswith(suffix):
                base_name = stem[: -len(suffix)]
                features.setdefault(base_name, {})[lang] = fp
                break
        else:
            # No suffix — treat as base language
            features.setdefault(stem, {})[base_lang] = fp

    # Strategy 2: directory-based — en/login.feature, zh/login.feature
    dir_based: dict[str, dict[str, Path]] = {}
    for fp in all_feature_files:
        # Check if parent directory name looks like a language tag
        parent = fp.parent.name
        if parent in [base_lang, *compare_langs]:
            dir_based.setdefault(fp.stem, {})[parent] = fp

    # Merge: prefer suffix-based, fill gaps with directory-based
    for name, lang_map in dir_based.items():
        merged = features.setdefault(name, {})
        for lang, path in lang_map.items():
            if lang not in merged:
                merged[lang] = path

    return features


def sync_features(
    base_dir: Path,
    base_lang: str,
    compare_langs: list[str],
) -> list[SyncIssue]:
    """Compare feature files across languages and report inconsistencies."""
    file_map = _find_matching_files(base_dir, base_lang, compare_langs)
    issues: list[SyncIssue] = []

    for _feature_name, lang_paths in file_map.items():
        base_path = lang_paths.get(base_lang)
        if base_path is None:
            continue

        base_feature = parse_feature(base_path)
        base_scenarios = {s.name: s for s in base_feature.scenarios}

        for compare_lang in compare_langs:
            compare_path = lang_paths.get(compare_lang)
            if compare_path is None:
                for sname in base_scenarios:
                    issues.append(
                        SyncIssue(
                            severity="error",
                            issue_type="missing_file",
                            base_scenario=sname,
                            compare_scenario=None,
                            compare_lang=compare_lang,
                            details=f"No feature file found for language '{compare_lang}'",
                        )
                    )
                continue

            compare_feature = parse_feature(compare_path)
            compare_scenarios = {s.name: s for s in compare_feature.scenarios}

            # Missing scenarios in compare
            for sname in base_scenarios:
                if sname not in compare_scenarios:
                    issues.append(
                        SyncIssue(
                            severity="error",
                            issue_type="missing_scenario",
                            base_scenario=sname,
                            compare_scenario=None,
                            compare_lang=compare_lang,
                            details=f"Scenario '{sname}' missing in {compare_lang}",
                        )
                    )

            # Extra scenarios in compare (not in base)
            for sname in compare_scenarios:
                if sname not in base_scenarios:
                    issues.append(
                        SyncIssue(
                            severity="warning",
                            issue_type="extra_scenario",
                            base_scenario=sname,
                            compare_scenario=sname,
                            compare_lang=compare_lang,
                            details=f"Scenario '{sname}' exists in {compare_lang} but not in base",
                        )
                    )

            # Step count and tag mismatch for matching scenarios
            for sname, base_sc in base_scenarios.items():
                comp_sc = compare_scenarios.get(sname)
                if comp_sc is None:
                    continue

                if len(base_sc.steps) != len(comp_sc.steps):
                    issues.append(
                        SyncIssue(
                            severity="warning",
                            issue_type="step_count_mismatch",
                            base_scenario=sname,
                            compare_scenario=sname,
                            compare_lang=compare_lang,
                            details=(
                                f"Step count mismatch: base has {len(base_sc.steps)}, "
                                f"{compare_lang} has {len(comp_sc.steps)}"
                            ),
                        )
                    )

                base_tags = set(base_sc.tags)
                comp_tags = set(comp_sc.tags)
                if base_tags != comp_tags:
                    missing = base_tags - comp_tags
                    extra = comp_tags - base_tags
                    parts: list[str] = []
                    if missing:
                        parts.append(f"missing tags: {sorted(missing)}")
                    if extra:
                        parts.append(f"extra tags: {sorted(extra)}")
                    issues.append(
                        SyncIssue(
                            severity="info",
                            issue_type="different_tag",
                            base_scenario=sname,
                            compare_scenario=sname,
                            compare_lang=compare_lang,
                            details=f"Tag difference: {'; '.join(parts)}",
                        )
                    )

    return issues
