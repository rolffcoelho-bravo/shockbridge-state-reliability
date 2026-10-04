import csv
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np
import yaml

from shockbridge_state_risk.data.download import sha256_file
from shockbridge_state_risk.state.instability import detect_breach_episodes
from shockbridge_state_risk.state.run009 import EpisodeRule
from shockbridge_state_risk.state.run009_amendment import (
    Run009AmendmentConfig,
    Run009AmendmentError,
    Run009AmendmentResult,
    load_run009_amendment_config,
    run_run009_amendment,
    write_run009_amendment_outputs,
)

ROOT = Path(__file__).resolve().parents[1]


class Run009AmendmentTests(unittest.TestCase):
    @staticmethod
    def _months() -> tuple[str, ...]:
        return tuple(
            f"month-{2014 + (month + 1) // 12:04d}-{(month + 1) % 12 + 1:02d}"
            for month in range(141)
        )

    def _config(self, directory: Path) -> Run009AmendmentConfig:
        diagnostics = directory / "diagnostics.csv"
        original_episodes = directory / "episodes.csv"
        source_audit = directory / "audit.json"
        source_manifest = directory / "manifest.yaml"
        months = self._months()
        variants = (
            "full",
            "omit_hicp_yoy",
            "omit_industrial_production_yoy",
            "omit_unemployment_rate",
            "omit_deposit_facility_rate",
        )
        rules = (
            EpisodeRule(3, 3, True),
            EpisodeRule(1, 1, False),
            EpisodeRule(6, 6, False),
        )
        with diagnostics.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=(
                    "month_id",
                    "panel_variant",
                    "rolling_months",
                    "primary_common_sample",
                    "core_breach",
                ),
            )
            writer.writeheader()
            for variant in variants:
                for window in (96, 120, 144):
                    flags = np.zeros(141, dtype=bool)
                    if variant == variants[-1] and window == 144:
                        flags[-10:] = True
                    else:
                        flags[10:20] = True
                    for month, flag in zip(months, flags):
                        writer.writerow(
                            {
                                "month_id": month,
                                "panel_variant": variant,
                                "rolling_months": window,
                                "primary_common_sample": True,
                                "core_breach": bool(flag),
                            }
                        )
        original_rows = []
        for variant in variants:
            for window in (96, 120, 144):
                flags = np.zeros(141, dtype=bool)
                if variant == variants[-1] and window == 144:
                    flags[-10:] = True
                else:
                    flags[10:20] = True
                omitted = None if variant == "full" else variant.removeprefix("omit_")
                for rule in rules:
                    episodes = detect_breach_episodes(
                        months,
                        flags,
                        rule.minimum_consecutive_breaches,
                        rule.recovery_consecutive_stable,
                    )
                    for number, episode in enumerate(episodes, start=1):
                        original_rows.append(
                            {
                                "panel_variant": variant,
                                "omitted_feature": omitted,
                                "rolling_months": window,
                                "minimum_consecutive_breaches": (rule.minimum_consecutive_breaches),
                                "recovery_consecutive_stable": (rule.recovery_consecutive_stable),
                                "primary_rule": rule.primary,
                                "episode_number": number,
                                "start_month": episode.start_month,
                                "end_month": episode.end_month,
                                "duration_months": episode.duration_months,
                                "breach_months": episode.breach_months,
                            }
                        )
        with original_episodes.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=(
                    "panel_variant",
                    "omitted_feature",
                    "rolling_months",
                    "minimum_consecutive_breaches",
                    "recovery_consecutive_stable",
                    "primary_rule",
                    "episode_number",
                    "start_month",
                    "end_month",
                    "duration_months",
                    "breach_months",
                ),
            )
            writer.writeheader()
            writer.writerows(original_rows)
        source_audit.write_text(
            json.dumps(
                {
                    "outcomes_accessed": False,
                    "episode_rows": len(original_rows),
                    "transmission_estimation_authorized": False,
                }
            ),
            encoding="utf-8",
        )
        manifest = {
            "artifact_id": "state-instability-run009-v1",
            "outputs": {
                "diagnostics": {"sha256": sha256_file(diagnostics)},
                "episodes": {"sha256": sha256_file(original_episodes)},
                "audit": {"sha256": sha256_file(source_audit)},
            },
            "decision": {
                "state_selected": False,
                "transmission_estimation_authorized": False,
            },
        }
        source_manifest.write_text(yaml.safe_dump(manifest), encoding="utf-8")
        protocol = ROOT / "research" / "methodology" / "run_009_episode_amendment_1_protocol.yaml"
        return Run009AmendmentConfig(
            config_sha256="test-config",
            amendment_id="run009-amendment-test",
            evidence_status="SOFTWARE_TEST_ONLY",
            approved_protocol_path=protocol,
            approved_protocol_sha256=sha256_file(protocol),
            source_manifest_path=source_manifest,
            source_manifest_sha256=sha256_file(source_manifest),
            diagnostic_path=diagnostics,
            diagnostic_sha256=sha256_file(diagnostics),
            original_episode_path=original_episodes,
            original_episode_sha256=sha256_file(original_episodes),
            source_audit_path=source_audit,
            source_audit_sha256=sha256_file(source_audit),
            common_origin_start=months[0],
            common_origin_end=months[-1],
            episode_rules=rules,
            outcomes_accessed=False,
            amendment_execution_authorized=True,
            transmission_outcome_execution_authorized=False,
        )

    @unittest.skipUnless(
        (ROOT / "data/processed/state_instability_episodes_run009_v1.csv").is_file(),
        "requires local hash-registered evidence",
    )
    def test_frozen_config_loads_and_hostile_change_fails(self) -> None:
        path = ROOT / "experiments" / "state_instability_run009_v1_amendment_1.yaml"
        config = load_run009_amendment_config(path)
        self.assertEqual(config.config_sha256, sha256_file(path))
        self.assertFalse(config.outcomes_accessed)
        with tempfile.TemporaryDirectory() as directory:
            original = yaml.safe_load(path.read_text(encoding="utf-8"))
            mutations = (
                ("outcomes_accessed", True),
                ("schema_version", 2),
                ("episode_rules", "not-a-list"),
                ("unexpected", 1),
            )
            for key, value in mutations:
                payload = dict(original)
                payload[key] = value
                candidate = Path(directory) / f"{key}.yaml"
                candidate.write_text(yaml.safe_dump(payload), encoding="utf-8")
                with self.subTest(key=key):
                    with self.assertRaises(Run009AmendmentError):
                        load_run009_amendment_config(candidate)

    def test_amendment_matches_original_and_marks_open_episodes(self) -> None:
        with tempfile.TemporaryDirectory() as directory_text:
            directory = Path(directory_text)
            config = self._config(directory)
            first = run_run009_amendment(config)
            second = run_run009_amendment(config)
            self.assertEqual(first, second)
            self.assertEqual(len(first.episode_rows), 45)
            self.assertEqual(first.audit["open_episode_rows"], 3)
            self.assertTrue(first.audit["synthetic_observations_used"])
            self.assertTrue(first.audit["original_fields_exact_match"])
            self.assertTrue(all(row.open_at_sample_end for row in first.episode_rows[-3:]))
            episode_path = directory / "out" / "episodes.csv"
            audit_path = directory / "out" / "audit.json"
            write_run009_amendment_outputs(first, episode_path, audit_path)
            with episode_path.open(newline="", encoding="utf-8") as stream:
                persisted = list(csv.DictReader(stream))
            self.assertEqual(len(persisted), 45)
            self.assertEqual(persisted[-1]["open_at_sample_end"], "True")
            self.assertEqual(json.loads(audit_path.read_text()), first.audit)

    def test_source_mismatch_and_output_failures_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory_text:
            directory = Path(directory_text)
            config = self._config(directory)
            result = run_run009_amendment(config)
            config.diagnostic_path.write_text(
                config.diagnostic_path.read_text(encoding="utf-8") + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(Run009AmendmentError, "changed"):
                run_run009_amendment(config)

            config = self._config(directory)
            result = run_run009_amendment(config)
            hostile_configs = (
                replace(config, outcomes_accessed=True),
                replace(config, episode_rules=config.episode_rules[:2]),
                replace(
                    config,
                    evidence_status="REAL_DATA_OUTCOME_BLIND_AMENDMENT",
                    amendment_id="wrong-amendment",
                ),
            )
            for hostile in hostile_configs:
                with self.subTest(hostile=hostile.amendment_id):
                    with self.assertRaises(Run009AmendmentError):
                        run_run009_amendment(hostile)

            source_audit = json.loads(config.source_audit_path.read_text())
            source_audit["outcomes_accessed"] = True
            config.source_audit_path.write_text(json.dumps(source_audit), encoding="utf-8")
            hostile_audit = replace(
                config,
                source_audit_sha256=sha256_file(config.source_audit_path),
            )
            manifest = yaml.safe_load(config.source_manifest_path.read_text())
            manifest["outputs"]["audit"]["sha256"] = hostile_audit.source_audit_sha256
            config.source_manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
            hostile_audit = replace(
                hostile_audit,
                source_manifest_sha256=sha256_file(config.source_manifest_path),
            )
            with self.assertRaisesRegex(Run009AmendmentError, "boundary"):
                run_run009_amendment(hostile_audit)

            config = self._config(directory)
            result = run_run009_amendment(config)
            manifest = yaml.safe_load(config.source_manifest_path.read_text())
            manifest["decision"]["state_selected"] = True
            config.source_manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
            hostile_manifest = replace(
                config,
                source_manifest_sha256=sha256_file(config.source_manifest_path),
            )
            with self.assertRaisesRegex(Run009AmendmentError, "immutable"):
                run_run009_amendment(hostile_manifest)

            config = self._config(directory)
            with config.diagnostic_path.open(newline="", encoding="utf-8") as stream:
                diagnostic_rows = list(csv.DictReader(stream))
            with config.diagnostic_path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(diagnostic_rows[0]))
                writer.writeheader()
                writer.writerows(diagnostic_rows[:-1])
            incomplete = replace(
                config,
                diagnostic_sha256=sha256_file(config.diagnostic_path),
            )
            manifest = yaml.safe_load(config.source_manifest_path.read_text())
            manifest["outputs"]["diagnostics"]["sha256"] = incomplete.diagnostic_sha256
            config.source_manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
            incomplete = replace(
                incomplete,
                source_manifest_sha256=sha256_file(config.source_manifest_path),
            )
            with self.assertRaisesRegex(Run009AmendmentError, "incomplete"):
                run_run009_amendment(incomplete)

            config = self._config(directory)
            with config.diagnostic_path.open(newline="", encoding="utf-8") as stream:
                diagnostic_rows = list(csv.DictReader(stream))
            diagnostic_rows[0]["core_breach"] = "invalid"
            with config.diagnostic_path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(diagnostic_rows[0]))
                writer.writeheader()
                writer.writerows(diagnostic_rows)
            invalid_flag = replace(
                config,
                diagnostic_sha256=sha256_file(config.diagnostic_path),
            )
            manifest = yaml.safe_load(config.source_manifest_path.read_text())
            manifest["outputs"]["diagnostics"]["sha256"] = invalid_flag.diagnostic_sha256
            config.source_manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
            invalid_flag = replace(
                invalid_flag,
                source_manifest_sha256=sha256_file(config.source_manifest_path),
            )
            with self.assertRaisesRegex(Run009AmendmentError, "breach flag"):
                run_run009_amendment(invalid_flag)

            config = self._config(directory)
            with config.original_episode_path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            for row in rows:
                row["unexpected"] = ""
            with config.original_episode_path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            invalid_schema = replace(
                config,
                original_episode_sha256=sha256_file(config.original_episode_path),
            )
            manifest = yaml.safe_load(config.source_manifest_path.read_text())
            manifest["outputs"]["episodes"]["sha256"] = invalid_schema.original_episode_sha256
            config.source_manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
            invalid_schema = replace(
                invalid_schema,
                source_manifest_sha256=sha256_file(config.source_manifest_path),
            )
            with self.assertRaisesRegex(Run009AmendmentError, "fields"):
                run_run009_amendment(invalid_schema)

            config = self._config(directory)
            with config.original_episode_path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            rows[0]["duration_months"] = "999"
            with config.original_episode_path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            altered = replace(
                config,
                original_episode_sha256=sha256_file(config.original_episode_path),
            )
            manifest = yaml.safe_load(config.source_manifest_path.read_text())
            manifest["outputs"]["episodes"]["sha256"] = altered.original_episode_sha256
            config.source_manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
            altered = replace(
                altered,
                source_manifest_sha256=sha256_file(config.source_manifest_path),
            )
            with self.assertRaisesRegex(Run009AmendmentError, "differ"):
                run_run009_amendment(altered)
            with self.assertRaisesRegex(Run009AmendmentError, "incomplete"):
                write_run009_amendment_outputs(
                    Run009AmendmentResult((), {}),
                    directory / "empty.csv",
                    directory / "empty.json",
                )
            with self.assertRaisesRegex(Run009AmendmentError, "distinct"):
                write_run009_amendment_outputs(result, directory / "same", directory / "same")
            stale_target = directory / "stale.csv"
            stale_target.with_suffix(".csv.part").write_text("stale", encoding="utf-8")
            with self.assertRaisesRegex(Run009AmendmentError, "stale"):
                write_run009_amendment_outputs(result, stale_target, directory / "stale.json")


if __name__ == "__main__":
    unittest.main()
