import csv
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np
import yaml

from shockbridge_state_risk.data.download import sha256_file
from shockbridge_state_risk.state.run007 import (
    Run007Config,
    Run007Error,
    Run007Result,
    load_run007_config,
    run_run007,
    write_run007_outputs,
)
from shockbridge_state_risk.state.stability import StabilityThresholds

ROOT = Path(__file__).resolve().parents[1]
FEATURES = (
    "hicp_yoy",
    "industrial_production_yoy",
    "unemployment_rate",
    "deposit_facility_rate",
)


class Run007Tests(unittest.TestCase):
    @staticmethod
    def _write_panel(path: Path, months: int = 124) -> None:
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
                year = 2000 + index // 12
                month = index % 12 + 1
                cycle = np.sin(index / 7.0) + 0.15 * np.cos(index / 3.0)
                values = (
                    2.0 + 0.4 * cycle,
                    1.2 - 1.1 * cycle + 0.05 * np.sin(index / 2.0),
                    7.5 + 0.9 * cycle,
                    1.0 + 0.25 * np.cos(index / 9.0),
                )
                for feature, value in zip(FEATURES, values):
                    writer.writerow(
                        {
                            "event_id": f"month-{year:04d}-{month:02d}",
                            "state_cutoff_timestamp": (f"{year:04d}-{month:02d}-01T23:59:59+01:00"),
                            "feature_id": feature,
                            "value": value,
                            "missing": "False",
                            "admission_status": "ADMITTED",
                        }
                    )

    @staticmethod
    def _thresholds() -> StabilityThresholds:
        return StabilityThresholds(
            minimum_pearson_correlation=0.0,
            minimum_spearman_correlation=0.0,
            maximum_sign_disagreement_rate=1.0,
            maximum_standardized_mean_absolute_difference=100.0,
            minimum_median_loading_cosine=0.0,
            minimum_loading_cosine=0.0,
            minimum_anchor_tenth_percentile=0.0,
            weak_anchor_cutoff=0.0,
            maximum_weak_anchor_rate=1.0,
        )

    def _config(self, panel: Path) -> Run007Config:
        return Run007Config(
            config_sha256="test-config",
            experiment_id="state-model-run007-test",
            evidence_status="SOFTWARE_TEST_ONLY",
            panel_path=panel,
            panel_sha256=sha256_file(panel),
            features=FEATURES,
            history_windows=("expanding", "rolling_120"),
            minimum_training_months=118,
            rolling_months=120,
            variance_floor=0.05,
            random_seed=17,
            state_counts=(2, 3),
            pca_components=2,
            pca_restarts=2,
            hmm_restarts=2,
            hmm_max_iterations=20,
            hmm_tolerance=1e-5,
            transition_prior=0.5,
            hmm_objective_gap_grid=(0.0, 2.0, 5.0, 10.0),
            thresholds=self._thresholds(),
            outcomes_accessed=False,
            execution_authorized=True,
        )

    @unittest.skipUnless(
        (ROOT / "data/processed/monthly_state_panel_v2.csv").is_file(),
        "requires local hash-registered evidence",
    )
    def test_frozen_config_loads_and_hostile_changes_fail_closed(self) -> None:
        path = ROOT / "experiments" / "state_model_run007_v1.yaml"
        config = load_run007_config(path)
        self.assertEqual(config.config_sha256, sha256_file(path))
        self.assertEqual(config.features, FEATURES)
        self.assertFalse(config.outcomes_accessed)
        self.assertTrue(config.execution_authorized)

        original = yaml.safe_load(path.read_text(encoding="utf-8"))
        mutations = (
            ("outcomes_accessed", "false"),
            ("execution_authorized", False),
            ("minimum_training_months", 61),
            ("schema_version", 2),
            ("features", "hicp_yoy"),
        )
        with tempfile.TemporaryDirectory() as directory:
            for key, value in mutations:
                with self.subTest(key=key, value=value):
                    payload = dict(original)
                    payload[key] = value
                    candidate = Path(directory) / f"{key}.yaml"
                    candidate.write_text(yaml.safe_dump(payload), encoding="utf-8")
                    with self.assertRaises(Run007Error):
                        load_run007_config(candidate)

    def test_run_is_deterministic_outcome_blind_and_excludes_shared_windows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            panel = Path(directory) / "panel.csv"
            self._write_panel(panel)
            config = self._config(panel)
            first = run_run007(config)
            second = run_run007(config)

            self.assertEqual(first, second)
            self.assertEqual(len(first.factor_rows), 12)
            self.assertEqual(len(first.challenger_rows), 72)
            self.assertEqual(len(first.restart_records), 192)
            self.assertEqual(first.audit["cross_window_distinct_origins"], 3)
            self.assertEqual(first.audit["cross_window_shared_origins_excluded"], 3)
            self.assertFalse(first.audit["outcomes_accessed"])
            self.assertFalse(first.audit["synthetic_observations_used"])
            self.assertFalse(first.audit["transmission_estimation_authorized"])
            self.assertEqual(
                first.audit["selected_primary_state_representation"], "continuous_factor"
            )
            record_types = {record["record_type"] for record in first.restart_records}
            self.assertEqual(
                record_types,
                {"pca_restart", "hmm_restart", "hmm_gap_sensitivity"},
            )

            factor_path = Path(directory) / "nested" / "factor.csv"
            challenger_path = Path(directory) / "nested" / "challenger.csv"
            restart_path = Path(directory) / "nested" / "restarts.jsonl"
            audit_path = Path(directory) / "nested" / "audit.json"
            write_run007_outputs(
                first,
                factor_path,
                challenger_path,
                restart_path,
                audit_path,
            )
            with factor_path.open(newline="", encoding="utf-8") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 12)
            with challenger_path.open(newline="", encoding="utf-8") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 72)
            self.assertEqual(len(restart_path.read_text().splitlines()), 192)
            self.assertEqual(json.loads(audit_path.read_text()), first.audit)
            self.assertFalse(any(Path(directory).rglob("*.part")))

            with panel.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            for row in rows:
                if row["event_id"] == "month-2010-04":
                    row["value"] = str(float(row["value"]) + 50.0)
            with panel.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            altered = run_run007(replace(config, panel_sha256=sha256_file(panel)))
            self.assertEqual(
                tuple(row for row in first.factor_rows if row.month_id != "month-2010-04"),
                tuple(row for row in altered.factor_rows if row.month_id != "month-2010-04"),
            )
            self.assertEqual(
                tuple(row for row in first.challenger_rows if row.month_id != "month-2010-04"),
                tuple(row for row in altered.challenger_rows if row.month_id != "month-2010-04"),
            )
            self.assertEqual(
                tuple(
                    record
                    for record in first.restart_records
                    if record["month_id"] != "month-2010-04"
                ),
                tuple(
                    record
                    for record in altered.restart_records
                    if record["month_id"] != "month-2010-04"
                ),
            )

    def test_panel_hash_is_rechecked_at_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            panel = Path(directory) / "panel.csv"
            self._write_panel(panel)
            config = self._config(panel)
            panel.write_text(panel.read_text() + "\n", encoding="utf-8")
            with self.assertRaisesRegex(Run007Error, "changed"):
                run_run007(config)

    def test_invalid_config_shape_and_empty_output_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            malformed = Path(directory) / "malformed.yaml"
            malformed.write_text("- not\n- a\n- mapping\n", encoding="utf-8")
            with self.assertRaises(Run007Error):
                load_run007_config(malformed)

            panel = Path(directory) / "panel.csv"
            self._write_panel(panel)
            config = self._config(panel)
            with self.assertRaises(Run007Error):
                run_run007(replace(config, panel_sha256="0" * 64))
            with self.assertRaisesRegex(Run007Error, "empty"):
                write_run007_outputs(
                    Run007Result((), (), (), {}),
                    Path(directory) / "factor.csv",
                    Path(directory) / "challenger.csv",
                    Path(directory) / "restart.jsonl",
                    Path(directory) / "audit.json",
                )


if __name__ == "__main__":
    unittest.main()
