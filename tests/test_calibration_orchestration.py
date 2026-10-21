import ast
import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import yaml

import shockbridge_state_risk.state.calibration_orchestration as orchestration_module
from shockbridge_state_risk.state.calibration_orchestration import (
    PIPELINE_OPERATIONS,
    REVISION_EXPOSURE,
    TIMING_STRENGTH,
    B2Member,
    CalibrationOrchestrationError,
    SeriesDescriptor,
    assess_calibration_analogue,
    combine_b2_history,
    deduplicate_scenario_identities,
    encode_month,
    evaluation_identity_payload,
    expected_calibration_months,
    fit_projected_observed_stable_pcp,
    orchestration_surface,
    prepare_history,
    scenario_identity,
    validate_and_serialize_calibration_ledger,
    validate_calibration_lock_body,
    validate_pipeline_trace,
    validate_run029_approval,
    write_complete_calibration_lock,
)

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "research/methodology/run_029_stage_A_orchestration_amendment_proposal_v1.yaml"
APPROVAL = ROOT / "research/methodology/run_030_stage_A_orchestration_amendment_approval_v1.yaml"


def descriptors() -> tuple[SeriesDescriptor, ...]:
    return (
        SeriesDescriptor(
            "HICP",
            "prices",
            "A_REPLAY_ELIGIBLE",
            "archived_policy_concept_vintages",
            "2003-01",
            0,
            1,
        ),
        SeriesDescriptor(
            "HICP_DUP",
            "prices",
            "B_RELEASE_LAG_ELIGIBLE",
            "current_history_shifted_to_verified_release_calendar",
            "2003-02",
            1,
            1,
        ),
        SeriesDescriptor(
            "IP",
            "activity",
            "A_REPLAY_ELIGIBLE",
            "archived_policy_concept_vintages",
            "2003-01",
            2,
            1,
        ),
        SeriesDescriptor(
            "DFR",
            "policy",
            "A_REPLAY_ELIGIBLE",
            "dated_effective_rate_with_history_timestamp",
            "2003-01",
            3,
            1,
        ),
        SeriesDescriptor(
            "FX",
            "external",
            "B_RELEASE_LAG_ELIGIBLE",
            "nonrevisable_dated_reference_rate_assumption_to_be_audited",
            "2003-01",
            4,
            -1,
        ),
    )


def fixture(rows: int = 150) -> np.ndarray:
    index = np.arange(rows, dtype=np.float64)
    base = np.column_stack(
        (
            np.sin(index / 7.0) + index / 50.0,
            np.sin(index / 7.0) + index / 50.0,
            np.cos(index / 11.0) + index / 80.0,
            np.sin(index / 17.0) - index / 120.0,
            np.cos(index / 5.0) + index / 100.0,
        )
    )
    return np.asarray(base, dtype=np.float64)


def lock_body() -> dict[str, object]:
    return {
        "stage": "calibration_lock",
        "approved_amendment_sha256": "a" * 64,
        "implementation_identity": {
            "git_commit": "b" * 40,
            "orchestrator_sha256": "c" * 64,
            "harness_sha256": "d" * 64,
            "protocol_sha256": "e" * 64,
            "run027_amendment_sha256": "f" * 64,
        },
        "required_counts": {
            "calibration_origins": 60,
            "embargo_months": 12,
            "evaluation_origins": 70,
        },
        "selected_settings": {
            "primary_threshold": {},
            "B1_cutoff_and_matched_participation_cutoff": {},
            "B2_cutoff_and_matched_participation_cutoff": {},
            "B3_lambda_cutoff_and_matched_participation_cutoff": {},
            "NC1_NC2_NC3_frozen_settings": {},
        },
        "calibration_metrics": {
            "candidate_grid_count": 144,
            "participation": 0.2,
            "decision_loss": 0.2,
            "future_failure_prevalence": 0.1,
            "authorized_future_failure_rate": 0.0,
            "nondegenerate_scenario_count_distribution": {},
            "comparator_metrics": {},
            "negative_control_metrics": {},
        },
        "calibration_origin_ledger_sha256": "1" * 64,
        "evaluation_identity_map_sha256": "2" * 64,
        "exact_input_hashes": {"panel": "3" * 64},
        "invariance_results": {"passed": True},
    }


