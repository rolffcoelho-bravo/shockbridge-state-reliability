#!/usr/bin/env python3
"""Write the immutable value-free Run 030 orchestration implementation audit."""

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

from shockbridge_state_risk.state.calibration_orchestration import (  # noqa: E402
    PIPELINE_OPERATIONS,
    orchestration_surface,
    validate_pipeline_trace,
    validate_run029_approval,
)

PROPOSAL = ROOT / "research/methodology/run_029_stage_A_orchestration_amendment_proposal_v1.yaml"
APPROVAL = ROOT / "research/methodology/run_030_stage_A_orchestration_amendment_approval_v1.yaml"
RUN026 = (
    ROOT / "research/methodology/run_026_information_clock_reliability_execution_protocol_v1.yaml"
)
RUN027 = ROOT / "research/methodology/run_027_reliability_execution_amendment_proposal_v1.yaml"
HARNESS = SRC / "shockbridge_state_risk/state/reliability_execution_harness.py"
ORCHESTRATOR = SRC / "shockbridge_state_risk/state/calibration_orchestration.py"
TESTS = ROOT / "tests/test_calibration_orchestration.py"
OUTPUT = ROOT / "reports/methodology/run_030_stage_A_orchestration_validation.audit.json"


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
    amendment_hash = validate_run029_approval(APPROVAL, PROPOSAL)
    validate_pipeline_trace(PIPELINE_OPERATIONS)
    imports = imported_modules(ORCHESTRATOR)
    prohibited_imports = tuple(
        value for value in imports if "transmission" in value or "outcome" in value
    )
    surface = orchestration_surface()
    gap_ids = tuple(sorted(key for key in surface if key.startswith("OG-")))
    expected = tuple(f"OG-{index:02d}" for index in range(1, 10))
    historical_harness_hash = sha256(HARNESS)
    passed = (
        amendment_hash == sha256(PROPOSAL)
        and gap_ids == expected
        and not prohibited_imports
        and historical_harness_hash
        == "ed8480fb7c42ed48d0014d1c4a779ceb4bffd594f8f023628a1ccb00c84ba378"
        and surface["official_fit_performed"] is False
        and surface["evaluation_fit_or_label_accessed"] is False
        and surface["transmission_module_imported"] is False
    )
    payload = {
        "audit_id": "run-030-stage-A-orchestration-validation-v1",
        "status": "ORCHESTRATION_IMPLEMENTATION_GATE_PASSED"
        if passed
        else "ORCHESTRATION_IMPLEMENTATION_GATE_FAILED",
        "approved_amendment_sha256": amendment_hash,
        "approval_sha256": sha256(APPROVAL),
        "unchanged_run026_protocol_sha256": sha256(RUN026),
        "unchanged_run027_amendment_sha256": sha256(RUN027),
        "unchanged_run028_harness_sha256": historical_harness_hash,
        "orchestrator_sha256": sha256(ORCHESTRATOR),
        "hostile_tests_sha256": sha256(TESTS),
        "pipeline_operations": PIPELINE_OPERATIONS,
        "implemented_gap_ids": gap_ids,
        "implementation_surface": surface,
        "imported_modules": imports,
        "prohibited_outcome_imports": prohibited_imports,
        "hostile_tests_expected": 14,
        "official_panel_loaded_into_estimator": False,
        "calibration_fit_performed": False,
        "evaluation_fit_metric_or_label_accessed": False,
        "transmission_outcomes_accessed": False,
        "synthetic_empirical_observations_used": False,
        "software_fixture_values_used_for_tests_only": True,
        "historical_anomaly_preserved": (
            "Run 028 zero-filled B3 is retained byte-for-byte; the approved Run 030 "
            "orchestrator supplies the prospective projected-missingness correction."
        ),
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
