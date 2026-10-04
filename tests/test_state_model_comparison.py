import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

from shockbridge_state_risk.data.download import sha256_file
from shockbridge_state_risk.state.benchmarks import (
    predict_change_point,
    predict_dynamic_factor,
    predict_hidden_markov,
    predict_pca_cluster,
)
from shockbridge_state_risk.state.comparison import (
    load_comparison_config,
    load_monthly_matrix,
    run_comparison,
    write_comparison_audit,
    write_comparison_csv,
)


class StateModelComparisonTests(unittest.TestCase):
    @staticmethod
    def _fixture(rows: int = 90) -> np.ndarray:
        values = []
        for index in range(rows):
            regime = (index // 15) % 3
            values.append(
                [
                    1.0 + regime + 0.02 * index,
                    2.0 - regime + 0.1 * np.sin(index),
                    9.0 - regime + 0.05 * np.cos(index),
                    -0.5 + regime,
                ]
            )
        result = np.asarray(values, dtype=np.float64)
        result[20, 1] = np.nan
        return result

    @staticmethod
    def _write_fixture_config(root: Path, fixture: np.ndarray, stem: str = "comparison") -> Path:
        panel = root / f"{stem}_panel.csv"
        fields = [
            "event_id",
            "state_cutoff_timestamp",
            "feature_id",
            "value",
            "missing",
            "admission_status",
        ]
        features = [
            "hicp_yoy",
            "industrial_production_yoy",
            "unemployment_rate",
            "deposit_facility_rate",
        ]
        with panel.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for index, values in enumerate(fixture):
                year = 2000 + index // 12
                month = index % 12 + 1
                cutoff = datetime(year, month, 1, 23, 59, 59, tzinfo=timezone.utc).isoformat()
                for feature, value in zip(features, values):
                    writer.writerow(
                        {
                            "event_id": f"month-{year:04d}-{month:02d}",
                            "state_cutoff_timestamp": cutoff,
                            "feature_id": feature,
                            "value": "" if np.isnan(value) else value,
                            "missing": str(bool(np.isnan(value))),
                            "admission_status": "ADMITTED",
                        }
                    )
        config_path = root / f"{stem}_config.yaml"
        config_path.write_text(
            yaml.safe_dump(
                {
                    "panel_path": str(panel),
                    "panel_sha256": sha256_file(panel),
                    "features": features,
                    "models": [
                        "pca_cluster",
                        "dynamic_factor",
                        "hidden_markov",
                        "change_point",
                    ],
                    "state_counts": [2, 3],
                    "history_windows": ["expanding", "rolling_120"],
                    "minimum_training_months": 60,
                    "random_seed": 5,
                    "kmeans_restarts": 3,
                    "hmm_restarts": 2,
                    "hmm_max_iterations": 60,
                    "hmm_tolerance": 1e-6,
                    "variance_floor": 0.05,
                    "transition_prior": 0.5,
                    "pca_components": 2,
                    "change_point_threshold": 3.5,
                    "change_point_minimum_segment": 12,
                    "screening": {
                        "minimum_global_hard_count": 1,
                        "minimum_global_weighted_ess": 1.0,
                        "minimum_block_hard_count": 0,
                        "minimum_block_weighted_ess": 0.0,
                        "minimum_restart_agreement": 0.0,
                        "require_score_gain_vs_single_gaussian": False,
                    },
                    "selection": {
                        "primary_state_count": 2,
                        "primary_history_window": "expanding",
                    },
                }
            ),
            encoding="utf-8",
        )
        return config_path

    def test_all_benchmarks_return_valid_probabilities(self) -> None:
        train = self._fixture()
        current = np.asarray([3.0, 0.5, 7.0, 2.0], dtype=np.float64)
        predictions = [
            predict_pca_cluster(train, current, 2, 2, 4, 0.05, 1),
            predict_dynamic_factor(train, current, 2, 4, 0.05, 2),
            predict_hidden_markov(train, current, 2, 3, 100, 1e-6, 0.05, 0.5, 3),
            predict_change_point(train, current, 2, 4, 0.05, 3.5, 12, 4),
        ]
        for prediction in predictions:
            self.assertAlmostEqual(float(np.sum(prediction.probabilities)), 1.0)
            self.assertTrue(np.isfinite(prediction.log_predictive_score))
            self.assertEqual(prediction.state_profiles.shape, (2, 4))

    def test_change_point_falls_back_when_segment_feature_is_all_missing(self) -> None:
        train = self._fixture()
        train[-15:, 2] = np.nan
        prediction = predict_change_point(
            train,
            np.asarray([2.0, 0.5, 7.0, 1.0]),
            2,
            4,
            0.05,
            3.5,
            12,
            42,
        )
        self.assertTrue(np.isfinite(prediction.log_predictive_score))

    def test_monthly_loader_rejects_duplicate_and_incomplete_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = load_comparison_config(self._write_fixture_config(root, self._fixture(64)))
            rows = config.panel_path.read_text(encoding="utf-8").splitlines()
            duplicate = root / "duplicate.csv"
            duplicate.write_text("\n".join([*rows, rows[1]]) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate monthly feature row"):
                load_monthly_matrix(duplicate, config.features)
            incomplete = root / "incomplete.csv"
            incomplete.write_text("\n".join([rows[0], *rows[2:]]) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing monthly feature row"):
                load_monthly_matrix(incomplete, config.features)

    def test_comparison_config_rejects_duplicate_grid_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = self._write_fixture_config(root, self._fixture(64))
            baseline = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            cases = (
                ("duplicate models", ("models",), [*baseline["models"], "dynamic_factor"]),
                ("grid is not a list", ("history_windows",), "expanding"),
                (
                    "score flag is not Boolean",
                    ("screening", "require_score_gain_vs_single_gaussian"),
                    "False",
                ),
                ("duplicate features", ("features",), [*baseline["features"], "hicp_yoy"]),
                ("short warmup", ("minimum_training_months",), 35),
                ("too few restarts", ("kmeans_restarts",), 1),
                ("invalid optimizer", ("hmm_tolerance",), 0.0),
                ("invalid threshold", ("screening", "minimum_restart_agreement"), 1.1),
                ("invalid primary state", ("selection", "primary_state_count"), 4),
                ("invalid primary window", ("selection", "primary_history_window"), "other"),
            )
            for label, keys, value in cases:
                with self.subTest(label=label):
                    payload = yaml.safe_load(yaml.safe_dump(baseline))
                    target = payload
                    for key in keys[:-1]:
                        target = target[key]
                    target[keys[-1]] = value
                    config_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_comparison_config(config_path)

            payload = yaml.safe_load(yaml.safe_dump(baseline))
            del payload["screening"]["minimum_global_hard_count"]
            config_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Screening config is missing"):
                load_comparison_config(config_path)

    def test_end_to_end_comparison_writes_auditable_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = self._write_fixture_config(root, self._fixture(64))
            result = run_comparison(load_comparison_config(config_path))
            csv_path = root / "nested" / "comparison.csv"
            audit_path = root / "nested" / "audit.json"
            write_comparison_csv(result.rows, csv_path)
            write_comparison_audit(result.audit, audit_path)
            self.assertEqual(len(result.rows), 64)
            self.assertTrue(csv_path.is_file())
            self.assertTrue(audit_path.is_file())
            self.assertFalse(result.audit["outcomes_accessed"])

    def test_comparison_is_exactly_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = load_comparison_config(self._write_fixture_config(root, self._fixture(64)))
            first = run_comparison(config)
            second = run_comparison(config)
            self.assertEqual(first.rows, second.rows)
            self.assertEqual(first.audit, second.audit)

    def test_future_observation_cannot_change_earlier_estimates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline_values = self._fixture(66)
            altered_values = baseline_values.copy()
            altered_values[-1] = np.asarray([50.0, -40.0, 30.0, 20.0])
            baseline = run_comparison(
                load_comparison_config(
                    self._write_fixture_config(root, baseline_values, "baseline")
                )
            )
            altered = run_comparison(
                load_comparison_config(self._write_fixture_config(root, altered_values, "altered"))
            )
            final_month = "month-2005-06"
            baseline_past = tuple(row for row in baseline.rows if row.month_id != final_month)
            altered_past = tuple(row for row in altered.rows if row.month_id != final_month)
            self.assertEqual(baseline_past, altered_past)
            self.assertNotEqual(baseline.rows, altered.rows)


if __name__ == "__main__":
    unittest.main()
