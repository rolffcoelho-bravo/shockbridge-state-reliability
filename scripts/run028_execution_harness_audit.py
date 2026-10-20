#!/usr/bin/env python3
"""Write the value-free Run 028 execution-harness implementation audit."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from shockbridge_state_risk.state.reliability_execution_harness import (  # noqa: E402
    implementation_surface,
    validate_approved_amendment,
)

PROPOSAL = ROOT / "research/methodology/run_027_reliability_execution_amendment_proposal_v1.yaml"
APPROVAL = ROOT / "research/methodology/run_028_reliability_execution_amendment_approval_v1.yaml"
RUN026 = (
    ROOT / "research/methodology/run_026_information_clock_reliability_execution_protocol_v1.yaml"
)
HARNESS = SRC / "shockbridge_state_risk/state/reliability_execution_harness.py"
TESTS = ROOT / "tests/test_reliability_execution_harness.py"
OUTPUT = ROOT / "reports/methodology/run_028_execution_harness_validation.audit.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def imported_modules(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return tuple(sorted(names))


def main() -> int:
    amendment_hash = validate_approved_amendment(APPROVAL, PROPOSAL)
    imports = imported_modules(HARNESS)
    outcome_imports = tuple(value for value in imports if "transmission" in value)
    surface = implementation_surface()
    gap_ids = tuple(sorted(key for key in surface if key.startswith("XG-")))
    expected = tuple(f"XG-{index:02d}" for index in range(1, 12))
    passed = (
        amendment_hash == sha256(PROPOSAL)
        and gap_ids == expected
        and not outcome_imports
        and surface["official_values_accessed"] is False
        and surface["evaluation_results_accessed"] is False
        and surface["outcome_modules_imported"] is False
    )
    payload = {
        "audit_id": "run-028-execution-harness-validation-v1",
        "status": "IMPLEMENTATION_GATE_PASSED" if passed else "IMPLEMENTATION_GATE_FAILED",
        "approved_amendment_sha256": amendment_hash,
        "approval_sha256": sha256(APPROVAL),
        "unchanged_run026_protocol_sha256": sha256(RUN026),
        "harness_sha256": sha256(HARNESS),
        "hostile_tests_sha256": sha256(TESTS),
        "implemented_gap_ids": gap_ids,
        "implementation_surface": surface,
        "imported_modules": imports,
        "prohibited_outcome_imports": outcome_imports,
        "official_values_accessed": False,
        "calibration_fit_performed": False,
        "evaluation_results_accessed": False,
        "transmission_outcomes_accessed": False,
        "synthetic_empirical_observations_used": False,
        "software_fixture_tests_expected": 15,
        "passed": passed,
    }
    if OUTPUT.exists():
        raise SystemExit(f"refusing to overwrite immutable audit: {OUTPUT}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{OUTPUT.name}.", dir=OUTPUT.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, OUTPUT)
    finally:
        temporary.unlink(missing_ok=True)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
