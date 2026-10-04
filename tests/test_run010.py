import csv
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np
import yaml

from shockbridge_state_risk.data.download import DownloadError, DownloadManifest, sha256_file
from shockbridge_state_risk.state.comparison import load_monthly_matrix
from shockbridge_state_risk.state.run010 import (
    APPROVED_DESIGN_SHA256,
    BootstrapContract,
    GeometryReferences,
    LatestSource,
    Run010Config,
    Run010Error,
    _geometry_rows,
    fetch_run010_sources,
    load_run010_config,
    run_run010,
    write_run010_outputs,
)

ROOT = Path(__file__).resolve().parents[1]
FEATURES = (
    "hicp_yoy",
    "industrial_production_yoy",
    "unemployment_rate",
    "deposit_facility_rate",
)
SOURCE_SPECS = {
    "hicp_yoy": ("RTD.M.S0.N.P_C_OV.X", "N", "P_C_OV", "X"),
    "industrial_production_yoy": ("RTD.M.S0.Y.I_XCONS.X", "Y", "I_XCONS", "X"),
    "unemployment_rate": ("RTD.M.S0.S.L_UNETO.F", "S", "L_UNETO", "F"),
}


class Run010Tests(unittest.TestCase):
    @staticmethod
    def _period(index: int, start_year: int = 2001) -> str:
        return f"{start_year + index // 12:04d}-{index % 12 + 1:02d}"

    @staticmethod
    def _month(index: int) -> str:
        return f"month-{2002 + index // 12:04d}-{index % 12 + 1:02d}"

    @classmethod
    def _levels(cls, feature: str, index: int) -> float:
        if feature == "hicp_yoy":
            return 90.0 * np.exp(0.0025 * index + 0.004 * np.sin(index / 8.0))
        if feature == "industrial_production_yoy":
            return 100.0 + 0.12 * index + 3.0 * np.sin(index / 10.0)
        return 8.5 - 0.006 * index + 0.35 * np.cos(index / 15.0)

    @classmethod
    def _write_latest_source(cls, path: Path, feature: str, periods: int = 182) -> None:
        series, adjustment, concept, denomination = SOURCE_SPECS[feature]
        fields = (
            "KEY",
            "FREQ",
            "REF_AREA",
            "ADJUSTMENT",
            "RT_ECON_CONCEPT",
            "RT_DENOM",
            "TIME_PERIOD",
            "OBS_VALUE",
            "ACTION",
        )
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for index in range(periods):
                writer.writerow(
                    {
                        "KEY": series,
                        "FREQ": "M",
                        "REF_AREA": "S0",
                        "ADJUSTMENT": adjustment,
                        "RT_ECON_CONCEPT": concept,
                        "RT_DENOM": denomination,
                        "TIME_PERIOD": cls._period(index),
                        "OBS_VALUE": cls._levels(feature, index),
                        "ACTION": "Replace",
                    }
                )

    @classmethod
    def _write_panel(cls, path: Path, months: int = 170) -> None:
        fields = (
            "event_id",
            "state_cutoff_timestamp",
            "feature_id",
            "observation_period",
            "value",
            "missing",
            "admission_status",
            "source_artifact_sha256",
        )
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for index in range(months):
                period_index = index + 12
                current = cls._period(period_index)
                previous = cls._period(period_index - 12)
                year, month = current.split("-")
                hicp = 100.0 * (
                    cls._levels("hicp_yoy", period_index)
                    / cls._levels("hicp_yoy", period_index - 12)
                    - 1.0
                ) + 0.08 * np.sin(index / 13.0)
                ip = 100.0 * (
                    cls._levels("industrial_production_yoy", period_index)
                    / cls._levels("industrial_production_yoy", period_index - 12)
                    - 1.0
                ) - 0.12 * np.cos(index / 17.0)
                unemployment = cls._levels("unemployment_rate", period_index) + 0.03 * np.sin(
                    index / 11.0
                )
                dfr = -0.3 + 0.55 * np.cos(index / 18.0) + 0.04 * np.sin(index / 5.0)
                values = (hicp, ip, unemployment, dfr)
                for feature, value in zip(FEATURES, values):
                    missing = feature == "industrial_production_yoy" and index in {12, 88}
                    writer.writerow(
                        {
                            "event_id": cls._month(index),
                            "state_cutoff_timestamp": f"{year}-{month}-01T23:59:59+01:00",
                            "feature_id": feature,
                            "observation_period": previous if missing else current,
                            "value": "" if missing else value,
                            "missing": str(missing),
                            "admission_status": "ADMITTED",
                            "source_artifact_sha256": "d" * 64,
                        }
                    )

    @classmethod
    def _config(cls, directory: Path, months: int = 170) -> Run010Config:
        directory.mkdir(parents=True, exist_ok=True)
        panel = directory / "panel.csv"
        diagnostic = directory / "run009.csv"
        source_manifest = directory / "sources.yaml"
        cls._write_panel(panel, months)
        sources = {}
        for feature in SOURCE_SPECS:
            path = directory / f"{feature}.csv"
            cls._write_latest_source(path, feature, months + 12)
            series = SOURCE_SPECS[feature][0]
            sources[feature] = LatestSource(
                feature,
                path,
                f"https://example.test/{feature}",
                series,
                sha256_file(path),
                path.stat().st_size,
                "2026-10-04T00:00:00+00:00",
            )
        source_manifest.write_text("test: true\n", encoding="utf-8")
        diagnostic.write_text("placeholder\n", encoding="utf-8")
        design = ROOT / "research/methodology/run_010_vintage_robustness_proposal_v1.yaml"
        config = Run010Config(
            config_sha256="test-config",
            experiment_id="state-vintage-robustness-run010-test",
            evidence_status="SOFTWARE_TEST_ONLY",
            approved_design_path=design,
            approved_design_sha256=APPROVED_DESIGN_SHA256,
            panel_path=panel,
            panel_sha256=sha256_file(panel),
            run009_diagnostic_path=diagnostic,
            run009_diagnostic_sha256=sha256_file(diagnostic),
            source_manifest_path=source_manifest,
            source_manifest_sha256=sha256_file(source_manifest),
            sources=sources,
            features=FEATURES,
            factor_dimension=2,
            rolling_months=(96, 120, 144),
            panel_start="month-2002-01",
            panel_end=cls._month(months - 1),
            common_origin_start="month-2014-02",
            common_origin_end=cls._month(months - 1),
            development_start="month-2002-01",
            development_end="month-2011-12",
            geometry_references=GeometryReferences(0.75, 0.90, 0.35, 0.35, 0.20, 1.00, 0.50),
            bootstrap=BootstrapContract(19, 10092026, 12, (24, 36)),
            outcomes_accessed=False,
            synthetic_observations_allowed=False,
            run_010_execution_authorized=True,
            transmission_outcome_execution_authorized=False,
        )
        matrix = load_monthly_matrix(panel, FEATURES)
        geometry = _geometry_rows(
            matrix.values, matrix.month_ids, matrix.cutoff_timestamps, "point_in_time", config
        )
        fields = (
            "month_id",
            "panel_variant",
            "rolling_months",
            "second_principal_cosine",
            "normalized_projector_distance",
            "gram_spectral_distance",
            "gram_normalized_frobenius_distance",
            "expanding_relative_eigengap",
            "rolling_relative_eigengap",
            "perturbation_to_minimum_eigengap_ratio",
            "core_breach",
        )
        with diagnostic.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for row in geometry:
                writer.writerow({field: getattr(row, field) for field in fields})
        return replace(
            config,
            run009_diagnostic_sha256=sha256_file(diagnostic),
        )

    def test_run_is_deterministic_complete_outcome_blind_and_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as directory_text:
            directory = Path(directory_text)
            config = self._config(directory)
            first = run_run010(config)
            second = run_run010(config)
            self.assertEqual(first, second)
            self.assertEqual(len(first.comparison_rows), 680)
            self.assertEqual(len(first.geometry_rows), 1470)
            self.assertTrue(first.audit["missingness_mask_exactly_preserved"])
            self.assertTrue(first.audit["point_in_time_geometry_exactly_reproduced"])
            self.assertFalse(first.audit["outcomes_accessed"])
            self.assertTrue(first.audit["synthetic_observations_used"])
            self.assertFalse(first.audit["transmission_estimation_authorized"])
            self.assertEqual(
                set(first.audit["value_revision_summary"]),
                {"hicp_yoy", "industrial_production_yoy", "unemployment_rate"},
            )
            output = directory / "output"
            paths = tuple(
                output / name
                for name in ("comparison.csv", "geometry.csv", "episodes.csv", "audit.json")
            )
            write_run010_outputs(first, *paths)
            self.assertFalse(any(output.rglob("*.part")))
            with self.assertRaisesRegex(Run010Error, "immutable"):
                write_run010_outputs(first, *paths)

    def test_source_mutation_and_coverage_anomalies_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory_text:
            directory = Path(directory_text)
            config = self._config(directory)
            source = config.sources["hicp_yoy"]
            source.path.write_text(source.path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaisesRegex(Run010Error, "source changed"):
                run_run010(config)

            repaired = self._config(directory / "repaired")
            ip_source = repaired.sources["industrial_production_yoy"]
            with ip_source.path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            rows = [row for row in rows if row["TIME_PERIOD"] != "2016-02"]
            with ip_source.path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            changed = replace(
                ip_source,
                sha256=sha256_file(ip_source.path),
                bytes=ip_source.path.stat().st_size,
            )
            hostile = replace(
                repaired,
                sources={**repaired.sources, "industrial_production_yoy": changed},
            )
            with self.assertRaisesRegex(Run010Error, "lacks required period"):
                run_run010(hostile)

    def test_config_loader_binds_exact_approved_source_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory_text:
            directory = Path(directory_text)
            fixture = self._config(directory / "fixture")
            proposal = yaml.safe_load(fixture.approved_design_path.read_text(encoding="utf-8"))
            approved_sources = proposal["proposed_latest_vintage_sources"]["series"]
            filenames = {
                "hicp_yoy": "run010_latest_hicp.csv",
                "industrial_production_yoy": "run010_latest_ip.csv",
                "unemployment_rate": "run010_latest_unemployment.csv",
            }
            source_records = {}
            for feature, source in fixture.sources.items():
                target = directory / "raw" / filenames[feature]
                target.parent.mkdir(parents=True, exist_ok=True)
                source.path.replace(target)
                approved = approved_sources[
                    {
                        "hicp_yoy": "hicp_index",
                        "industrial_production_yoy": "industrial_production_index",
                        "unemployment_rate": "unemployment_rate",
                    }[feature]
                ]
                source_records[feature] = {
                    "path": str(target),
                    "url": approved["url"],
                    "final_url": approved["url"],
                    "series_key": approved["series_key"],
                    "sha256": sha256_file(target),
                    "bytes": target.stat().st_size,
                    "retrieved_at_utc": "2026-10-04T00:00:00+00:00",
                    "attempts": [{"attempt": 1, "status": "success"}],
                }
            manifest = directory / "sources.yaml"
            manifest_payload = {
                "schema_version": 1,
                "manifest_id": "run010-latest-sources-v1",
                "approved_design_path": str(fixture.approved_design_path),
                "approved_design_sha256": APPROVED_DESIGN_SHA256,
                "evidence_status": "REAL_OFFICIAL_DATA_EX_POST_LATEST_VINTAGE",
                "outcomes_accessed": False,
                "sources": source_records,
            }
            manifest.write_text(yaml.safe_dump(manifest_payload, sort_keys=False), encoding="utf-8")
            config_payload = {
                "schema_version": 1,
                "experiment_id": fixture.experiment_id,
                "evidence_status": fixture.evidence_status,
                "approved_design_path": str(fixture.approved_design_path),
                "approved_design_sha256": APPROVED_DESIGN_SHA256,
                "panel_path": str(fixture.panel_path),
                "panel_sha256": fixture.panel_sha256,
                "run009_diagnostic_path": str(fixture.run009_diagnostic_path),
                "run009_diagnostic_sha256": fixture.run009_diagnostic_sha256,
                "source_manifest_path": str(manifest),
                "source_manifest_sha256": sha256_file(manifest),
                "features": list(FEATURES),
                "factor_dimension": 2,
                "rolling_months": [96, 120, 144],
                "panel_start": fixture.panel_start,
                "panel_end": fixture.panel_end,
                "common_origin_start": fixture.common_origin_start,
                "common_origin_end": fixture.common_origin_end,
                "development_start": fixture.development_start,
                "development_end": fixture.development_end,
                "geometry_references": {
                    field: getattr(fixture.geometry_references, field)
                    for field in fixture.geometry_references.__dataclass_fields__
                },
                "bootstrap": {
                    "replications": 19,
                    "random_seed": 10092026,
                    "primary_block_months": 12,
                    "sensitivity_block_months": [24, 36],
                },
                "outcomes_accessed": False,
                "synthetic_observations_allowed": False,
                "run_010_execution_authorized": True,
                "transmission_outcome_execution_authorized": False,
            }
            config_path = directory / "config.yaml"
            config_path.write_text(
                yaml.safe_dump(config_payload, sort_keys=False), encoding="utf-8"
            )
            loaded = load_run010_config(config_path)
            self.assertEqual(set(loaded.sources), set(SOURCE_SPECS))

            manifest_payload["sources"]["hicp_yoy"]["url"] = "https://example.test/substitute"
            manifest.write_text(yaml.safe_dump(manifest_payload, sort_keys=False), encoding="utf-8")
            config_payload["source_manifest_sha256"] = sha256_file(manifest)
            config_path.write_text(
                yaml.safe_dump(config_payload, sort_keys=False), encoding="utf-8"
            )
            with self.assertRaisesRegex(Run010Error, "provenance differs"):
                load_run010_config(config_path)

    @patch("shockbridge_state_risk.state.run010.time.sleep")
    @patch("shockbridge_state_risk.state.run010.download_https")
    def test_fetch_retries_only_approved_conditions_and_publishes_atomic_bundle(
        self, download, sleep
    ) -> None:
        calls = 0

        def retrieve(url: str, destination: Path, timeout_seconds: float) -> DownloadManifest:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise DownloadError("The read operation timed out")
            if "P_C_OV" in url:
                feature = "hicp_yoy"
            elif "I_XCONS" in url:
                feature = "industrial_production_yoy"
            else:
                feature = "unemployment_rate"
            self._write_latest_source(destination, feature, 2)
            return DownloadManifest(
                url,
                url,
                "2026-10-04T00:00:00+00:00",
                sha256_file(destination),
                destination.stat().st_size,
                str(destination),
            )

        download.side_effect = retrieve
        with tempfile.TemporaryDirectory() as directory_text:
            directory = Path(directory_text)
            raw = directory / "raw"
            manifest = directory / "manifest.yaml"
            payload = fetch_run010_sources(
                ROOT / "research/methodology/run_010_vintage_robustness_proposal_v1.yaml",
                raw,
                manifest,
            )
            self.assertTrue(manifest.is_file())
            self.assertEqual(set(payload["sources"]), set(SOURCE_SPECS))
            self.assertEqual(calls, 4)
            sleep.assert_called_once_with(5.0)
            self.assertFalse(any(directory.rglob("*.download")))
            self.assertFalse(any(directory.rglob("*.part")))

    @patch("shockbridge_state_risk.state.run010.time.sleep")
    @patch("shockbridge_state_risk.state.run010.download_https")
    def test_fetch_does_not_retry_terminal_http_error(self, download, sleep) -> None:
        download.side_effect = DownloadError("HTTP Error 404: Not Found")
        with tempfile.TemporaryDirectory() as directory_text:
            directory = Path(directory_text)
            with self.assertRaisesRegex(Run010Error, "without retry"):
                fetch_run010_sources(
                    ROOT / "research/methodology/run_010_vintage_robustness_proposal_v1.yaml",
                    directory / "raw",
                    directory / "manifest.yaml",
                )
            self.assertEqual(download.call_count, 1)
            sleep.assert_not_called()
            self.assertFalse(any(directory.rglob("*.download")))
            self.assertFalse(any(directory.rglob("*.part")))


if __name__ == "__main__":
    unittest.main()
