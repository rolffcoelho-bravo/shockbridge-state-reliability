import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from shockbridge_state_risk.data.series_history import (
    SeriesHistoryError,
    audit_existing_series_pilot,
    audit_series_response,
    classify_timing,
    fetch_and_audit_series_pilot,
    load_and_validate_series_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "research/data/run_020_series_pilot_manifest_v1.yaml"


class SeriesHistoryTests(unittest.TestCase):
    def _write_manifest(self, payload: dict, directory: str) -> Path:
        path = Path(directory) / "manifest.yaml"
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        return path

    def _minimal_project(self, directory: str) -> tuple[Path, Path, Path, dict]:
        root = Path(directory)
        (root / "pyproject.toml").write_text("[project]\nname='schema-fixture'\n", encoding="utf-8")
        manifest_directory = root / "research/data"
        manifest_directory.mkdir(parents=True)
        raw_directory = root / "data/raw/pilot"
        raw_directory.mkdir(parents=True)
        series = []
        channels = ["prices_and_expectations", "real_activity_and_labour"]
        for index, channel in enumerate(channels, start=1):
            pilot_id = f"S{index}"
            series.append(
                {
                    "pilot_id": pilot_id,
                    "full_series_key": f"TEST.M.{pilot_id}",
                    "api_path": f"TEST/M.{pilot_id}",
                    "channel": channel,
                    "panel_role": "schema_fixture",
                    "expected_frequency": "M",
                    "expected_unit": "PC",
                    "proposed_transformation": "level",
                    "sample_start": "2025-01",
                    "sample_end": "2025-01",
                    "expected_timing_class": "B_RELEASE_LAG_ELIGIBLE",
                    "query_url": (
                        "https://data-api.ecb.europa.eu/service/data/"
                        f"TEST/M.{pilot_id}?includeHistory=true&format=csvdata&"
                        "startPeriod=2025-01&endPeriod=2025-01"
                    ),
                    "series_locator": f"https://data.ecb.europa.eu/data/datasets/TEST/{pilot_id}",
                }
            )
        payload = {
            "manifest_id": "schema-fixture",
            "status": "FROZEN_BEFORE_PILOT_OBSERVATION_RETRIEVAL",
            "service_root": "https://data-api.ecb.europa.eu/service/data",
            "rights_locator": "https://www.ecb.europa.eu/stats/usage-policy",
            "real_official_data_only": True,
            "synthetic_empirical_observations_allowed": False,
            "transmission_outcomes_allowed": False,
            "pilot_limits": {
                "maximum_response_bytes_per_series": 10_000,
                "state_estimation": "prohibited",
            },
            "series": series,
            "candidate_panels": [
                {
                    "panel_id": "P0",
                    "series_ids": ["S1"],
                    "required_distinct_channels": 1,
                },
                {
                    "panel_id": "P1",
                    "extends": "P0",
                    "additional_series_ids": ["S2"],
                    "required_distinct_channels": 2,
                },
            ],
        }
        manifest = manifest_directory / "manifest.yaml"
        manifest.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        return root, manifest, raw_directory, payload

    def _write_schema_response(self, path: Path, pilot_id: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "KEY,FREQ,TIME_PERIOD,OBS_VALUE,UNIT,ACTION,VALID_FROM\n"
            f"TEST.M.{pilot_id},M,2025-01,SCHEMA_ONLY,PC,Replace,\n",
            encoding="utf-8",
        )

    def test_registered_manifest_is_frozen_real_and_has_distinct_panels(self) -> None:
        payload = load_and_validate_series_manifest(MANIFEST)
        self.assertEqual(len(payload["series"]), 11)
        self.assertEqual(len(payload["candidate_panels"]), 2)
        self.assertTrue(payload["real_official_data_only"])
        self.assertFalse(payload["synthetic_empirical_observations_allowed"])
        self.assertFalse(payload["transmission_outcomes_allowed"])

    def test_nonofficial_query_host_fails_closed(self) -> None:
        payload = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        payload["series"][0]["query_url"] = payload["series"][0]["query_url"].replace(
            "data-api.ecb.europa.eu", "example.com"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_manifest(payload, directory)
            with self.assertRaisesRegex(SeriesHistoryError, "official host"):
                load_and_validate_series_manifest(path)

    def test_unknown_panel_series_fails_closed(self) -> None:
        payload = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        payload["candidate_panels"][1]["additional_series_ids"].append("UNKNOWN")
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_manifest(payload, directory)
            with self.assertRaisesRegex(SeriesHistoryError, "unknown series"):
                load_and_validate_series_manifest(path)

    def test_timing_classification_uses_release_dates_not_values(self) -> None:
        timing, _, delay = classify_timing(
            "PILOT_TO_CLASSIFY",
            ["2025-01-02", "2025-01-03"],
            ["2025-01-03T16:00:00+01:00", "2025-01-06T16:00:00+01:00"],
        )
        self.assertEqual(timing, "A_REPLAY_ELIGIBLE")
        self.assertEqual(delay, 3)

        timing, _, delay = classify_timing(
            "PILOT_TO_CLASSIFY",
            ["2025-01-02"],
            ["2026-01-02T16:00:00+01:00"],
        )
        self.assertEqual(timing, "B_RELEASE_LAG_ELIGIBLE")
        self.assertEqual(delay, 365)

    def test_replay_class_requires_history_timestamp_on_every_row(self) -> None:
        timing, reason, _ = classify_timing(
            "A_REPLAY_ELIGIBLE",
            ["2025-01", "2025-02"],
            ["2025-02-01T10:00:00+01:00", ""],
        )
        self.assertEqual(timing, "D_INELIGIBLE")
        self.assertIn("lacks VALID_FROM", reason)

    def test_timing_arrays_must_have_equal_length(self) -> None:
        with self.assertRaisesRegex(SeriesHistoryError, "equal length"):
            classify_timing("PILOT_TO_CLASSIFY", ["2025-01-02"], [])

    def test_frozen_timing_classes_and_invalid_dates_are_explicit(self) -> None:
        self.assertEqual(
            classify_timing("C_BUILD_FORWARD_ONLY", ["ignored"], ["ignored"])[0],
            "C_BUILD_FORWARD_ONLY",
        )
        self.assertEqual(
            classify_timing("D_INELIGIBLE", ["ignored"], ["ignored"])[0],
            "D_INELIGIBLE",
        )
        with self.assertRaisesRegex(SeriesHistoryError, "VALID_FROM"):
            classify_timing("PILOT_TO_CLASSIFY", ["2025-01"], ["not-a-date"])
        with self.assertRaisesRegex(SeriesHistoryError, "observation period"):
            classify_timing("PILOT_TO_CLASSIFY", ["not-a-period"], ["2025-01-02"])

    def test_response_unit_must_match_frozen_metadata(self) -> None:
        spec = {
            "pilot_id": "UNIT_SCHEMA_TEST",
            "full_series_key": "TEST.M.OFFICIAL.KEY",
            "expected_frequency": "M",
            "expected_unit": "PC",
            "expected_timing_class": "B_RELEASE_LAG_ELIGIBLE",
            "channel": "real_activity_and_labour",
        }
        content = (
            "KEY,FREQ,TIME_PERIOD,OBS_VALUE,UNIT,ACTION,VALID_FROM\n"
            "TEST.M.OFFICIAL.KEY,M,2025-01,NOT_USED,PC_ACT,Replace,"
            "2025-02-01T10:00:00+01:00\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "response.csv"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(SeriesHistoryError, "unit differs"):
                audit_series_response(spec, path, 10_000)

    def test_response_path_is_project_relative_when_root_is_supplied(self) -> None:
        spec = {
            "pilot_id": "PORTABLE_PATH_TEST",
            "full_series_key": "TEST.M.OFFICIAL.KEY",
            "expected_frequency": "M",
            "expected_unit": "PC",
            "expected_timing_class": "B_RELEASE_LAG_ELIGIBLE",
            "channel": "real_activity_and_labour",
        }
        content = (
            "KEY,FREQ,TIME_PERIOD,OBS_VALUE,UNIT,ACTION,VALID_FROM\n"
            "TEST.M.OFFICIAL.KEY,M,2025-01,NOT_USED,PC,Replace,\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "data/raw/response.csv"
            path.parent.mkdir(parents=True)
            path.write_text(content, encoding="utf-8")
            audit = audit_series_response(spec, path.resolve(), 10_000, root.resolve())
            self.assertEqual(audit.response_path, "data/raw/response.csv")

    def test_response_outside_project_fails_closed(self) -> None:
        spec = {
            "pilot_id": "OUTSIDE_PATH_TEST",
            "full_series_key": "TEST.M.OFFICIAL.KEY",
            "expected_frequency": "M",
            "expected_unit": "PC",
            "expected_timing_class": "B_RELEASE_LAG_ELIGIBLE",
            "channel": "real_activity_and_labour",
        }
        content = (
            "KEY,FREQ,TIME_PERIOD,OBS_VALUE,UNIT,ACTION,VALID_FROM\n"
            "TEST.M.OFFICIAL.KEY,M,2025-01,NOT_USED,PC,Replace,\n"
        )
        with (
            tempfile.TemporaryDirectory() as project_directory,
            tempfile.TemporaryDirectory() as outside,
        ):
            path = Path(outside) / "response.csv"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(SeriesHistoryError, "outside the canonical project"):
                audit_series_response(spec, path, 10_000, Path(project_directory))

    def test_existing_bytes_produce_portable_immutable_aggregate_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, manifest, raw_directory, _ = self._minimal_project(directory)
            self._write_schema_response(raw_directory / "s1.csv", "S1")
            self._write_schema_response(raw_directory / "s2.csv", "S2")
            output = root / "reports/pilot.audit.json"

            result = audit_existing_series_pilot(manifest, raw_directory, output)

            self.assertTrue(result.passed)
            self.assertEqual(result.series_count, 2)
            self.assertEqual(result.channel_count, 2)
            self.assertEqual(result.manifest_path, "research/data/manifest.yaml")
            self.assertEqual(result.all_series[0].response_path, "data/raw/pilot/s1.csv")
            self.assertEqual([panel["passed"] for panel in result.panel_results], [True, True])
            self.assertTrue(output.is_file())
            with self.assertRaisesRegex(SeriesHistoryError, "refusing to overwrite"):
                audit_existing_series_pilot(manifest, raw_directory, output)

    def test_existing_audit_rejects_missing_response_and_unrooted_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _, manifest, raw_directory, _ = self._minimal_project(directory)
            output = Path(directory) / "audit.json"
            with self.assertRaisesRegex(SeriesHistoryError, "missing frozen pilot response"):
                audit_existing_series_pilot(manifest, raw_directory, output)

        with tempfile.TemporaryDirectory() as directory:
            payload = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
            manifest = self._write_manifest(payload, directory)
            with self.assertRaisesRegex(SeriesHistoryError, "pyproject.toml"):
                audit_existing_series_pilot(
                    manifest, Path(directory), Path(directory) / "audit.json"
                )

    def test_panel_gate_fails_when_declared_member_is_forward_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, manifest, raw_directory, payload = self._minimal_project(directory)
            payload["series"][1]["expected_timing_class"] = "C_BUILD_FORWARD_ONLY"
            manifest.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            self._write_schema_response(raw_directory / "s1.csv", "S1")
            self._write_schema_response(raw_directory / "s2.csv", "S2")

            result = audit_existing_series_pilot(
                manifest, raw_directory, root / "reports/forward-only.audit.json"
            )

            self.assertFalse(result.passed)
            self.assertEqual(result.panel_results[1]["retained_series"], ["S1"])

    def test_fetch_uses_frozen_urls_and_refuses_existing_destinations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, manifest, raw_directory, _ = self._minimal_project(directory)
            calls: list[str] = []

            def schema_download(url: str, destination: Path) -> None:
                calls.append(url)
                pilot_id = "S1" if "M.S1" in url else "S2"
                self._write_schema_response(destination, pilot_id)

            with patch(
                "shockbridge_state_risk.data.series_history.download_https",
                side_effect=schema_download,
            ):
                result = fetch_and_audit_series_pilot(
                    manifest, raw_directory, root / "reports/fetch.audit.json"
                )
            self.assertTrue(result.passed)
            self.assertEqual(len(calls), 2)
            self.assertTrue(all("includeHistory=true" in url for url in calls))

            with self.assertRaisesRegex(SeriesHistoryError, "refusing to overwrite"):
                fetch_and_audit_series_pilot(
                    manifest, raw_directory, root / "reports/second-fetch.audit.json"
                )

    def test_response_schema_and_identity_errors_fail_closed(self) -> None:
        spec = {
            "pilot_id": "S1",
            "full_series_key": "TEST.M.S1",
            "expected_frequency": "M",
            "expected_unit": "PC",
            "expected_timing_class": "B_RELEASE_LAG_ELIGIBLE",
            "channel": "prices_and_expectations",
        }
        cases = {
            "exceeds": ("KEY,FREQ,TIME_PERIOD,OBS_VALUE\n" + "x" * 100, 10),
            "lacks columns": ("KEY,FREQ\nTEST.M.S1,M\n", 10_000),
            "contains no rows": ("KEY,FREQ,TIME_PERIOD,OBS_VALUE,UNIT\n", 10_000),
            "key differs": (
                "KEY,FREQ,TIME_PERIOD,OBS_VALUE,UNIT\nOTHER,M,2025-01,X,PC\n",
                10_000,
            ),
            "frequency differs": (
                "KEY,FREQ,TIME_PERIOD,OBS_VALUE,UNIT\nTEST.M.S1,Q,2025-Q1,X,PC\n",
                10_000,
            ),
            "empty pilot observation": (
                "KEY,FREQ,TIME_PERIOD,OBS_VALUE,UNIT\nTEST.M.S1,M,2025-01,,PC\n",
                10_000,
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            for index, (message, (content, limit)) in enumerate(cases.items()):
                with self.subTest(message=message):
                    path = Path(directory) / f"case-{index}.csv"
                    path.write_text(content, encoding="utf-8")
                    with self.assertRaisesRegex(SeriesHistoryError, message):
                        audit_series_response(spec, path, limit)

    def test_manifest_scope_and_panel_mutations_fail_closed(self) -> None:
        base = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        mutations = [
            ("frozen", lambda value: value.update(status="DRAFT")),
            ("real official", lambda value: value.update(real_official_data_only=False)),
            (
                "synthetic empirical",
                lambda value: value.update(synthetic_empirical_observations_allowed=True),
            ),
            (
                "transmission outcomes",
                lambda value: value.update(transmission_outcomes_allowed=True),
            ),
            (
                "positive integer",
                lambda value: value["pilot_limits"].update(maximum_response_bytes_per_series=True),
            ),
            (
                "state estimation",
                lambda value: value["pilot_limits"].update(state_estimation="yes"),
            ),
            ("at least two series", lambda value: value.update(series=value["series"][:1])),
            ("missing fields", lambda value: value["series"][0].pop("expected_unit")),
            (
                "must be unique",
                lambda value: value["series"][1].update(pilot_id=value["series"][0]["pilot_id"]),
            ),
            ("unknown channel", lambda value: value["series"][0].update(channel="unknown")),
            (
                "unknown timing class",
                lambda value: value["series"][0].update(expected_timing_class="unknown"),
            ),
            (
                "does not match api_path",
                lambda value: value["series"][0].update(api_path="RTD/M.WRONG"),
            ),
            (
                "request CSV history",
                lambda value: value["series"][0].update(
                    query_url=value["series"][0]["query_url"].replace(
                        "includeHistory=true", "includeHistory=false"
                    )
                ),
            ),
            (
                "period differs",
                lambda value: value["series"][0].update(
                    query_url=value["series"][0]["query_url"].replace(
                        "startPeriod=2025-01", "startPeriod=2024-01"
                    )
                ),
            ),
            ("at least two candidate panels", lambda value: value.update(candidate_panels=[])),
            (
                "duplicate panel_id",
                lambda value: value["candidate_panels"][1].update(
                    panel_id=value["candidate_panels"][0]["panel_id"]
                ),
            ),
            (
                "unknown or later panel",
                lambda value: value["candidate_panels"][1].update(extends="UNKNOWN"),
            ),
            (
                "additional_series_ids",
                lambda value: value["candidate_panels"][1].update(additional_series_ids=[]),
            ),
            (
                "duplicate series",
                lambda value: value["candidate_panels"][1]["additional_series_ids"].append(
                    value["candidate_panels"][0]["series_ids"][0]
                ),
            ),
        ]
        for message, mutate in mutations:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
                payload = yaml.safe_load(yaml.safe_dump(base))
                mutate(payload)
                path = self._write_manifest(payload, directory)
                with self.assertRaisesRegex(SeriesHistoryError, message):
                    load_and_validate_series_manifest(path)


if __name__ == "__main__":
    unittest.main()
