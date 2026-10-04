import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from shockbridge_state_risk.cli import main
from shockbridge_state_risk.data.download import DownloadManifest
from shockbridge_state_risk.data.ecb_events import EAMPDAudit, SheetAudit
from shockbridge_state_risk.data.state_panel import PanelAudit
from shockbridge_state_risk.state.replay import StateReplayResult
from shockbridge_state_risk.state.run007 import Run007Result
from shockbridge_state_risk.state.run008 import Run008Result
from shockbridge_state_risk.state.run009 import Run009Result
from shockbridge_state_risk.state.run009_amendment import Run009AmendmentResult
from shockbridge_state_risk.state.run010 import Run010Result

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_blocked_contract_returns_two_and_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(
                [
                    "audit-contract",
                    str(ROOT / "research" / "empirical_contract_v1.yaml"),
                ]
            )
        payload = json.loads(output.getvalue())
        self.assertEqual(result, 2)
        self.assertEqual(payload["declared_status"], "BLOCKED")

    def test_synthetic_replay_returns_zero_and_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(["synthetic-replay"])
        payload = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(payload["evidence_status"], "SYNTHETIC_ONLY")

    @patch("shockbridge_state_risk.cli.audit_ea_mpd")
    def test_event_workbook_audit_command(self, audit_ea_mpd) -> None:
        audit_ea_mpd.return_value = EAMPDAudit(
            sha256="a" * 64,
            bytes=10,
            workbook_last_update="date",
            sheets={"Press Release Window": SheetAudit(1, 2, "2020-01-01", "2020-01-01", 0, {})},
        )
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(["audit-ecb-events", "ea-mpd", "workbook.xlsx"])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue())["bytes"], 10)

    @patch("shockbridge_state_risk.cli.download_https")
    def test_event_workbook_fetch_command(self, download_https) -> None:
        download_https.return_value = DownloadManifest(
            source_url="https://example.test/source",
            final_url="https://example.test/final",
            retrieved_at_utc="2026-10-02T00:00:00+00:00",
            sha256="b" * 64,
            bytes=20,
            destination="workbook.xlsx",
        )
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(["fetch-ecb-events", "ea-empd", "workbook.xlsx"])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue())["bytes"], 20)

    @patch("shockbridge_state_risk.cli.run_design_grid")
    @patch("shockbridge_state_risk.cli.load_design_grid")
    def test_design_power_prints_json(self, load_design_grid, run_design_grid) -> None:
        load_design_grid.return_value = object()
        run_design_grid.return_value = {"evidence_status": "SYNTHETIC_DESIGN_ONLY"}
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(["design-power", "grid.yaml"])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue())["evidence_status"], "SYNTHETIC_DESIGN_ONLY")

    @patch("shockbridge_state_risk.cli.run_design_grid")
    @patch("shockbridge_state_risk.cli.load_design_grid")
    def test_design_power_writes_output_atomically(self, load_design_grid, run_design_grid) -> None:
        load_design_grid.return_value = object()
        run_design_grid.return_value = {"value": 1}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "results.json"
            output = io.StringIO()
            with redirect_stdout(output):
                result = main(["design-power", "grid.yaml", "--output", str(path)])
            self.assertEqual(result, 0)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"value": 1})
            self.assertEqual(output.getvalue().strip(), str(path))

    @patch("shockbridge_state_risk.cli.write_panel_csv")
    @patch("shockbridge_state_risk.cli.audit_panel")
    @patch("shockbridge_state_risk.cli.build_candidate_state_panel")
    @patch("shockbridge_state_risk.cli.load_source_registry")
    def test_state_panel_command_writes_audit_atomically(
        self,
        load_source_registry,
        build_candidate_state_panel,
        audit_panel,
        write_panel_csv,
    ) -> None:
        load_source_registry.return_value = {}
        build_candidate_state_panel.return_value = ()
        audit_panel.return_value = PanelAudit(1, 5, 5, {}, {}, 0, 0)
        with tempfile.TemporaryDirectory() as directory:
            audit_path = Path(directory) / "nested" / "audit.json"
            output = io.StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "build-state-panel",
                        "registry.yaml",
                        "panel.csv",
                        "--audit-output",
                        str(audit_path),
                    ]
                )
            self.assertEqual(result, 0)
            self.assertEqual(json.loads(audit_path.read_text(encoding="utf-8"))["features"], 5)
            write_panel_csv.assert_called_once_with((), Path("panel.csv"))

    @patch("shockbridge_state_risk.cli.write_replay_csv")
    @patch("shockbridge_state_risk.cli.run_state_replay")
    @patch("shockbridge_state_risk.cli.load_state_replay_config")
    def test_state_replay_command_writes_audit_atomically(
        self, load_config, run_replay, write_replay
    ) -> None:
        load_config.return_value = object()
        run_replay.return_value = StateReplayResult((), {"screening_pass": False})
        with tempfile.TemporaryDirectory() as directory:
            audit_path = Path(directory) / "audit.json"
            output = io.StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "state-replay",
                        "config.yaml",
                        "probabilities.csv",
                        "--audit-output",
                        str(audit_path),
                    ]
                )
            self.assertEqual(result, 0)
            self.assertFalse(json.loads(audit_path.read_text(encoding="utf-8"))["screening_pass"])
            write_replay.assert_called_once_with((), Path("probabilities.csv"))

    @patch("shockbridge_state_risk.cli.write_panel_csv")
    @patch("shockbridge_state_risk.cli.audit_panel")
    @patch("shockbridge_state_risk.cli.build_monthly_state_panel")
    @patch("shockbridge_state_risk.cli.load_source_registry")
    @patch("shockbridge_state_risk.cli.load_monthly_panel_config")
    def test_monthly_panel_command_records_audit(
        self,
        load_monthly_config,
        load_registry,
        build_monthly,
        audit_panel,
        write_panel,
    ) -> None:
        from datetime import date
        from types import SimpleNamespace

        load_monthly_config.return_value = SimpleNamespace(
            source_registry=Path("sources.yaml"),
            start=date(2002, 1, 1),
            end=date(2002, 2, 1),
            cutoff_rule="month_start_23_59_59_europe_berlin",
        )
        load_registry.return_value = {}
        build_monthly.return_value = ()
        audit_panel.return_value = PanelAudit(2, 4, 8, {}, {}, 0, 0)
        with tempfile.TemporaryDirectory() as directory:
            audit_path = Path(directory) / "monthly.json"
            result = main(
                [
                    "build-monthly-state-panel",
                    "config.yaml",
                    "monthly.csv",
                    "--audit-output",
                    str(audit_path),
                ]
            )
            self.assertEqual(result, 0)
            self.assertEqual(json.loads(audit_path.read_text())["events"], 2)
            write_panel.assert_called_once_with((), Path("monthly.csv"))

    @patch("shockbridge_state_risk.cli.write_run007_outputs")
    @patch("shockbridge_state_risk.cli.run_run007")
    @patch("shockbridge_state_risk.cli.load_run007_config")
    def test_run007_command_requires_and_routes_all_outputs(
        self, load_config, run, write_outputs
    ) -> None:
        load_config.return_value = object()
        result_object = Run007Result((), (), (), {})
        run.return_value = result_object
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(
                [
                    "run-state-redesign",
                    "config.yaml",
                    "--factor-output",
                    "factor.csv",
                    "--challenger-output",
                    "challenger.csv",
                    "--restart-output",
                    "restart.jsonl",
                    "--audit-output",
                    "audit.json",
                ]
            )
        self.assertEqual(result, 0)
        load_config.assert_called_once_with(Path("config.yaml"))
        run.assert_called_once_with(load_config.return_value)
        write_outputs.assert_called_once_with(
            result_object,
            Path("factor.csv"),
            Path("challenger.csv"),
            Path("restart.jsonl"),
            Path("audit.json"),
        )
        self.assertEqual(output.getvalue().strip(), "audit.json")

    @patch("shockbridge_state_risk.cli.write_run008_outputs")
    @patch("shockbridge_state_risk.cli.run_run008")
    @patch("shockbridge_state_risk.cli.load_run008_config")
    def test_run008_command_requires_and_routes_all_outputs(
        self, load_config, run, write_outputs
    ) -> None:
        load_config.return_value = object()
        result_object = Run008Result((), (), (), {})
        run.return_value = result_object
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(
                [
                    "run-state-subspace",
                    "config.yaml",
                    "--subspace-output",
                    "subspace.csv",
                    "--fixed-factor-output",
                    "fixed.csv",
                    "--two-factor-output",
                    "two.csv",
                    "--audit-output",
                    "audit.json",
                ]
            )
        self.assertEqual(result, 0)
        load_config.assert_called_once_with(Path("config.yaml"))
        run.assert_called_once_with(load_config.return_value)
        write_outputs.assert_called_once_with(
            result_object,
            Path("subspace.csv"),
            Path("fixed.csv"),
            Path("two.csv"),
            Path("audit.json"),
        )
        self.assertEqual(output.getvalue().strip(), "audit.json")

    @patch("shockbridge_state_risk.cli.write_run009_outputs")
    @patch("shockbridge_state_risk.cli.run_run009")
    @patch("shockbridge_state_risk.cli.load_run009_config")
    def test_run009_command_requires_and_routes_all_outputs(
        self, load_config, run, write_outputs
    ) -> None:
        load_config.return_value = object()
        result_object = Run009Result((), (), {})
        run.return_value = result_object
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(
                [
                    "run-state-instability",
                    "config.yaml",
                    "--diagnostic-output",
                    "diagnostic.csv",
                    "--episode-output",
                    "episodes.csv",
                    "--audit-output",
                    "audit.json",
                ]
            )
        self.assertEqual(result, 0)
        load_config.assert_called_once_with(Path("config.yaml"))
        run.assert_called_once_with(load_config.return_value)
        write_outputs.assert_called_once_with(
            result_object,
            Path("diagnostic.csv"),
            Path("episodes.csv"),
            Path("audit.json"),
        )
        self.assertEqual(output.getvalue().strip(), "audit.json")

    @patch("shockbridge_state_risk.cli.write_run009_amendment_outputs")
    @patch("shockbridge_state_risk.cli.run_run009_amendment")
    @patch("shockbridge_state_risk.cli.load_run009_amendment_config")
    def test_run009_amendment_routes_versioned_outputs(
        self, load_config, run, write_outputs
    ) -> None:
        load_config.return_value = object()
        result_object = Run009AmendmentResult((), {})
        run.return_value = result_object
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(
                [
                    "amend-state-instability-episodes",
                    "amendment.yaml",
                    "--episode-output",
                    "amended.csv",
                    "--audit-output",
                    "amendment.json",
                ]
            )
        self.assertEqual(result, 0)
        load_config.assert_called_once_with(Path("amendment.yaml"))
        run.assert_called_once_with(load_config.return_value)
        write_outputs.assert_called_once_with(
            result_object, Path("amended.csv"), Path("amendment.json")
        )
        self.assertEqual(output.getvalue().strip(), "amendment.json")

    @patch("shockbridge_state_risk.cli.fetch_run010_sources")
    def test_run010_fetch_routes_frozen_design_and_outputs(self, fetch) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(
                [
                    "fetch-run010-sources",
                    "design.yaml",
                    "raw",
                    "--manifest-output",
                    "sources.yaml",
                ]
            )
        self.assertEqual(result, 0)
        fetch.assert_called_once_with(Path("design.yaml"), Path("raw"), Path("sources.yaml"))
        self.assertEqual(output.getvalue().strip(), "sources.yaml")

    @patch("shockbridge_state_risk.cli.write_run010_outputs")
    @patch("shockbridge_state_risk.cli.run_run010")
    @patch("shockbridge_state_risk.cli.load_run010_config")
    def test_run010_command_requires_and_routes_complete_bundle(
        self, load_config, run, write_outputs
    ) -> None:
        load_config.return_value = object()
        result_object = Run010Result((), (), (), {})
        run.return_value = result_object
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(
                [
                    "run-vintage-robustness",
                    "config.yaml",
                    "--comparison-output",
                    "comparison.csv",
                    "--geometry-output",
                    "geometry.csv",
                    "--episode-output",
                    "episodes.csv",
                    "--audit-output",
                    "audit.json",
                ]
            )
        self.assertEqual(result, 0)
        load_config.assert_called_once_with(Path("config.yaml"))
        run.assert_called_once_with(load_config.return_value)
        write_outputs.assert_called_once_with(
            result_object,
            Path("comparison.csv"),
            Path("geometry.csv"),
            Path("episodes.csv"),
            Path("audit.json"),
        )
        self.assertEqual(output.getvalue().strip(), "audit.json")


if __name__ == "__main__":
    unittest.main()
