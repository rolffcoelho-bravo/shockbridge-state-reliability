import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from shockbridge_state_risk.state.reliability_protocol_completeness import (
    ReliabilityProtocolCompletenessError,
    audit_protocol_completeness,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = (
    ROOT / "research/methodology/run_026_information_clock_reliability_execution_protocol_v1.yaml"
)
SCRIPT = ROOT / "scripts/run027_protocol_completeness_audit.py"


class ReliabilityProtocolCompletenessTests(unittest.TestCase):
    def test_frozen_protocol_stops_before_empirical_fit_with_eleven_exact_gaps(self) -> None:
        audit = audit_protocol_completeness(PROTOCOL)
        self.assertFalse(audit.passed)
        self.assertEqual(audit.critical_gap_count, 11)
        self.assertEqual(
            tuple(item.gap_id for item in audit.gaps),
            tuple(f"XG-{index:02d}" for index in range(1, 12)),
        )
        self.assertFalse(audit.empirical_fit_performed)
        self.assertFalse(audit.evaluation_results_accessed)
        self.assertFalse(audit.transmission_outcomes_accessed)

    def test_audit_contains_reproducible_protocol_identity(self) -> None:
        first = audit_protocol_completeness(PROTOCOL)
        second = audit_protocol_completeness(PROTOCOL)
        self.assertEqual(first, second)
        self.assertEqual(len(first.protocol_sha256), 64)
        self.assertEqual(
            first.protocol_path,
            "research/methodology/run_026_information_clock_reliability_execution_protocol_v1.yaml",
        )

    def test_wrong_protocol_identity_and_missing_root_fail_closed(self) -> None:
        payload = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
        payload["protocol_id"] = "wrong"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
            path = root / "protocol.yaml"
            path.write_text(yaml.safe_dump(payload), encoding="utf-8")
            with self.assertRaisesRegex(ReliabilityProtocolCompletenessError, "identifier"):
                audit_protocol_completeness(path)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "protocol.yaml"
            path.write_text("protocol_id: test\n", encoding="utf-8")
            with self.assertRaisesRegex(ReliabilityProtocolCompletenessError, "project root"):
                audit_protocol_completeness(path)

    def test_cli_serializes_failure_audit_once_and_returns_stop_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "audit.json"
            command = [
                sys.executable,
                str(SCRIPT),
                "--protocol",
                str(PROTOCOL),
                "--output",
                str(output),
            ]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 2)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertFalse(payload["passed"])
            self.assertEqual(payload["critical_gap_count"], 11)
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("refusing to overwrite", second.stderr)


if __name__ == "__main__":
    unittest.main()
