import tempfile
import unittest
from pathlib import Path

from shockbridge_state_risk.contracts import ContractError, audit_contract, load_contract

ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    @staticmethod
    def complete_contract() -> dict:
        return {
            "contract_id": "example",
            "status": "FROZEN",
            "region": "euro_area",
            "shock": {
                "primary_component": "target",
                "event_window": "press_release",
                "normalization": "one-unit factor shock",
            },
            "outcomes": {"primary": ["eurusd_return"]},
            "horizons": {"primary": "event_window"},
            "estimand": {"target": "conditional response"},
            "evaluation": {
                "development_block": "2002-2017",
                "calibration_block": "2018-2021",
                "final_block": "2022-2025",
            },
            "reliability": {"failure_event": "interval miss"},
            "rights": {"redistribution_status": "metadata_only"},
        }

    def test_repository_contract_is_deliberately_blocked(self) -> None:
        contract = load_contract(ROOT / "research" / "empirical_contract_v1.yaml")
        audit = audit_contract(contract)
        self.assertFalse(audit.ready_for_real_estimation)
        self.assertEqual(audit.declared_status, "BLOCKED")
        self.assertIn("required:evaluation.final_block", audit.blockers)
        self.assertNotIn("required:outcomes.primary", audit.blockers)

    def test_frozen_contract_with_tbd_fails_closed(self) -> None:
        contract = self.complete_contract()
        contract["outcomes"]["primary"] = "TBD"
        audit = audit_contract(contract)
        self.assertFalse(audit.ready_for_real_estimation)
        self.assertIn("status:FROZEN_WITH_UNRESOLVED_FIELDS", audit.blockers)

    def test_complete_frozen_contract_is_ready(self) -> None:
        audit = audit_contract(self.complete_contract())
        self.assertTrue(audit.ready_for_real_estimation)
        self.assertEqual(audit.blockers, ())

    def test_missing_nested_field_is_reported(self) -> None:
        contract = self.complete_contract()
        del contract["shock"]["event_window"]
        audit = audit_contract(contract)
        self.assertIn("required:shock.event_window", audit.blockers)

    def test_invalid_status_is_rejected(self) -> None:
        contract = self.complete_contract()
        contract["status"] = "READY"
        with self.assertRaises(ContractError):
            audit_contract(contract)

    def test_empty_contract_id_is_rejected(self) -> None:
        contract = self.complete_contract()
        contract["contract_id"] = ""
        with self.assertRaises(ContractError):
            audit_contract(contract)

    def test_non_mapping_yaml_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.yaml"
            path.write_text("- not\n- a\n- mapping\n", encoding="utf-8")
            with self.assertRaises(ContractError):
                load_contract(path)


if __name__ == "__main__":
    unittest.main()
