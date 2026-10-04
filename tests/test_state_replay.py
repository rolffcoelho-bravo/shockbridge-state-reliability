import csv
import tempfile
import unittest
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import yaml

from shockbridge_state_risk.data.download import sha256_file
from shockbridge_state_risk.state.replay import (
    ReplayRow,
    StateReplayError,
    assert_probability_integrity,
    load_state_matrix,
    load_state_replay_config,
    run_state_replay,
    write_replay_csv,
)


class StateReplayTests(unittest.TestCase):
    FEATURES = (
        "hicp_yoy",
        "industrial_production_yoy",
        "unemployment_rate",
        "deposit_facility_rate",
    )

    @staticmethod
    def _write_inputs(root: Path, events: int = 26) -> tuple[Path, Path]:
        panel = root / "panel.csv"
        shocks = root / "shocks.csv"
        panel_fields = [
            "event_id",
            "feature_id",
            "admission_status",
            "missing",
            "value",
        ]
        start = date(2002, 1, 3)
        with panel.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=panel_fields)
            writer.writeheader()
            for index in range(events):
                event_date = start + timedelta(days=35 * index)
                slack = -1.0 if index < events // 2 else 1.0
                values = (2.0 + 0.2 * slack, 1.2 - 2.0 * slack, 7.0 + slack, 1.0 + slack)
                for feature, value in zip(StateReplayTests.FEATURES, values):
                    writer.writerow(
                        {
                            "event_id": f"ecb-pr-{event_date.isoformat()}",
                            "feature_id": feature,
                            "admission_status": "ADMITTED",
                            "missing": "False",
                            "value": value + 0.01 * index,
                        }
                    )
        with shocks.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["date", "target"])
            writer.writeheader()
            for index in range(events):
                event_date = start + timedelta(days=35 * index)
                writer.writerow({"date": event_date.isoformat(), "target": (-1) ** index * 0.1})
        return panel, shocks

    def _write_config(self, root: Path, panel: Path, shocks: Path) -> Path:
        config = root / "config.yaml"
        config.write_text(
            yaml.safe_dump(
                {
                    "panel_path": str(panel),
                    "panel_sha256": sha256_file(panel),
                    "shock_path": str(shocks),
                    "shock_sha256": sha256_file(shocks),
                    "features": list(self.FEATURES),
                    "n_states": 2,
                    "minimum_training_events": 20,
                    "restarts": 2,
                    "max_iterations": 80,
                    "tolerance": 1e-6,
                    "variance_floor": 0.05,
                    "transition_prior": 0.5,
                    "random_seed": 44,
                    "minimum_hard_count": 1,
                    "minimum_weighted_ess": 1.0,
                    "maximum_mean_entropy": 0.7,
                    "minimum_restart_agreement": 0.0,
                }
            ),
            encoding="utf-8",
        )
        return config

    def test_full_replay_is_outcome_blind_and_writes_probabilities(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            panel, shocks = self._write_inputs(root)
            config = load_state_replay_config(self._write_config(root, panel, shocks))
            result = run_state_replay(config)
            output = root / "nested" / "probabilities.csv"
            write_replay_csv(result.rows, output)
            with output.open(encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 26)
        self.assertEqual(rows[0]["probability_state_0"], "")
        self.assertAlmostEqual(
            float(rows[-1]["probability_state_0"]) + float(rows[-1]["probability_state_1"]),
            1.0,
        )
        self.assertFalse(result.audit["outcomes_accessed"])
        self.assertFalse(result.audit["shock_used_for_model_selection"])
        self.assertEqual(result.audit["support"]["warmup_events"], 20)

    def test_hash_mismatch_and_probability_corruption_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            panel, shocks = self._write_inputs(root)
            config_path = self._write_config(root, panel, shocks)
            payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            payload["panel_sha256"] = "0" * 64
            config_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
            with self.assertRaises(StateReplayError):
                load_state_replay_config(config_path)

        valid = ReplayRow("event", "2020-01-01", 20, 0.5, 0.5, 0, 0.69, 0.0, 0.0, 1.0, True, 2, 1)
        assert_probability_integrity((valid,))
        with self.assertRaises(StateReplayError):
            assert_probability_integrity((replace(valid, probability_state_1=0.4),))
        with self.assertRaises(StateReplayError):
            assert_probability_integrity((replace(valid, probability_state_0=None),))

    def test_state_loader_rejects_duplicate_and_incomplete_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            panel, _ = self._write_inputs(root)
            rows = panel.read_text(encoding="utf-8").splitlines()
            duplicate = root / "duplicate.csv"
            duplicate.write_text("\n".join([*rows, rows[1]]) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(StateReplayError, "Duplicate event feature row"):
                load_state_matrix(duplicate, self.FEATURES)
            incomplete = root / "incomplete.csv"
            incomplete.write_text("\n".join([rows[0], *rows[2:]]) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(StateReplayError, "Missing event feature row"):
                load_state_matrix(incomplete, self.FEATURES)

    def test_replay_config_rejects_duplicate_features(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            panel, shocks = self._write_inputs(root)
            config_path = self._write_config(root, panel, shocks)
            baseline = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            cases = (
                ("duplicate features", "features", [*baseline["features"], self.FEATURES[0]]),
                ("too few restarts", "restarts", 1),
                ("invalid optimizer", "max_iterations", 0),
                ("negative support", "minimum_weighted_ess", -1.0),
                ("invalid agreement", "minimum_restart_agreement", 1.1),
            )
            for label, key, value in cases:
                with self.subTest(label=label):
                    payload = yaml.safe_load(yaml.safe_dump(baseline))
                    payload[key] = value
                    config_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
                    with self.assertRaises(StateReplayError):
                        load_state_replay_config(config_path)


if __name__ == "__main__":
    unittest.main()
