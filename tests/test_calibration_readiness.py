import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from shockbridge_state_risk.state.calibration_readiness import (
    CalibrationReadinessError,
    audit_calibration_readiness,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = (
    ROOT / "research/methodology/run_026_information_clock_reliability_execution_protocol_v1.yaml"
)
AMENDMENT = ROOT / "research/methodology/run_027_reliability_execution_amendment_proposal_v1.yaml"
APPROVAL = ROOT / "research/methodology/run_028_reliability_execution_amendment_approval_v1.yaml"
HARNESS = ROOT / "src/shockbridge_state_risk/state/reliability_execution_harness.py"
STAGE_A = ROOT / "research/methodology/run_029_stage_A_calibration_approval_v1.yaml"
SCRIPT = ROOT / "scripts/run029_stage_A_readiness_audit.py"


def audit():
    return audit_calibration_readiness(PROTOCOL, AMENDMENT, APPROVAL, HARNESS, STAGE_A)


class CalibrationReadinessTests(unittest.TestCase):
    def test_stage_A_stops_on_six_result_and_three_auditability_gaps(self) -> None:
        result = audit()
        self.assertFalse(result.passed)
        self.assertTrue(result.stage_A_owner_approval_recorded)
        self.assertTrue(result.primitive_implementation_gate_passed)
        self.assertEqual(result.critical_result_choice_count, 6)
        self.assertEqual(result.critical_auditability_gap_count, 3)
        self.assertEqual(
            tuple(item.gap_id for item in result.gaps),
            tuple(f"OG-{index:02d}" for index in range(1, 10)),
        )

    def test_audit_is_value_free_and_reproducible(self) -> None:
        first = audit()
        second = audit()
        self.assertEqual(first, second)
        self.assertFalse(first.official_panel_value_loaded_into_estimator)
        self.assertFalse(first.calibration_fit_performed)
        self.assertFalse(first.evaluation_results_accessed)
        self.assertFalse(first.transmission_outcomes_accessed)
        self.assertFalse(
            any(path.startswith(("data/", "private/")) for path in first.inspected_paths)
        )
        self.assertTrue(all(len(value) == 64 for value in first.input_sha256.values()))

    def test_tampered_stage_A_binding_fails_closed(self) -> None:
        payload = yaml.safe_load(STAGE_A.read_text(encoding="utf-8"))
        payload["bound_implementation"]["run_028_harness_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "approval.yaml"
            path.write_text(yaml.safe_dump(payload), encoding="utf-8")
            with self.assertRaisesRegex(CalibrationReadinessError, "harness"):
                audit_calibration_readiness(PROTOCOL, AMENDMENT, APPROVAL, HARNESS, path)

    def test_cli_writes_once_and_returns_deliberate_stop_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "audit.json"
            command = [sys.executable, str(SCRIPT), "--output", str(output)]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 2)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["gaps"]), 9)
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("refusing to overwrite", second.stderr)


if __name__ == "__main__":
    unittest.main()
