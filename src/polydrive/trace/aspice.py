"""ASPICE process evidence collector."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ASPICEEvidence:
    process_id: str  # e.g. "SWE.1", "SWE.6", "MAN.6"
    process_name: str
    evidence_type: str  # artifact, metric, process
    description: str
    file_path: Path | None = None
    status: str = "found"  # found, missing, partial


# Patterns that indicate ASPICE process evidence
_FILE_PATTERNS: list[tuple[str, list[str]]] = [
    (
        "SWE.1",
        [
            r"(?i)requirement",
            r"(?i)spec",
            r"(?i)\.req$",
        ],
    ),
    (
        "SWE.4",
        [
            r"(?i)test[_\-]?spec",
            r"(?i)test[_\-]?plan",
        ],
    ),
    (
        "SWE.5",
        [
            r"(?i)test[_\-]?result",
            r"(?i)test[_\-]?report",
        ],
    ),
    (
        "SWE.6",
        [
            r"(?i)\.feature$",
            r"(?i)gherkin",
            r"(?i)acceptance[_\-]?test",
        ],
    ),
    (
        "SUP.9",
        [
            r"(?i)qa[_\-]?report",
            r"(?i)quality[_\-]?review",
        ],
    ),
    (
        "MAN.6",
        [
            r"(?i)metric",
            r"(?i)dashboard",
            r"(?i)kpi",
        ],
    ),
]

# Terminology / localization file extensions
_TERMINOLOGY_EXTS = {".tbx", ".tmx", ".xliff"}

# CI config paths
_CI_CONFIGS = [
    Path(".github") / "workflows",
    Path(".gitlab-ci.yml"),
    Path("Jenkinsfile"),
]

_PROCESS_NAMES: dict[str, str] = {
    "SWE.1": "Software Requirements Analysis",
    "SWE.4": "Software Qualification Test",
    "SWE.5": "Software Integration Test",
    "SWE.6": "Software Verification",
    "SUP.9": "Problem Resolution Management",
    "MAN.6": "Process Improvement",
}


def collect_aspice_evidence(project_dir: Path) -> list[ASPICEEvidence]:
    """Scan project directory for ASPICE language-related evidence."""
    evidence: list[ASPICEEvidence] = []

    if not project_dir.is_dir():
        return evidence

    # Gather all files (non-hidden, non-node_modules etc.)
    all_files: list[Path] = []
    skip_dirs = {
        ".git",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }
    for fp in project_dir.rglob("*"):
        if any(part in skip_dirs for part in fp.relative_to(project_dir).parts):
            continue
        if fp.is_file():
            all_files.append(fp)

    # Check file-based evidence per process
    found_processes: dict[str, list[Path]] = {}
    for process_id, patterns in _FILE_PATTERNS:
        for fp in all_files:
            rel = str(fp.relative_to(project_dir))
            for pat in patterns:
                if re.search(pat, rel):
                    found_processes.setdefault(process_id, []).append(fp)
                    break

    for process_id, files in found_processes.items():
        evidence.append(
            ASPICEEvidence(
                process_id=process_id,
                process_name=_PROCESS_NAMES.get(process_id, process_id),
                evidence_type="artifact",
                description=f"Found {len(files)} matching file(s)",
                file_path=files[0],
                status="found",
            )
        )

    # Mark missing processes
    for process_id, _patterns in _FILE_PATTERNS:
        if process_id not in found_processes:
            evidence.append(
                ASPICEEvidence(
                    process_id=process_id,
                    process_name=_PROCESS_NAMES.get(process_id, process_id),
                    evidence_type="artifact",
                    description="No matching files found",
                    status="missing",
                )
            )

    # Check for terminology management files (TBX, TMX, XLIFF)
    term_files = [fp for fp in all_files if fp.suffix in _TERMINOLOGY_EXTS]
    if term_files:
        evidence.append(
            ASPICEEvidence(
                process_id="SWE.1",
                process_name=_PROCESS_NAMES.get("SWE.1", "SWE.1"),
                evidence_type="artifact",
                description=f"Terminology management file(s) found: {len(term_files)}",
                file_path=term_files[0],
                status="found",
            )
        )

    # Check for Gherkin feature files
    feature_files = [fp for fp in all_files if fp.suffix == ".feature"]
    if feature_files:
        evidence.append(
            ASPICEEvidence(
                process_id="SWE.6",
                process_name=_PROCESS_NAMES.get("SWE.6", "SWE.6"),
                evidence_type="artifact",
                description=f"BDD feature file(s) found: {len(feature_files)}",
                file_path=feature_files[0],
                status="found",
            )
        )

    # Check for PolyDrive config
    polydrive_yaml = project_dir / "polydrive.yaml"
    polydrive_dir = project_dir / ".polydrive"
    if polydrive_yaml.exists() or polydrive_dir.is_dir():
        evidence.append(
            ASPICEEvidence(
                process_id="MAN.6",
                process_name=_PROCESS_NAMES.get("MAN.6", "MAN.6"),
                evidence_type="process",
                description="PolyDrive configuration found — indicates language governance process",
                file_path=polydrive_yaml if polydrive_yaml.exists() else None,
                status="found",
            )
        )

    # Check for CI configuration with polydrive commands
    for ci_path in _CI_CONFIGS:
        full = project_dir / ci_path
        if full.is_dir():
            for ci_file in full.rglob("*"):
                if ci_file.is_file():
                    try:
                        text = ci_file.read_text(encoding="utf-8", errors="ignore")
                        if "polydrive" in text.lower():
                            evidence.append(
                                ASPICEEvidence(
                                    process_id="MAN.6",
                                    process_name=_PROCESS_NAMES.get("MAN.6", "MAN.6"),
                                    evidence_type="process",
                                    description="CI pipeline includes polydrive commands",
                                    file_path=ci_file,
                                    status="found",
                                )
                            )
                    except OSError:
                        pass
        elif full.is_file():
            try:
                text = full.read_text(encoding="utf-8", errors="ignore")
                if "polydrive" in text.lower():
                    evidence.append(
                        ASPICEEvidence(
                            process_id="MAN.6",
                            process_name=_PROCESS_NAMES.get("MAN.6", "MAN.6"),
                            evidence_type="process",
                            description="CI pipeline includes polydrive commands",
                            file_path=full,
                            status="found",
                        )
                    )
            except OSError:
                pass

    # Check for glossary/terminology files
    glossary_files = [
        fp
        for fp in all_files
        if fp.suffix in (".tbx", ".csv")
        and re.search(r"(?i)glossary|terminology|term", str(fp))
    ]
    if glossary_files:
        evidence.append(
            ASPICEEvidence(
                process_id="SWE.1",
                process_name=_PROCESS_NAMES.get("SWE.1", "SWE.1"),
                evidence_type="artifact",
                description=f"Glossary/terminology file(s) found: {len(glossary_files)}",
                file_path=glossary_files[0],
                status="found",
            )
        )

    return evidence
