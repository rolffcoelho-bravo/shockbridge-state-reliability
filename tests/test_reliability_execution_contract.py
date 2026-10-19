import csv
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from shockbridge_state_risk.state import reliability_execution_contract as contract
from shockbridge_state_risk.state.reliability_execution_contract import (
    ReliabilityExecutionContractError,
    audit_reliability_execution_contract,
    write_reliability_execution_contract_audit,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = (
    ROOT / "research/methodology/run_026_information_clock_reliability_execution_protocol_v1.yaml"
)
AUTHENTIC_PANEL = (
    ROOT / "data/processed/run025_dfr_effective_dates_v1/"
    "registered_mir_bsi__effective_day_dfr/p0_core_replay_and_fast.csv"
)
EVIDENCE_SKIP_REASON = "requires local hash-registered evidence"


class ReliabilityExecutionContractTests(unittest.TestCase):
    def _fixture(self, directory: str) -> tuple[Path, Path, dict]:
        """Build synthetic software files that are never empirical evidence."""
        root = Path(directory)
        (root / "pyproject.toml").write_text("[project]\nname='run026-fixture'\n", encoding="utf-8")
        payload = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
        for index, item in enumerate(payload["bound_inputs"]):
            destination = root / str(item["path"])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(f"synthetic software fixture {index}\n", encoding="utf-8")
            item["bytes"] = destination.stat().st_size
            item["sha256"] = hashlib.sha256(destination.read_bytes()).hexdigest()
        for scenario in payload["source_clock_inputs"]["scenarios"]:
            scenario_id = str(scenario["scenario_id"])
            mir_next_day = scenario_id.startswith("next_day_mir_bsi")
            dfr_next_day = scenario_id.endswith("next_day_dfr")
            for panel in scenario["panels"]:
                panel_id = str(panel["panel_id"])
                destination = root / str(panel["path"])
                destination.parent.mkdir(parents=True, exist_ok=True)
                series_count = 7 if panel_id == "P0_CORE_REPLAY_AND_FAST" else 10
                with destination.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=contract.PANEL_COLUMNS)
                    writer.writeheader()
                    for origin in range(274):
                        year = 2003 + origin // 12
                        month = origin % 12 + 1
                        origin_month = f"{year:04d}-{month:02d}"
                        for series in range(series_count):
                            timing_shift = (
                                0.125
                                if panel_id == "P1_AUGMENTED_BANK_CREDIT"
                                and mir_next_day
                                and series in {7, 8, 9}
                                else 0.0
                            )
                            writer.writerow(
                                {
                                    "panel_id": panel_id,
                                    "origin_month": origin_month,
                                    "origin_timestamp": f"{origin_month}-01T23:59:59+01:00",
                                    "series_id": f"S{series:02d}",
                                    "observation_period": origin_month,
                                    "usable_timestamp": (
                                        f"{origin_month}-{'03' if dfr_next_day else '02'}"
                                        "T00:00:00+01:00"
                                    ),
                                    "transformed_value": (
                                        f"{origin + series / 10 + timing_shift:.3f}"
                                    ),
                                    "is_missing": "0",
                                    "missing_reason": "",
                                    "source_response_sha256": f"{series:064x}",
                                }
                            )
                panel["bytes"] = destination.stat().st_size
                panel["sha256"] = hashlib.sha256(destination.read_bytes()).hexdigest()
        relative_protocol = PROTOCOL.relative_to(ROOT)
        protocol_path = root / relative_protocol
        protocol_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_protocol(protocol_path, payload)
        return root, protocol_path, payload

    def _write_protocol(self, protocol_path: Path, payload: dict) -> None:
        protocol_path.write_text(
            yaml.safe_dump(payload, sort_keys=False, width=100), encoding="utf-8"
        )

    def _rehash_panel(self, payload: dict, relative: str, path: Path) -> None:
        for scenario in payload["source_clock_inputs"]["scenarios"]:
            for panel in scenario["panels"]:
                if panel["path"] == relative:
                    panel["bytes"] = path.stat().st_size
                    panel["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                    return
        self.fail(f"panel not found in protocol: {relative}")

    def _write_panel(self, path: Path, row: dict[str, str]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=contract.PANEL_COLUMNS)
            writer.writeheader()
            writer.writerow(row)

    @unittest.skipUnless(
        PROTOCOL.is_file() and AUTHENTIC_PANEL.is_file(),
        EVIDENCE_SKIP_REASON,
    )
    def test_registered_protocol_is_outcome_sealed_and_duplicate_neutral(self) -> None:
        audit = audit_reliability_execution_contract(PROTOCOL)
        self.assertTrue(audit.passed)
        self.assertEqual(audit.bound_inputs_verified, 12)
        self.assertEqual(audit.source_clock_labels, 4)
        self.assertEqual(audit.panel_files_verified, 8)
        self.assertEqual(audit.panel_rows_verified, 18632)
        self.assertEqual(audit.analytic_equivalence_classes, 3)
        self.assertEqual(audit.provenance_labeled_scenario_ceiling, 224)
        self.assertEqual(audit.unique_analytic_scenario_ceiling, 88)
        self.assertEqual(audit.comparator_count, 4)
        self.assertTrue(audit.evaluation_labels_matured)
        self.assertFalse(audit.empirical_reliability_fit_performed)
        self.assertFalse(audit.evaluation_results_accessed)
        self.assertFalse(audit.transmission_outcomes_accessed)
        self.assertFalse(audit.synthetic_empirical_observations_used)

    @unittest.skipUnless(
        PROTOCOL.is_file() and AUTHENTIC_PANEL.is_file(),
        EVIDENCE_SKIP_REASON,
    )
    def test_relative_protocol_path_matches_absolute_preflight(self) -> None:
        relative = PROTOCOL.relative_to(ROOT)
        audit = audit_reliability_execution_contract(relative)
        self.assertEqual(audit.protocol_path, str(relative))
        self.assertTrue(audit.passed)

    def test_writer_is_atomic_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, protocol_path, _ = self._fixture(directory)
            audit = audit_reliability_execution_contract(protocol_path)
            output = root / "audit.json"
            write_reliability_execution_contract_audit(audit, output)
            self.assertIn('"passed": true', output.read_text(encoding="utf-8"))
            self.assertEqual(list(Path(directory).glob("*.part")), [])
            with self.assertRaisesRegex(ReliabilityExecutionContractError, "refusing to overwrite"):
                write_reliability_execution_contract_audit(audit, output)

    def test_writer_removes_temporary_file_after_atomic_replace_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, protocol_path, _ = self._fixture(directory)
            audit = audit_reliability_execution_contract(protocol_path)
            output = root / "audit.json"
            with mock.patch.object(contract.os, "replace", side_effect=OSError("replace failed")):
                with self.assertRaisesRegex(OSError, "replace failed"):
                    write_reliability_execution_contract_audit(audit, output)
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(directory).glob("*.part")), [])

    def test_low_level_contract_guards_fail_closed(self) -> None:
        with self.assertRaisesRegex(ReliabilityExecutionContractError, "must be a mapping"):
            contract._mapping([], "object")
        with self.assertRaisesRegex(ReliabilityExecutionContractError, "nonempty list"):
            contract._list([], "items")
        with self.assertRaisesRegex(ReliabilityExecutionContractError, "nonempty string"):
            contract._nonempty("  ", "name")
        for value in (True, 0, -1, "1"):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ReliabilityExecutionContractError, "positive integer"),
            ):
                contract._positive_int(value, "count")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "nested/protocol.yaml"
            nested.parent.mkdir(parents=True)
            nested.write_text("status: test\n", encoding="utf-8")
            with self.assertRaisesRegex(
                ReliabilityExecutionContractError, "cannot locate project root"
            ):
                contract._project_root(nested)
            with self.assertRaisesRegex(
                ReliabilityExecutionContractError, "escapes the project root"
            ):
                contract._inside(root, "../outside", "artifact")
            with self.assertRaisesRegex(ReliabilityExecutionContractError, "exact SHA-256"):
                contract._validate_registered_file(
                    root, {"path": "missing", "bytes": 1, "sha256": "not-a-hash"}, "artifact"
                )
            with self.assertRaisesRegex(ReliabilityExecutionContractError, "is missing"):
                contract._validate_registered_file(
                    root, {"path": "missing", "bytes": 1, "sha256": "0" * 64}, "artifact"
                )
            present = root / "present"
            present.write_text("x", encoding="utf-8")
            with self.assertRaisesRegex(ReliabilityExecutionContractError, "byte or hash mismatch"):
                contract._validate_registered_file(
                    root, {"path": "present", "bytes": 2, "sha256": "0" * 64}, "artifact"
                )
        with self.assertRaisesRegex(ReliabilityExecutionContractError, "must use YYYY-MM"):
            contract._month_index("2026-13", "month")

    def test_panel_reader_rejects_schema_identity_and_value_anomalies(self) -> None:
        valid = {
            "panel_id": "P0_CORE_REPLAY_AND_FAST",
            "origin_month": "2020-01",
            "origin_timestamp": "2020-01-01T23:59:59+01:00",
            "series_id": "TEST",
            "observation_period": "2019-12",
            "usable_timestamp": "2019-12-15T00:00:00+01:00",
            "transformed_value": "1.5",
            "is_missing": "0",
            "missing_reason": "",
            "source_response_sha256": "0" * 64,
        }
        cases = (
            ("panel_id", "WRONG", "panel_id mismatch"),
            ("is_missing", "x", "invalid missingness flag"),
            ("transformed_value", "not-a-number", "not numeric"),
            ("transformed_value", "nan", "nonfinite"),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            schema_path = root / "schema.csv"
            schema_path.write_text("wrong,column\n1,2\n", encoding="utf-8")
            with self.assertRaisesRegex(ReliabilityExecutionContractError, "schema mismatch"):
                contract._analytic_panel_hash(schema_path, valid["panel_id"], 1)
            for field, value, message in cases:
                with self.subTest(field=field, value=value):
                    path = root / f"{field}-{value}.csv"
                    row = dict(valid)
                    row[field] = value
                    self._write_panel(path, row)
                    with self.assertRaisesRegex(ReliabilityExecutionContractError, message):
                        contract._analytic_panel_hash(path, valid["panel_id"], 1)
            missing_value_path = root / "missing-value.csv"
            missing_row = dict(valid, is_missing="1", transformed_value="1.5")
            self._write_panel(missing_value_path, missing_row)
            with self.assertRaisesRegex(ReliabilityExecutionContractError, "missing panel row"):
                contract._analytic_panel_hash(missing_value_path, valid["panel_id"], 1)
            valid_path = root / "valid.csv"
            self._write_panel(valid_path, valid)
            with self.assertRaisesRegex(ReliabilityExecutionContractError, "row count mismatch"):
                contract._analytic_panel_hash(valid_path, valid["panel_id"], 2)

    def test_bound_input_mutation_fails_before_panel_inspection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, protocol_path, _ = self._fixture(directory)
            bound = root / "research/methodology/run_020_information_set_reliability_method_v1.md"
            bound.write_text(bound.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ReliabilityExecutionContractError, "byte or hash mismatch"):
                audit_reliability_execution_contract(protocol_path)

    def test_scientific_firewalls_fail_closed(self) -> None:
        mutations = (
            ("synthetic_empirical_observations_allowed", True),
            ("empirical_reliability_fit_allowed_during_protocol_freeze", True),
            ("evaluation_results_access_allowed_during_protocol_freeze", True),
            ("transmission_outcomes_access_allowed", True),
            ("transmission_module_import_allowed", True),
            ("methodological_novelty_claim_allowed", True),
        )
        for field, value in mutations:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                _, protocol_path, payload = self._fixture(directory)
                payload["scientific_boundary"][field] = value
                self._write_protocol(protocol_path, payload)
                with self.assertRaisesRegex(ReliabilityExecutionContractError, field):
                    audit_reliability_execution_contract(protocol_path)

    def test_value_change_cannot_masquerade_as_timestamp_only_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, protocol_path, payload = self._fixture(directory)
            relative = (
                "data/processed/run025_dfr_effective_dates_v1/"
                "next_day_mir_bsi__next_day_dfr/p1_augmented_bank_credit.csv"
            )
            panel_path = root / relative
            with panel_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["transformed_value"] = str(float(rows[0]["transformed_value"]) + 0.25)
            with panel_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            self._rehash_panel(payload, relative, panel_path)
            self._write_protocol(protocol_path, payload)
            with self.assertRaisesRegex(
                ReliabilityExecutionContractError, "three frozen analytic classes"
            ):
                audit_reliability_execution_contract(protocol_path)

    def test_duplicate_panel_key_fails_even_with_updated_file_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, protocol_path, payload = self._fixture(directory)
            relative = (
                "data/processed/run025_dfr_effective_dates_v1/"
                "registered_mir_bsi__effective_day_dfr/p0_core_replay_and_fast.csv"
            )
            panel_path = root / relative
            with panel_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            rows[1]["origin_month"] = rows[0]["origin_month"]
            rows[1]["series_id"] = rows[0]["series_id"]
            with panel_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            self._rehash_panel(payload, relative, panel_path)
            self._write_protocol(protocol_path, payload)
            with self.assertRaisesRegex(ReliabilityExecutionContractError, "duplicate panel key"):
                audit_reliability_execution_contract(protocol_path)

    def test_registered_comparator_and_slow_release_rules_cannot_be_dropped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _, protocol_path, payload = self._fixture(directory)
            payload["registered_comparators"] = payload["registered_comparators"][:-1]
            self._write_protocol(protocol_path, payload)
            with self.assertRaisesRegex(
                ReliabilityExecutionContractError, "registered comparator set changed"
            ):
                audit_reliability_execution_contract(protocol_path)
        with tempfile.TemporaryDirectory() as directory:
            _, protocol_path, payload = self._fixture(directory)
            payload["model_scenario_generator"]["release_lag_policies"] = [
                "observed_registered_source_clock"
            ]
            self._write_protocol(protocol_path, payload)
            with self.assertRaisesRegex(
                ReliabilityExecutionContractError, "slow-release stress was dropped"
            ):
                audit_reliability_execution_contract(protocol_path)


if __name__ == "__main__":
    unittest.main()
