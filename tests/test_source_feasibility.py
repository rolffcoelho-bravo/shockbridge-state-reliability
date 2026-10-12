import csv
import tempfile
import unittest
from pathlib import Path

from shockbridge_state_risk.data.source_feasibility import (
    SourceFeasibilityError,
    audit_source_feasibility,
    load_and_validate_source_matrix,
    validate_channel_architecture,
)

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "research/data/run_019_source_feasibility_matrix_v1.csv"
ARCHITECTURE = ROOT / "research/data/run_019_channel_architecture_v1.yaml"


class SourceFeasibilityTests(unittest.TestCase):
    def test_registered_run019_records_pass(self) -> None:
        audit = audit_source_feasibility(MATRIX, ARCHITECTURE)
        self.assertEqual(audit.source_rows, 10)
        self.assertEqual(audit.eligibility_counts["A_REPLAY_ELIGIBLE"], 2)
        self.assertEqual(audit.eligibility_counts["B_RELEASE_LAG_ELIGIBLE"], 7)
        self.assertEqual(audit.eligibility_counts["C_BUILD_FORWARD_ONLY"], 1)
        self.assertEqual(audit.eligibility_counts["D_INELIGIBLE"], 0)
        self.assertEqual(audit.architecture_tiers, 6)
        self.assertEqual(audit.required_channels, 8)
        self.assertFalse(audit.empirical_observations_retrieved)
        self.assertFalse(audit.transmission_outcomes_accessed)

    def test_matrix_rejects_nonofficial_locator(self) -> None:
        rows = load_and_validate_source_matrix(MATRIX)
        rows[0]["primary_locator"] = "https://example.com/not-official"
        with tempfile.TemporaryDirectory() as directory_text:
            path = Path(directory_text) / "matrix.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(SourceFeasibilityError, "approved official host"):
                load_and_validate_source_matrix(path)

    def test_architecture_rejects_unknown_source(self) -> None:
        source_ids = {row["source_row_id"] for row in load_and_validate_source_matrix(MATRIX)}
        content = ARCHITECTURE.read_text(encoding="utf-8").replace(
            "DGECFIN_BCS_SA]", "UNKNOWN_SOURCE]"
        )
        with tempfile.TemporaryDirectory() as directory_text:
            path = Path(directory_text) / "architecture.yaml"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(SourceFeasibilityError, "architecture/source mismatch"):
                validate_channel_architecture(path, source_ids)


if __name__ == "__main__":
    unittest.main()
