import csv
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np
import yaml

from shockbridge_state_risk.data.download import sha256_file
from shockbridge_state_risk.state.run008 import (
    FactorThresholds,
    Run008Config,
    Run008Error,
    Run008Result,
    SubspaceThresholds,
    load_run008_config,
    run_run008,
    write_run008_outputs,
)

ROOT = Path(__file__).resolve().parents[1]
FEATURES = (
    "hicp_yoy",
    "industrial_production_yoy",
    "unemployment_rate",
    "deposit_facility_rate",
)


class Run008Tests(unittest.TestCase):
    @staticmethod
    def _write_panel(path: Path, months: int = 130) -> None:
        fields = (
            "event_id",
            "state_cutoff_timestamp",
            "feature_id",
            "value",
            "missing",
            "admission_status",
        )
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for index in range(months):
                year = 2002 + index // 12
                month = index % 12 + 1
                slack = np.sin(index / 8.0) + 0.2 * np.cos(index / 19.0)
                tightness = np.cos(index / 13.0) - 0.1 * np.sin(index / 5.0)
                values = (
                    2.0 - 0.8 * tightness + 0.05 * slack,
                    1.0 - 1.1 * slack + 0.05 * tightness,
                    7.0 + 0.9 * slack - 0.05 * tightness,
                    1.5 + 0.9 * tightness + 0.05 * slack,
                )
                for feature, value in zip(FEATURES, values):
                    writer.writerow(
                        {
                            "event_id": f"month-{year:04d}-{month:02d}",
                            "state_cutoff_timestamp": f"{year:04d}-{month:02d}-01T23:59:59+01:00",
                            "feature_id": feature,
                            "value": value,
                            "missing": "False",
                            "admission_status": "ADMITTED",
                        }
                    )

    @staticmethod
    def _subspace_thresholds() -> SubspaceThresholds:
        return SubspaceThresholds(0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0, -1.0, -1.0)

    @staticmethod
    def _factor_thresholds() -> FactorThresholds:
        return FactorThresholds(-1.0, -1.0, 1.0, 100.0)

    def _config(self, panel: Path, months: int = 130) -> Run008Config:
        final_index = months - 1
        final_year = 2002 + final_index // 12
        final_month = final_index % 12 + 1
        design = ROOT / "research" / "methodology" / "run_008_subspace_design_proposal_v1.yaml"
        return Run008Config(
            config_sha256="test-config",
            experiment_id="state-model-run008-test",
            evidence_status="SOFTWARE_TEST_ONLY",
            approved_design_path=design,
            approved_design_sha256=sha256_file(design),
            panel_path=panel,
            panel_sha256=sha256_file(panel),
            features=FEATURES,
            history_windows=("expanding", "rolling_120"),
            minimum_training_months=60,
            rolling_months=120,
            development_months=120,
            development_start="month-2002-01",
            development_end="month-2011-12",
            evaluation_start="month-2012-01",
            evaluation_end=f"month-{final_year:04d}-{final_month:02d}",
            factor_dimension=2,
            variance_floor=0.05,
            transition_ridge=1e-6,
            maximum_transition_spectral_radius=0.98,
            subspace_thresholds=self._subspace_thresholds(),
            fixed_scalar_thresholds=self._factor_thresholds(),
            require_positive_mean_log_score_gain_each_history=True,
            two_factor_thresholds=self._factor_thresholds(),
            outcomes_accessed=False,
            state_model_execution_authorized=True,
            transmission_outcome_execution_authorized=False,
        )

    @unittest.skipUnless(
        (ROOT / "data/processed/monthly_state_panel_v2.csv").is_file(),
        "requires local hash-registered evidence",
    )
    def test_frozen_config_loads_and_hostile_changes_fail_closed(self) -> None:
        path = ROOT / "experiments" / "state_model_run008_v1.yaml"
        config = load_run008_config(path)
        self.assertEqual(config.config_sha256, sha256_file(path))
        self.assertEqual(config.features, FEATURES)
        self.assertTrue(config.state_model_execution_authorized)
        self.assertFalse(config.outcomes_accessed)
        self.assertFalse(config.transmission_outcome_execution_authorized)

        original = yaml.safe_load(path.read_text(encoding="utf-8"))
        mutations = (
            ("outcomes_accessed", True),
            ("state_model_execution_authorized", False),
            ("transmission_outcome_execution_authorized", True),
            ("factor_dimension", 1),
            ("development_months", 119),
            ("approved_design_sha256", "0" * 64),
            ("unexpected_field", 1),
        )
        with tempfile.TemporaryDirectory() as directory:
            for key, value in mutations:
                with self.subTest(key=key):
                    payload = dict(original)
                    payload[key] = value
                    candidate = Path(directory) / f"{key}.yaml"
                    candidate.write_text(yaml.safe_dump(payload), encoding="utf-8")
                    with self.assertRaises(Run008Error):
                        load_run008_config(candidate)

    def test_run_is_deterministic_outcome_blind_and_excludes_shared_histories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            panel = Path(directory) / "panel.csv"
            self._write_panel(panel)
            config = self._config(panel)
            first = run_run008(config)
            second = run_run008(config)
            self.assertEqual(first, second)
            self.assertEqual(len(first.subspace_rows), 140)
            self.assertEqual(len(first.fixed_factor_rows), 20)
            self.assertEqual(len(first.two_factor_rows), 140)
            self.assertEqual(first.audit["cross_window_distinct_origins"], 9)
            self.assertEqual(first.audit["cross_window_shared_origins_excluded"], 61)
            self.assertFalse(first.audit["outcomes_accessed"])
            self.assertFalse(first.audit["synthetic_observations_used"])
            self.assertFalse(first.audit["transmission_estimation_authorized"])
            self.assertEqual(
                first.audit["anchored_two_factor_diagnostic"]["transmission_eligible"], False
            )

            subspace_path = Path(directory) / "nested" / "subspace.csv"
            fixed_path = Path(directory) / "nested" / "fixed.csv"
            two_path = Path(directory) / "nested" / "two.csv"
            audit_path = Path(directory) / "nested" / "audit.json"
            write_run008_outputs(first, subspace_path, fixed_path, two_path, audit_path)
            for output_path, expected_rows in (
                (subspace_path, 140),
                (fixed_path, 20),
                (two_path, 140),
            ):
                with output_path.open(newline="", encoding="utf-8") as stream:
                    self.assertEqual(len(list(csv.DictReader(stream))), expected_rows)
            self.assertEqual(json.loads(audit_path.read_text()), first.audit)
            self.assertFalse(any(Path(directory).rglob("*.part")))
            with self.assertRaisesRegex(Run008Error, "distinct"):
                write_run008_outputs(
                    first,
                    subspace_path,
                    subspace_path,
                    two_path,
                    audit_path,
                )

    def test_future_change_cannot_modify_earlier_estimates_or_frozen_loading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            panel = Path(directory) / "panel.csv"
            self._write_panel(panel)
            config = self._config(panel)
            original = run_run008(config)
            original_loading = original.audit["development_fixed_loading"]
            with panel.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            changed_month = "month-2012-07"
            for row in rows:
                if row["event_id"] == changed_month and row["feature_id"] == "hicp_yoy":
                    row["value"] = str(float(row["value"]) + 25.0)
            with panel.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            altered = run_run008(replace(config, panel_sha256=sha256_file(panel)))
            self.assertEqual(altered.audit["development_fixed_loading"], original_loading)
            for first_rows, second_rows in (
                (original.subspace_rows, altered.subspace_rows),
                (original.fixed_factor_rows, altered.fixed_factor_rows),
                (original.two_factor_rows, altered.two_factor_rows),
            ):
                self.assertEqual(
                    tuple(row for row in first_rows if row.month_id < changed_month),
                    tuple(row for row in second_rows if row.month_id < changed_month),
                )

    def test_hash_rechecks_invalid_boundaries_metrics_and_empty_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            panel = Path(directory) / "panel.csv"
            self._write_panel(panel)
            config = self._config(panel)
            panel.write_text(panel.read_text() + "\n", encoding="utf-8")
            with self.assertRaisesRegex(Run008Error, "changed"):
                run_run008(config)
            repaired = replace(config, panel_sha256=sha256_file(panel))
            with self.assertRaisesRegex(Run008Error, "frozen contract"):
                run_run008(replace(repaired, evidence_status="REAL_DATA_OUTCOME_BLIND"))
            with self.assertRaisesRegex(Run008Error, "boundaries"):
                run_run008(replace(repaired, development_end="month-2011-11"))
            with self.assertRaises(Run008Error):
                run_run008(replace(repaired, rolling_months=200))
            with self.assertRaises(Run008Error):
                write_run008_outputs(
                    Run008Result((), (), (), {}),
                    Path(directory) / "subspace.csv",
                    Path(directory) / "fixed.csv",
                    Path(directory) / "two.csv",
                    Path(directory) / "audit.json",
                )


if __name__ == "__main__":
    unittest.main()