class CalibrationOrchestrationTests(unittest.TestCase):
    """Hostile fixtures only; no fixture value is empirical evidence."""

    def test_exact_approval_is_bound_and_firewalls_are_closed(self) -> None:
        digest = validate_run029_approval(APPROVAL, PROPOSAL)
        self.assertEqual(
            digest,
            "723e00e5bbaa701698ff59a149a68de37bedda6268e76e624524d0e142b04a9b",
        )
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "proposal.yaml"
            changed.write_bytes(PROPOSAL.read_bytes() + b"\n")
            with self.assertRaisesRegex(CalibrationOrchestrationError, "byte identity"):
                validate_run029_approval(APPROVAL, changed)

    def test_pipeline_order_is_exact_and_permutations_fail(self) -> None:
        validate_pipeline_trace(PIPELINE_OPERATIONS)
        changed = list(PIPELINE_OPERATIONS)
        changed[5], changed[6] = changed[6], changed[5]
        with self.assertRaisesRegex(CalibrationOrchestrationError, "frozen order"):
            validate_pipeline_trace(changed)

    def test_categorical_maps_are_complete_and_month_encoding_is_exact(self) -> None:
        self.assertEqual(set(TIMING_STRENGTH), {"A_REPLAY_ELIGIBLE", "B_RELEASE_LAG_ELIGIBLE"})
        self.assertEqual(len(REVISION_EXPOSURE), 5)
        self.assertEqual(encode_month("2026-10"), 2026 * 12 + 9)
        with self.assertRaisesRegex(CalibrationOrchestrationError, "YYYY-MM"):
            encode_month("2026-13")

    def test_histories_select_independently_and_identity_allows_different_columns(self) -> None:
        expanding_values = fixture()
        expanding_values[:25, 4] = np.nan
        rolling_values = fixture(120)
        rolling_values[:, 4] = np.nan
        expanding = prepare_history(expanding_values, descriptors())
        rolling = prepare_history(rolling_values, descriptors())
        self.assertIn("FX", expanding.retained_series_ids)
        self.assertNotIn("FX", rolling.retained_series_ids)
        self.assertIn(("HICP", "HICP_DUP"), expanding.exact_components)
        identity = scenario_identity("panel__clock__timing__missing__family", expanding, rolling)
        self.assertEqual(len(identity.sha256), 64)
        self.assertNotEqual(expanding.standardized.shape[1], rolling.standardized.shape[1])

    def test_identity_deduplication_uses_lexical_representative(self) -> None:
        values = fixture()
        history = prepare_history(values, descriptors())
        first = scenario_identity(
            "z_provenance", history, prepare_history(values[-120:], descriptors())
        )
        second = scenario_identity(
            "a_provenance", history, prepare_history(values[-120:], descriptors())
        )
        # Provenance IDs are part of the registered identity; emulate equal analytic paths
        # by using the same identity digest while retaining both labels.
        second = type(second)(second.full_scenario_id, first.payload, first.sha256)
        representatives, mapping = deduplicate_scenario_identities((first, second))
        self.assertEqual(representatives[first.sha256].full_scenario_id, "a_provenance")
        self.assertEqual(mapping["z_provenance"], "a_provenance")

    def test_b2_is_duplicate_neutral_and_projector_rotation_invariant(self) -> None:
        scalar_a = np.linspace(-1.0, 1.0, 120)
        scalar_b = np.cos(np.arange(120) / 10.0)
        loading = np.asarray([[1.0, 0.0], [0.0, 1.0], [0.4, 0.2]])
        rotation, _ = np.linalg.qr(np.asarray([[1.0, 2.0], [2.0, -1.0]]))
        projector = loading @ np.linalg.pinv(loading)
        rotated_projector = (loading @ rotation) @ np.linalg.pinv(loading @ rotation)
        members = (
            B2Member("A", scalar_a, projector, 0.8),
            B2Member("B", scalar_b, rotated_projector, 0.6),
        )
        base = combine_b2_history(members)
        duplicate = combine_b2_history((*members, members[0]))
        self.assertTrue(
            np.allclose(base.standardized_anchor_scalar, duplicate.standardized_anchor_scalar)
        )
        self.assertTrue(np.allclose(base.channel_operator, duplicate.channel_operator, atol=1e-12))
        self.assertAlmostEqual(base.mean_anchor_capture, 0.7)

    def test_projected_pcp_does_not_force_missing_cells_to_observed_zero(self) -> None:
        row = np.arange(1.0, 13.0)[:, None]
        values = row @ np.asarray([[1.0, 0.5, -0.25, 0.8]])
        values[3:9, 1] = np.nan
        fit = fit_projected_observed_stable_pcp(values)
        missing = ~np.isfinite(values)
        self.assertTrue(fit.converged)
        self.assertTrue(np.all(fit.sparse[missing] == 0.0))
        self.assertGreater(float(np.linalg.norm(fit.low_rank[missing])), 0.1)
        observed = np.isfinite(values)
        self.assertTrue(
            np.allclose((fit.low_rank + fit.sparse)[observed], values[observed], atol=1e-6)
        )

    def test_stage_A_analogue_uses_only_sixty_calibration_origins(self) -> None:
        actions = np.asarray([True] * 12 + [False] * 48)
        labels = np.asarray([False] * 60)
        counts = np.asarray([2] * 60)
        result = assess_calibration_analogue(actions, labels, counts)
        self.assertTrue(result.passed)
        self.assertAlmostEqual(result.participation, 0.2)
        with self.assertRaisesRegex(CalibrationOrchestrationError, "60 origins"):
            assess_calibration_analogue(actions[:-1], labels[:-1], counts[:-1])

    def test_evaluation_identity_has_no_fit_metric_or_label_field(self) -> None:
        payload = {
            "origin_month": "2019-01",
            "full_scenario_id": "scenario",
            "analytic_representative_id": "representative",
            "provenance_member_ids": ["scenario"],
            "expanding_ordered_retained_series_ids": ["A"],
            "expanding_eligibility_mask_hash": "a" * 64,
            "expanding_standardized_matrix_hash": "b" * 64,
            "rolling_ordered_retained_series_ids": ["A"],
            "rolling_eligibility_mask_hash": "c" * 64,
            "rolling_standardized_matrix_hash": "d" * 64,
        }
        encoded, digest = evaluation_identity_payload(payload)
        self.assertEqual(
            encoded, json.dumps(payload, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        )
        self.assertEqual(digest, hashlib.sha256(encoded).hexdigest())
        with self.assertRaisesRegex(CalibrationOrchestrationError, "fitted"):
            evaluation_identity_payload({**payload, "loss_metric": 0.1})

    def test_calibration_ledger_is_exactly_sixty_complete_matured_origins(self) -> None:
        rows = []
        for month in expected_calibration_months():
            rows.append(
                {
                    "origin_month": month,
                    "matured_future_failure_label": False,
                    "analytic_scenario_count": 2,
                    "provenance_to_analytic_mapping": {},
                    "scenario_representatives_and_failure_reasons": {},
                    "envelope_statistics": {},
                    "candidate_authorization_vector_hash": "a" * 64,
                    "B1_B2_B3_candidate_authorization_vector_hashes": {"B1": "b" * 64},
                    "negative_control_candidate_vector_hashes": {"NC1": "c" * 64},
                    "selected_primary_and_comparator_decisions": {},
                }
            )
        serialized = validate_and_serialize_calibration_ledger(rows)
        self.assertEqual(serialized.count(b"\n"), 60)
        with self.assertRaisesRegex(CalibrationOrchestrationError, "60 rows"):
            validate_and_serialize_calibration_ledger(rows[:-1])

    def test_complete_lock_schema_is_required_before_atomic_creation(self) -> None:
        body = lock_body()
        validate_calibration_lock_body(body)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stage_A.lock.json"
            digest = write_complete_calibration_lock(path, body)
            self.assertEqual(json.loads(path.read_text())["stage_A_sha256"], digest)
            with self.assertRaisesRegex(CalibrationOrchestrationError, "overwrite"):
                write_complete_calibration_lock(path, body)
        incomplete = dict(body)
        incomplete.pop("calibration_origin_ledger_sha256")
        with self.assertRaisesRegex(CalibrationOrchestrationError, "incomplete"):
            validate_calibration_lock_body(incomplete)

    def test_all_nine_resolutions_exist_without_forbidden_imports_or_execution(self) -> None:
        surface = orchestration_surface()
        self.assertEqual(
            {key for key in surface if key.startswith("OG-")},
            {f"OG-{index:02d}" for index in range(1, 10)},
        )
        self.assertFalse(surface["official_fit_performed"])
        self.assertFalse(surface["evaluation_fit_or_label_accessed"])
        source = inspect.getsource(orchestration_module)
        tree = ast.parse(source)
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertFalse(any("transmission" in name or "outcome" in name for name in imported))

    def test_hostile_orchestration_inputs_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = yaml.safe_load(APPROVAL.read_text())
            variants = (
                ({**base, "status": "NOT_APPROVED"}, "not approved"),
                ({**base, "approval_scope": {}}, "scope"),
                ({**base, "still_prohibited": {}}, "firewall"),
            )
            for index, (payload, message) in enumerate(variants):
                path = root / f"approval-{index}.yaml"
                path.write_text(yaml.safe_dump(payload, sort_keys=False))
                with self.assertRaisesRegex(CalibrationOrchestrationError, message):
                    validate_run029_approval(path, PROPOSAL)

        values = fixture()
        with self.assertRaisesRegex(CalibrationOrchestrationError, "align"):
            prepare_history(values[:, :-1], descriptors())
        duplicated = list(descriptors())
        duplicated[-1] = duplicated[0]
        with self.assertRaisesRegex(CalibrationOrchestrationError, "unique"):
            prepare_history(values, duplicated)
        with self.assertRaisesRegex(CalibrationOrchestrationError, "No history"):
            prepare_history(np.ones_like(values), descriptors())
        invalid_descriptor = list(descriptors())
        invalid_descriptor[0] = SeriesDescriptor(
            "HICP",
            "prices",
            "UNKNOWN",
            "archived_policy_concept_vintages",
            "2003-01",
            0,
            1,
        )
        with self.assertRaisesRegex(CalibrationOrchestrationError, "categorical"):
            prepare_history(values, invalid_descriptor)

        history = prepare_history(values, descriptors())
        rolling = prepare_history(values[-120:], descriptors())
        with self.assertRaisesRegex(CalibrationOrchestrationError, "histories"):
            scenario_identity("", history, rolling)

        scalar = np.arange(120, dtype=np.float64)
        projector = np.eye(2)
        one = B2Member("A", scalar, projector, 0.8)
        with self.assertRaisesRegex(CalibrationOrchestrationError, "at least two"):
            combine_b2_history((one,))
        inconsistent = B2Member("A", scalar + 1.0, projector, 0.8)
        with self.assertRaisesRegex(CalibrationOrchestrationError, "inconsistent"):
            combine_b2_history((one, inconsistent))
        other_shape = B2Member("B", scalar[:-1], projector, 0.7)
        with self.assertRaisesRegex(CalibrationOrchestrationError, "common spaces"):
            combine_b2_history((one, other_shape))
        nonfinite = B2Member("B", scalar, projector, float("nan"))
        with self.assertRaisesRegex(CalibrationOrchestrationError, "nonfinite"):
            combine_b2_history((one, nonfinite))

        with self.assertRaisesRegex(CalibrationOrchestrationError, "matrix"):
            fit_projected_observed_stable_pcp(np.ones(3))
        with self.assertRaisesRegex(CalibrationOrchestrationError, "controls"):
            fit_projected_observed_stable_pcp(np.eye(3), lambda_multiplier=3.0)
        with self.assertRaisesRegex(CalibrationOrchestrationError, "did not converge"):
            hard = np.random.default_rng(30).normal(size=(8, 5))
            hard[1, 2] = np.nan
            fit_projected_observed_stable_pcp(hard, tolerance=1e-30, maximum_iterations=1)

        failed = assess_calibration_analogue(
            np.zeros(60, dtype=np.bool_),
            np.zeros(60, dtype=np.bool_),
            np.ones(60, dtype=np.int64),
        )
        self.assertEqual(
            failed.failures,
            (
                "participation_below_0_10",
                "authorized_origin_has_fewer_than_two_scenarios",
            ),
        )

    def test_hostile_ledger_and_lock_fields_fail_closed(self) -> None:
        identity = {
            "origin_month": "2019-01",
            "full_scenario_id": "scenario",
            "analytic_representative_id": "representative",
            "provenance_member_ids": ["scenario"],
            "expanding_ordered_retained_series_ids": ["A"],
            "expanding_eligibility_mask_hash": "bad",
            "expanding_standardized_matrix_hash": "b" * 64,
            "rolling_ordered_retained_series_ids": ["A"],
            "rolling_eligibility_mask_hash": "c" * 64,
            "rolling_standardized_matrix_hash": "d" * 64,
        }
        with self.assertRaisesRegex(CalibrationOrchestrationError, "hash is invalid"):
            evaluation_identity_payload(identity)

        rows = []
        for month in expected_calibration_months():
            rows.append(
                {
                    "origin_month": month,
                    "matured_future_failure_label": False,
                    "analytic_scenario_count": 2,
                    "provenance_to_analytic_mapping": {},
                    "scenario_representatives_and_failure_reasons": {},
                    "envelope_statistics": {},
                    "candidate_authorization_vector_hash": "a" * 64,
                    "B1_B2_B3_candidate_authorization_vector_hashes": {"B1": "b" * 64},
                    "negative_control_candidate_vector_hashes": {"NC1": "c" * 64},
                    "selected_primary_and_comparator_decisions": {},
                }
            )
        unordered = [dict(row) for row in rows]
        unordered[0]["origin_month"] = "2013-02"
        with self.assertRaisesRegex(CalibrationOrchestrationError, "unordered"):
            validate_and_serialize_calibration_ledger(unordered)
        wrong_schema = [dict(row) for row in rows]
        wrong_schema[0]["matured_future_failure_label"] = 0
        with self.assertRaisesRegex(CalibrationOrchestrationError, "schema"):
            validate_and_serialize_calibration_ledger(wrong_schema)
        wrong_count = [dict(row) for row in rows]
        wrong_count[0]["analytic_scenario_count"] = -1
        with self.assertRaisesRegex(CalibrationOrchestrationError, "scenario count"):
            validate_and_serialize_calibration_ledger(wrong_count)
        wrong_hash = [dict(row) for row in rows]
        wrong_hash[0]["candidate_authorization_vector_hash"] = "bad"
        with self.assertRaisesRegex(CalibrationOrchestrationError, "invalid hash"):
            validate_and_serialize_calibration_ledger(wrong_hash)

        mutations = (
            ("implementation_identity", {}, "identity"),
            (
                "implementation_identity",
                {**lock_body()["implementation_identity"], "git_commit": "bad"},
                "commit",
            ),
            ("exact_input_hashes", {}, "input hashes"),
            ("approved_amendment_sha256", "bad", "SHA-256"),
            ("required_counts", {}, "counts"),
            ("selected_settings", {}, "settings"),
            ("calibration_metrics", {}, "metrics"),
        )
        for field, value, message in mutations:
            body = lock_body()
            body[field] = value
            with self.assertRaisesRegex(CalibrationOrchestrationError, message):
                validate_calibration_lock_body(body)


if __name__ == "__main__":
    unittest.main()
