#!/usr/bin/env python3
"""Write the immutable Run 031 geometry/selection runner audit."""

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
    expected_calibration_months,
)
from shockbridge_state_risk.state.stage_a_calibration import (  # noqa: E402
    B3_LAMBDA_MULTIPLIERS,
    threshold_grid,
)

APPROVAL = ROOT / "research/methodology/run_031_stage_A_empirical_runner_approval_v1.yaml"
CALIBRATION = SRC / "shockbridge_state_risk/state/stage_a_calibration.py"
GEOMETRY = SRC / "shockbridge_state_risk/state/stage_a_geometry.py"
CALIBRATION_TESTS = ROOT / "tests/test_stage_a_calibration.py"
GEOMETRY_TESTS = ROOT / "tests/test_stage_a_geometry.py"
OUTPUT = ROOT / "reports/methodology/run_031_stage_A_runner_validation.audit.json"


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


def test_method_count(path: Path) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
        for node in ast.walk(tree)
    )


def main() -> int:
    imports = tuple(sorted(set(imported_modules(CALIBRATION) + imported_modules(GEOMETRY))))
    prohibited = tuple(
        name
        for name in imports
        if "transmission" in name or "outcome" in name or ".evaluation" in name
    )
    candidate_count = len(threshold_grid())
    calibration_origins = len(expected_calibration_months())
    hostile_tests = test_method_count(CALIBRATION_TESTS) + test_method_count(GEOMETRY_TESTS)
    passed = (
        candidate_count == 144
        and calibration_origins == 60
        and B3_LAMBDA_MULTIPLIERS == (0.5, 1.0, 2.0)
        and hostile_tests == 10
        and not prohibited
    )
    payload = {
        "audit_id": "run-031-stage-A-runner-validation-v1",
        "status": "STAGE_A_TRANSACTION_AND_GEOMETRY_GATE_PASSED"
        if passed
        else "STAGE_A_TRANSACTION_AND_GEOMETRY_GATE_FAILED",
        "approval_sha256": sha256(APPROVAL),
        "calibration_module_sha256": sha256(CALIBRATION),
        "geometry_module_sha256": sha256(GEOMETRY),
        "calibration_tests_sha256": sha256(CALIBRATION_TESTS),
        "geometry_tests_sha256": sha256(GEOMETRY_TESTS),
        "candidate_grid_count": candidate_count,
        "calibration_origin_count": calibration_origins,
        "B3_lambda_multipliers": B3_LAMBDA_MULTIPLIERS,
        "focused_test_methods": hostile_tests,
        "imports": imports,
        "prohibited_imports": prohibited,
        "official_panel_loaded_into_estimator": False,
        "calibration_fit_performed": False,
        "evaluation_metric_or_label_accessed": False,
        "transmission_outcomes_accessed": False,
        "software_fixture_values_used_for_tests_only": True,
        "remaining_gate": (
            "Implement and hostile-test the hash-bound origin-by-scenario panel generator "
            "before supplying official geometry to this transaction."
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
