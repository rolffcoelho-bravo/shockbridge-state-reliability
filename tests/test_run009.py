import csv
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np
import yaml

from shockbridge_state_risk.data.download import sha256_file
from shockbridge_state_risk.state.run009 import (
    EpisodeRule,
    GeometryReferences,
    Run009Config,
    Run009Error,
    Run009Result,
    load_run009_config,
    run_run009,
    write_run009_outputs,
)

ROOT = Path(__file__).resolve().parents[1]
FEATURES = (
    "hicp_yoy",
    "industrial_production_yoy",
    "unemployment_rate",
    "deposit_facility_rate",
)


class Run009Tests(unittest.TestCase):
    @staticmethod
    def _month(index: int) -> str:
        return f"month-{2002 + index // 12:04d}-{index % 12 + 1:02d}"

    @classmethod
    def _write_panel(cls, path: Path, months: int = 170) -> None:
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
                first = np.sin(index / 9.0) + 0.2 * np.cos(index / 23.0)
                second = np.cos(index / 14.0) - 0.1 * np.sin(index / 4.0)
                values = (
                    2.0 + first + 0.15 * second,
                    1.0 - 1.1 * first + 0.10 * second,
                    7.0 + 0.9 * first - 0.05 * second,
                    -0.2 + 0.8 * second + 0.05 * first,
                )
                for feature, value in zip(FEATURES, values):
                    missing = feature == "industrial_production_yoy" and index in {12, 88}
                    writer.writerow(
                        {
                            "event_id": cls._month(index),
                            "state_cutoff_timestamp": (f"{year:04d}-{month:02d}-01T23:59:59+01:00"),
                            "feature_id": feature,
                            "value": "" if missing else value,
                            "missing": str(missing),
                            "admission_status": "ADMITTED",
                        }
                    )

    @classmethod
    def _write_fixed_factor(cls, path: Path, months: int = 170) -> None:
        with path.open("w", newline="", encoding="utf-8") as stream:
            fields = ("month_id", "history_window", "standardized_factor_mean")
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for index in range(120, months):
                for history in ("expanding", "rolling_120"):
                    base = np.sin(index / 11.0)
                    value = base if history == "expanding" else base + 0.1 * np.cos(index / 5.0)
                    writer.writerow(
                        {
                            "month_id": cls._month(index),
                            "history_window": history,
                            "standardized_factor_mean": value,
                        }
                    )

    @staticmethod
    def _write_manifest(path: Path, fixed_path: Path) -> None:
        payload = {
            "selection_status": "KILL_GATE_RUN_008_REQUIRED_GATES_FAILED",
            "frozen_design": {
                "outcomes_accessed": False,
                "synthetic_observations_used": False,
            },
            "outputs": {
                "fixed_factor": {
                    "path": str(fixed_path),
                    "sha256": sha256_file(fixed_path),
                }
            },
            "decision": {
                "selected_primary_state_representation": None,
                "transmission_estimation_authorized": False,
            },
        }
        path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    def _config(self, directory: Path, months: int = 170) -> Run009Config:
        panel = directory / "panel.csv"
        fixed = directory / "fixed.csv"
        manifest = directory / "manifest.yaml"
        self._write_panel(panel, months)
        self._write_fixed_factor(fixed, months)
        self._write_manifest(manifest, fixed)
        design = (
            ROOT / "research" / "methodology" / "run_009_instability_diagnostic_proposal_v1.yaml"
        )
        return Run009Config(
            config_sha256="test-config",
            experiment_id="state-instability-run009-test",
            evidence_status="SOFTWARE_TEST_ONLY",
            approved_design_path=design,
            approved_design_sha256=sha256_file(design),
            panel_path=panel,
            panel_sha256=sha256_file(panel),
            run_008_manifest_path=manifest,
            run_008_manifest_sha256=sha256_file(manifest),
            run_008_fixed_factor_path=fixed,
            run_008_fixed_factor_sha256=sha256_file(fixed),
            features=FEATURES,
            factor_dimension=2,
            rolling_months=(96, 120, 144),
            panel_start="month-2002-01",
            panel_end=self._month(months - 1),
            common_origin_start="month-2014-02",
            common_origin_end=self._month(months - 1),
            geometry_references=GeometryReferences(0.75, 0.90, 0.35, 0.35, 0.35, 0.20, 1.00, 0.50),
            episode_rules=(
                EpisodeRule(3, 3, True),
                EpisodeRule(1, 1, False),
                EpisodeRule(6, 6, False),
            ),
            policy_rate_zero_tolerance=1e-12,
            sign_materiality_thresholds=(0.25, 0.10, 0.50),
            leave_one_feature_out=True,
            outcomes_accessed=False,
            run_009_state_diagnostic_execution_authorized=True,
            transmission_outcome_execution_authorized=False,
        )

    @unittest.skipUnless(
        (ROOT / "data/processed/state_fixed_factor_run008_v1.csv").is_file(),
        "requires local hash-registered evidence",
    )
    def test_frozen_empirical_config_loads_and_hostile_changes_fail_closed(self) -> None:
        path = ROOT / "experiments" / "state_instability_run009_v1.yaml"
        config = load_run009_config(path)
        self.assertEqual(config.config_sha256, sha256_file(path))
        self.assertEqual(config.rolling_months, (96, 120, 144))
        self.assertTrue(config.leave_one_feature_out)
        self.assertFalse(config.outcomes_accessed)
        original = yaml.safe_load(path.read_text(encoding="utf-8"))
        mutations = (
            ("outcomes_accessed", True),
            ("run_009_state_diagnostic_execution_authorized", False),
            ("transmission_outcome_execution_authorized", True),
            ("factor_dimension", True),
            ("rolling_months", [96, 120]),
            ("panel_sha256", "0" * 64),
            ("schema_version", 2),
            ("unexpected_field", 1),
        )
        with tempfile.TemporaryDirectory() as directory:
            for key, value in mutations:
                with self.subTest(key=key):
                    payload = dict(original)
                    payload[key] = value
                    candidate = Path(directory) / f"{key}.yaml"
                    candidate.write_text(yaml.safe_dump(payload), encoding="utf-8")
                    with self.assertRaises(Run009Error):
                        load_run009_config(candidate)

    def test_run_is_deterministic_complete_outcome_blind_and_writes_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory_text:
            directory = Path(directory_text)
            config = self._config(directory)
            first = run_run009(config)
            second = run_run009(config)
            self.assertEqual(first, second)
            self.assertEqual(len(first.diagnostic_rows), 735)
            self.assertEqual(first.audit["common_origins"], 25)
            self.assertEqual(
                set(first.audit["geometry_summary"]),
                {
                    "full",
                    "omit_hicp_yoy",
                    "omit_industrial_production_yoy",
                    "omit_unemployment_rate",
                    "omit_deposit_facility_rate",
                },
            )
            self.assertFalse(first.audit["outcomes_accessed"])
            self.assertEqual(first.audit["evidence_status"], "SOFTWARE_TEST_ONLY")
            self.assertTrue(first.audit["synthetic_observations_used"])
            self.assertFalse(first.audit["transmission_estimation_authorized"])
            full = next(row for row in first.diagnostic_rows if row.panel_variant == "full")
            omitted = next(row for row in first.diagnostic_rows if row.panel_variant != "full")
            self.assertIsNotNone(full.expanding_policy_anchor_capture)
            self.assertIsNotNone(full.location_shift_json)
            self.assertIsNone(omitted.expanding_policy_anchor_capture)
            self.assertIsNone(omitted.location_shift_json)

            outputs = []
            for suffix in ("one", "two"):
                target = directory / suffix
                diagnostic = target / "diagnostic.csv"
                episodes = target / "episodes.csv"
                audit = target / "audit.json"
                write_run009_outputs(first, diagnostic, episodes, audit)
                outputs.append((diagnostic, episodes, audit))
                self.assertEqual(json.loads(audit.read_text()), first.audit)
                self.assertFalse(any(target.rglob("*.part")))
            for left, right in zip(outputs[0], outputs[1]):
                self.assertEqual(left.read_bytes(), right.read_bytes())
            with self.assertRaisesRegex(Run009Error, "distinct"):
                write_run009_outputs(first, outputs[0][0], outputs[0][0], outputs[0][2])

    def test_future_change_cannot_modify_earlier_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as directory_text:
            directory = Path(directory_text)
            config = self._config(directory)
            original = run_run009(config)
            with config.panel_path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            changed_month = "month-2015-06"
            for row in rows:
                if row["event_id"] == changed_month and row["feature_id"] == "hicp_yoy":
                    row["value"] = str(float(row["value"]) + 20.0)
            with config.panel_path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            altered = run_run009(replace(config, panel_sha256=sha256_file(config.panel_path)))
            earlier_original = tuple(
                row for row in original.diagnostic_rows if row.month_id <= changed_month
            )
            earlier_altered = tuple(
                row for row in altered.diagnostic_rows if row.month_id <= changed_month
            )
            self.assertEqual(earlier_original, earlier_altered)

    def test_hash_boundaries_and_incomplete_outputs_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory_text:
            directory = Path(directory_text)
            config = self._config(directory)
            config.panel_path.write_text(config.panel_path.read_text() + "\n", encoding="utf-8")
            with self.assertRaisesRegex(Run009Error, "changed"):
                run_run009(config)
            repaired = replace(config, panel_sha256=sha256_file(config.panel_path))
            hostile_configs = (
                replace(repaired, features=(FEATURES[0],) * 4),
                replace(repaired, factor_dimension=1),
                replace(
                    repaired,
                    episode_rules=(
                        EpisodeRule(True, 1, False),
                        EpisodeRule(3, 3, True),
                        EpisodeRule(6, 6, False),
                    ),
                ),
                replace(
                    repaired,
                    geometry_references=replace(
                        repaired.geometry_references,
                        weak_relative_eigengap=float("nan"),
                    ),
                ),
                replace(repaired, sign_materiality_thresholds=(0.2, 0.1, 0.5)),
                replace(repaired, leave_one_feature_out=False),
                replace(
                    repaired,
                    evidence_status="REAL_DATA_OUTCOME_BLIND",
                    experiment_id="wrong-real-run",
                ),
            )
            for hostile in hostile_configs:
                with self.subTest(hostile=hostile):
                    with self.assertRaises(Run009Error):
                        run_run009(hostile)
            with self.assertRaisesRegex(Run009Error, "boundaries"):
                run_run009(replace(repaired, common_origin_start="month-2030-01"))

            manifest = yaml.safe_load(repaired.run_008_manifest_path.read_text())
            manifest["frozen_design"]["outcomes_accessed"] = True
            repaired.run_008_manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
            hostile_manifest = replace(
                repaired,
                run_008_manifest_sha256=sha256_file(repaired.run_008_manifest_path),
            )
            with self.assertRaisesRegex(Run009Error, "kill gate"):
                run_run009(hostile_manifest)
            self._write_manifest(repaired.run_008_manifest_path, repaired.run_008_fixed_factor_path)
            repaired = replace(
                repaired,
                run_008_manifest_sha256=sha256_file(repaired.run_008_manifest_path),
            )
            with self.assertRaisesRegex(Run009Error, "incomplete"):
                write_run009_outputs(
                    Run009Result((), (), {}),
                    directory / "diagnostic.csv",
                    directory / "episodes.csv",
                    directory / "audit.json",
                )
            stale = directory / "fresh.csv.part"
            stale.write_text("incomplete", encoding="utf-8")
            result = run_run009(repaired)
            with self.assertRaisesRegex(Run009Error, "pre-existing"):
                write_run009_outputs(
                    result,
                    directory / "fresh.csv",
                    directory / "fresh-episodes.csv",
                    directory / "fresh-audit.json",
                )
            stale.unlink()
            invalid_row = replace(result.diagnostic_rows[0], second_principal_cosine=float("nan"))
            invalid_result = replace(
                result,
                diagnostic_rows=(invalid_row, *result.diagnostic_rows[1:]),
            )
            with self.assertRaisesRegex(Run009Error, "non-finite"):
                write_run009_outputs(
                    invalid_result,
                    directory / "invalid.csv",
                    directory / "invalid-episodes.csv",
                    directory / "invalid-audit.json",
                )
            self.assertFalse(any(directory.glob("invalid*.part")))


if __name__ == "__main__":
    unittest.main()
