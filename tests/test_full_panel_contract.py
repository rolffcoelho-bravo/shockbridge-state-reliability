import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from shockbridge_state_risk.data.full_panel_contract import (
    FullPanelContractError,
    audit_full_panel_contract,
    write_full_panel_contract_audit,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/methodology/run_021_full_panel_build_protocol_v1.yaml"
MANIFEST = ROOT / "research/data/run_021_full_panel_manifest_v1.yaml"


class FullPanelContractTests(unittest.TestCase):
    def _fixture(self, directory: str) -> tuple[Path, Path, Path]:
        root = Path(directory)
        (root / "pyproject.toml").write_text("[project]\nname='run021-fixture'\n", encoding="utf-8")
        protocol = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
        paths = {str(item["path"]) for item in protocol["bound_inputs"]}
        paths.add("research/methodology/run_021_full_panel_build_protocol_v1.yaml")
        for relative in paths:
            source = ROOT / relative
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        return (
            root,
            root / "research/methodology/run_021_full_panel_build_protocol_v1.yaml",
            root / "research/data/run_021_full_panel_manifest_v1.yaml",
        )

    def _write_yaml(self, path: Path, payload: dict) -> None:
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    def _rehash_manifest(self, protocol_path: Path, manifest_path: Path) -> None:
        protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        for item in protocol["bound_inputs"]:
            if item["path"] == "research/data/run_021_full_panel_manifest_v1.yaml":
                item["sha256"] = digest
        self._write_yaml(protocol_path, protocol)

    def test_registered_contract_is_value_free_complete_and_matured(self) -> None:
        audit = audit_full_panel_contract(PROTOCOL, MANIFEST)
        self.assertTrue(audit.passed)
        self.assertEqual(audit.series_count, 10)
        self.assertEqual(audit.panel_count, 2)
        self.assertEqual(audit.channel_count, 7)
        self.assertEqual(audit.maximum_scenarios_before_deduplication, 56)
        self.assertTrue(audit.evaluation_labels_matured)
        self.assertFalse(audit.full_history_retrieval_performed)
        self.assertFalse(audit.state_estimation_performed)
        self.assertFalse(audit.transmission_outcomes_accessed)
        self.assertFalse(audit.synthetic_empirical_observations_used)

    def test_writer_is_immutable_and_atomic(self) -> None:
        audit = audit_full_panel_contract(PROTOCOL, MANIFEST)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "audit.json"
            write_full_panel_contract_audit(audit, output)
            self.assertIn('"passed": true', output.read_text(encoding="utf-8"))
            self.assertEqual(list(Path(directory).glob("*.part")), [])
            with self.assertRaisesRegex(FullPanelContractError, "refusing to overwrite"):
                write_full_panel_contract_audit(audit, output)

    def test_bound_input_mutation_fails_before_design_use(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, protocol_path, manifest_path = self._fixture(directory)
            source = root / "research/data/run_019_channel_architecture_v1.yaml"
            source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaisesRegex(FullPanelContractError, "bound input hash mismatch"):
                audit_full_panel_contract(protocol_path, manifest_path)

    def test_scientific_boundaries_fail_closed(self) -> None:
        mutations = [
            ("real_official", "real_official_data_only", False),
            ("synthetic_empirical", "synthetic_empirical_observations_allowed", True),
            ("transmission", "transmission_outcomes_access_allowed", True),
            ("full_history", "full_history_retrieval_allowed_in_run_021", True),
            ("state_estimation", "state_estimation_allowed_in_run_021", True),
        ]
        for message, field, value in mutations:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                _, protocol_path, manifest_path = self._fixture(directory)
                protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
                protocol["scientific_boundary"][field] = value
                self._write_yaml(protocol_path, protocol)
                with self.assertRaisesRegex(FullPanelContractError, message):
                    audit_full_panel_contract(protocol_path, manifest_path)

    def test_manifest_requires_separate_approval_and_pending_hashes(self) -> None:
        mutations = [
            (
                "separate_owner_approval",
                lambda payload: payload["retrieval_contract"].update(
                    next_stage_requires_separate_owner_approval=False
                ),
            ),
            (
                "pre-retrieval response hashes",
                lambda payload: payload["retrieval_contract"].update(
                    response_hash_state_before_retrieval="made-up"
                ),
            ),
            (
                "pre-retrieval hash",
                lambda payload: payload["series"][0].update(response_sha256="0" * 64),
            ),
        ]
        for message, mutate in mutations:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
                _, protocol_path, manifest_path = self._fixture(directory)
                manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
                mutate(manifest)
                self._write_yaml(manifest_path, manifest)
                self._rehash_manifest(protocol_path, manifest_path)
                with self.assertRaisesRegex(FullPanelContractError, message):
                    audit_full_panel_contract(protocol_path, manifest_path)

    def test_query_metadata_and_release_hosts_are_exact(self) -> None:
        mutations = [
            (
                "query period differs",
                lambda payload: payload["series"][0].update(
                    query_url=payload["series"][0]["query_url"].replace(
                        "startPeriod=2002-01", "startPeriod=2003-01"
                    )
                ),
            ),
            (
                "metadata differs",
                lambda payload: payload["series"][0].update(unit="PC"),
            ),
            (
                "official HTTPS host",
                lambda payload: payload["release_sources"].update(
                    rtd_information="https://example.com/rtd"
                ),
            ),
            (
                "sign must be exactly",
                lambda payload: payload["series"][0].update(sign=True),
            ),
        ]
        for message, mutate in mutations:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
                _, protocol_path, manifest_path = self._fixture(directory)
                manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
                mutate(manifest)
                self._write_yaml(manifest_path, manifest)
                self._rehash_manifest(protocol_path, manifest_path)
                with self.assertRaisesRegex(FullPanelContractError, message):
                    audit_full_panel_contract(protocol_path, manifest_path)

    def test_panels_cannot_depart_from_accepted_pilot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _, protocol_path, manifest_path = self._fixture(directory)
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            manifest["panels"][1]["series_ids"].remove("BSI_MONETARY_AGGREGATE_M3")
            self._write_yaml(manifest_path, manifest)
            self._rehash_manifest(protocol_path, manifest_path)
            with self.assertRaisesRegex(FullPanelContractError, "accepted pilot panel"):
                audit_full_panel_contract(protocol_path, manifest_path)

    def test_scenario_count_and_label_maturity_are_recomputed(self) -> None:
        mutations = [
            (
                "maximum scenarios",
                lambda payload: payload["admissible_information_set_generator"].update(
                    maximum_scenarios_before_deduplication=112
                ),
            ),
            (
                "12-month evaluation label",
                lambda payload: payload["chronological_validation"].update(
                    evaluation_end="2025-10"
                ),
            ),
        ]
        for message, mutate in mutations:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
                _, protocol_path, manifest_path = self._fixture(directory)
                protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
                mutate(protocol)
                self._write_yaml(protocol_path, protocol)
                with self.assertRaisesRegex(FullPanelContractError, message):
                    audit_full_panel_contract(protocol_path, manifest_path)

    def test_bound_input_path_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _, protocol_path, manifest_path = self._fixture(directory)
            protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
            protocol["bound_inputs"][0]["path"] = "../../outside.yaml"
            self._write_yaml(protocol_path, protocol)
            with self.assertRaisesRegex(FullPanelContractError, "escapes the project root"):
                audit_full_panel_contract(protocol_path, manifest_path)


if __name__ == "__main__":
    unittest.main()
