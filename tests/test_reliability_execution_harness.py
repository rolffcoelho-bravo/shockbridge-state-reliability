import ast
import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import shockbridge_state_risk.state.reliability_execution_harness as harness_module
from shockbridge_state_risk.state.reliability_engine import channel_projector, score_projector
from shockbridge_state_risk.state.reliability_execution_harness import (
    HistoryFitSummary,
    PanelCell,
    ReliabilityExecutionHarnessError,
    SeriesRedundancyMetadata,
    ThresholdCandidate,
    apply_slow_release_stress,
    assess_negative_controls,
    build_origin_matrix,
    cyclic_shift_within_blocks,
    evaluate_within_scenario_gate,
    fit_observed_stable_pcp,
    implementation_surface,
    make_noncircular_block_plan,
    match_calibration_participation,
    permute_label_blocks,
    rank_invariant_anchor_state,
    recover_complete_case_scores,
    resolve_near_duplicates,
    rotate_series_channel_assignments,
    scenario_history_key,
    select_calibration_threshold,
    simultaneous_bootstrap_intervals,
    start_evaluation_once,
    validate_approved_amendment,
    write_calibration_lock,
)

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "research/methodology/run_027_reliability_execution_amendment_proposal_v1.yaml"
APPROVAL = ROOT / "research/methodology/run_028_reliability_execution_amendment_approval_v1.yaml"


class ReliabilityExecutionHarnessTests(unittest.TestCase):
    """Hostile software fixtures only; no fixture is empirical evidence."""

    def test_approved_amendment_is_exact_and_firewalls_remain_closed(self) -> None:
        digest = validate_approved_amendment(APPROVAL, PROPOSAL)
        self.assertEqual(
            digest,
            "cda763f5102d6491dfce4d3b0687cf5729089e156cf2cac59be716fb04655899",
        )
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "proposal.yaml"
            changed.write_bytes(PROPOSAL.read_bytes() + b"\n")
            with self.assertRaisesRegex(ReliabilityExecutionHarnessError, "byte identity changed"):
                validate_approved_amendment(APPROVAL, changed)

    def test_origin_matrix_and_slow_release_shift_values_metadata_and_masks(self) -> None:
        cells = (
            PanelCell("2020-01", "A", 1.0, "2019-12"),
            PanelCell("2020-02", "A", None, "", "not_released"),
            PanelCell("2020-03", "A", 3.0, "2020-02"),
            PanelCell("2020-01", "B", 10.0, "2020-01"),
            PanelCell("2020-02", "B", 11.0, "2020-02"),
            PanelCell("2020-03", "B", 12.0, "2020-03"),
        )
        matrix = build_origin_matrix(cells, ("2020-01", "2020-02", "2020-03"), ("A", "B"))
        shifted = apply_slow_release_stress(matrix, ("A",))
        self.assertTrue(np.isnan(shifted.values[0, 0]))
        self.assertEqual(shifted.missing_reasons[0][0], "slow_release_boundary")
        self.assertEqual(shifted.values[1, 0], 1.0)
        self.assertEqual(shifted.observation_periods[1][0], "2019-12")
        self.assertTrue(np.isnan(shifted.values[2, 0]))
        self.assertEqual(shifted.missing_reasons[2][0], "not_released")
        self.assertTrue(np.array_equal(shifted.values[:, 1], matrix.values[:, 1]))

    def test_origin_matrix_fails_on_duplicates_and_unregistered_cells(self) -> None:
        duplicate = PanelCell("2020-01", "A", 1.0, "2019-12")
        with self.assertRaisesRegex(ReliabilityExecutionHarnessError, "Duplicate"):
            build_origin_matrix((duplicate, duplicate), ("2020-01",), ("A",))
        with self.assertRaisesRegex(ReliabilityExecutionHarnessError, "outside"):
            build_origin_matrix(
                (PanelCell("2020-02", "A", 1.0, "2020-01"),),
                ("2020-01",),
                ("A",),
            )
        with self.assertRaisesRegex(ReliabilityExecutionHarnessError, "incomplete"):
            build_origin_matrix(
                (PanelCell("2020-01", "A", 1.0, "2019-12"),),
                ("2020-01", "2020-02"),
                ("A",),
            )

    def test_complete_case_fit_recovers_exact_final_120_calendar_scores(self) -> None:
        index = np.arange(180, dtype=np.float64)
        factors = np.column_stack((index / 40.0, np.sin(index / 9.0)))
        loadings = np.asarray([[1.0, 0.2], [-0.4, 1.0], [0.7, -0.3], [0.3, 0.8]], dtype=np.float64)
        values = factors @ loadings.T
        values[-120::5, 0] = np.nan
        values[-119::7, 1] = np.nan
        result = recover_complete_case_scores(
            values,
            np.asarray([1.0, 1.0, 1.0, 1.0]),
            candidate_ranks=(2,),
        )
        self.assertEqual(result.rank, 2)
        self.assertEqual(result.final_window_scores.shape, (120, 2))
        self.assertTrue(np.all(np.isfinite(result.final_window_scores)))
        self.assertGreaterEqual(result.complete_row_indices.size, 60)

    def test_complete_case_recovery_fails_when_calendar_row_is_unidentified(self) -> None:
        index = np.arange(130, dtype=np.float64)
        values = np.column_stack((index, np.sin(index), np.cos(index), index / 3.0))
        values[-1, 1:] = np.nan
        with self.assertRaisesRegex(ReliabilityExecutionHarnessError, "unidentified"):
            recover_complete_case_scores(
                values, np.ones(4), candidate_ranks=(2,), final_window_rows=120
            )

    def test_near_duplicate_resolution_uses_components_and_frozen_tie_break(self) -> None:
        index = np.arange(80, dtype=np.float64)
        values = np.column_stack(
            (
                index,
                index + 0.001 * np.sin(index),
                index + 0.002 * np.cos(index),
                np.sin(index / 3.0),
            )
        )
        metadata = (
            SeriesRedundancyMetadata("A", "credit", 1, 1, 2, 0.0, 0),
            SeriesRedundancyMetadata("B", "credit", 2, 1, 5, 0.0, 1),
            SeriesRedundancyMetadata("C", "credit", 2, 0, 8, 0.0, 2),
            SeriesRedundancyMetadata("D", "prices", 1, 0, 0, 0.0, 3),
        )
        result = resolve_near_duplicates(values, metadata)
        self.assertEqual(result.components, (("A", "B", "C"), ("D",)))
        self.assertEqual(result.retained_indices, (2, 3))
        reverse = resolve_near_duplicates(values[:, ::-1], metadata[::-1])
        self.assertEqual(
            {metadata[index].series_id for index in result.retained_indices},
            {metadata[::-1][index].series_id for index in reverse.retained_indices},
        )

    def test_anchor_scalar_is_rotation_invariant_for_ranks_one_two_and_three(self) -> None:
        generator = np.random.default_rng(27)
        for rank in (1, 2, 3):
            with self.subTest(rank=rank):
                scores = generator.normal(size=(80, rank))
                loadings = generator.normal(size=(8, rank))
                rotation, _ = np.linalg.qr(generator.normal(size=(rank, rank)))
                base = rank_invariant_anchor_state(scores, loadings, np.eye(8))
                changed = rank_invariant_anchor_state(
                    scores @ rotation, loadings @ rotation, np.eye(8)
                )
                self.assertAlmostEqual(base.capture, changed.capture, places=12)
                self.assertTrue(
                    np.allclose(
                        base.standardized_scores,
                        changed.standardized_scores,
                        rtol=0.0,
                        atol=1e-11,
                    )
                )

    def test_dual_history_identity_and_all_within_scenario_gates_are_executable(self) -> None:
        index = np.arange(130, dtype=np.float64)
        scores = np.column_stack((index, np.sin(index)))
        loadings = np.asarray([[1.0, 0.0], [0.0, 1.0], [0.5, 0.2]])
        mask = np.ones((130, 3), dtype=np.bool_)
        values = scores @ loadings.T
        key = scenario_history_key(mask, values, mask[-120:], values[-120:])
        self.assertEqual(len(key), 64)
        summary = HistoryFitSummary(
            converged=True,
            channel_count=5,
            final_scores_identified=True,
            anchor_capture=0.8,
            score_projector=score_projector(scores),
            channel_projector=channel_projector(loadings, np.eye(3)),
        )
        gate = evaluate_within_scenario_gate(
            summary,
            summary,
            score_threshold=0.1,
            channel_threshold=0.1,
            orientation_floor=0.7,
        )
        self.assertTrue(gate.passed)
        failed = evaluate_within_scenario_gate(
            HistoryFitSummary(**{**summary.__dict__, "converged": False}),
            summary,
            score_threshold=0.1,
            channel_threshold=0.1,
            orientation_floor=0.9,
        )
        self.assertEqual(failed.failures, ("nonconvergence", "anchor_capture"))
        with self.assertRaisesRegex(ReliabilityExecutionHarnessError, "120-row"):
            scenario_history_key(mask, values, mask[-119:], values[-119:])
        with self.assertRaisesRegex(ReliabilityExecutionHarnessError, "controls"):
            evaluate_within_scenario_gate(
                summary,
                summary,
                score_threshold=-0.1,
                channel_threshold=0.1,
                orientation_floor=0.7,
            )

    def test_robust_pca_is_deterministic_and_preserves_observed_decomposition(self) -> None:
        left = np.arange(24, dtype=np.float64).reshape(8, 3) / 10.0
        right = np.asarray([[1.0, -0.3, 0.4, 0.8]])
        low_rank = left[:, :1] @ right
        values = low_rank.copy()
        values[2, 1] += 8.0
        values[6, 3] -= 5.0
        values[1, 2] = np.nan
        first = fit_observed_stable_pcp(values)
        second = fit_observed_stable_pcp(values)
        observed = np.isfinite(values)
        self.assertTrue(first.converged)
        self.assertLessEqual(first.relative_primal_error, 1e-8)
        self.assertTrue(
            np.allclose(
                (first.low_rank + first.sparse)[observed],
                values[observed],
                rtol=0.0,
                atol=1e-6,
            )
        )
        self.assertEqual(first.low_rank.tobytes(), second.low_rank.tobytes())

    def test_calibration_threshold_and_matching_tie_breaks_are_frozen(self) -> None:
        candidates = (
            ThresholdCandidate("wide", 0.2, 0.6, 0.2, 0.2, 0.5),
            ThresholdCandidate("tight", 0.2, 0.6, 0.1, 0.1, 0.8),
            ThresholdCandidate("loss", 0.1, 0.2, 0.3, 0.3, 0.5),
        )
        self.assertEqual(select_calibration_threshold(candidates).candidate_id, "loss")
        self.assertEqual(match_calibration_participation(candidates, 0.59).candidate_id, "tight")

    def test_structure_breaking_controls_change_paths_and_have_failure_rule(self) -> None:
        channels = ("a", "a", "b", "c")
        rotated = rotate_series_channel_assignments(channels, ("a", "b", "c"))
        self.assertNotEqual(rotated, channels)
        values = np.arange(72, dtype=np.float64)
        blocks = ("calibration",) * 36 + ("evaluation",) * 36
        shifted = cyclic_shift_within_blocks(values, blocks, shift=24)
        self.assertFalse(np.array_equal(values, shifted))
        self.assertEqual(set(shifted[:36]), set(values[:36]))
        labels = np.arange(60)
        self.assertEqual(
            permute_label_blocks(labels).tobytes(), permute_label_blocks(labels).tobytes()
        )
        passed = assess_negative_controls(
            primary_loss=0.2,
            primary_success=True,
            nc1_loss=0.3,
            nc1_success=False,
            nc2_loss=0.1,
            nc2_success=True,
            primary_threshold_and_loss="primary",
            nc3_threshold_and_loss="permuted",
        )
        self.assertTrue(passed.passed)
        failed = assess_negative_controls(
            primary_loss=0.2,
            primary_success=True,
            nc1_loss=0.1,
            nc1_success=True,
            nc2_loss=0.1,
            nc2_success=True,
            primary_threshold_and_loss="same",
            nc3_threshold_and_loss="same",
        )
        self.assertFalse(failed.passed)

    def test_noncircular_bootstrap_is_deterministic_bounded_and_simultaneous(self) -> None:
        first = make_noncircular_block_plan(20, 6, 25)
        second = make_noncircular_block_plan(20, 6, 25)
        self.assertEqual(first.indices.tobytes(), second.indices.tobytes())
        self.assertGreaterEqual(int(first.indices.min()), 0)
        self.assertLess(int(first.indices.max()), 20)
        for row in first.indices:
            for start in range(0, 18, 6):
                segment = row[start : min(start + 6, 20)]
                if segment.size > 1:
                    self.assertTrue(np.all(np.diff(segment) == 1))
        estimates = np.column_stack((np.linspace(-0.2, 0.2, 25), np.ones(25, dtype=np.float64)))
        intervals = simultaneous_bootstrap_intervals(estimates, np.asarray([0.0, 1.0]))
        self.assertEqual(intervals.simultaneous_lower[1], 1.0)
        self.assertEqual(intervals.simultaneous_upper[1], 1.0)
        self.assertGreaterEqual(intervals.critical_value, 0.0)

    def test_calibration_lock_and_evaluation_marker_are_hash_chained_and_single_use(self) -> None:
        amendment_hash = hashlib.sha256(PROPOSAL.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / "calibration.lock.json"
            marker = root / "evaluation.started.json"
            lock_hash = write_calibration_lock(
                lock,
                approved_amendment_sha256=amendment_hash,
                implementation_commit="fixture-commit",
                exact_input_hashes={"input": "a" * 64},
                selected_settings={"threshold": 0.1},
                calibration_metrics={"loss": 0.2},
                evaluation_identity_hashes=("b" * 64,),
                invariance_results={"passed": True},
            )
            self.assertEqual(json.loads(lock.read_text())["stage_A_sha256"], lock_hash)
            marker_hash = start_evaluation_once(
                lock,
                marker,
                expected_amendment_sha256=amendment_hash,
                import_scan_passed=True,
            )
            self.assertEqual(len(marker_hash), 64)
            with self.assertRaisesRegex(ReliabilityExecutionHarnessError, "overwrite"):
                start_evaluation_once(
                    lock,
                    marker,
                    expected_amendment_sha256=amendment_hash,
                    import_scan_passed=True,
                )
            with self.assertRaisesRegex(ReliabilityExecutionHarnessError, "scan"):
                start_evaluation_once(
                    lock,
                    root / "second-marker.json",
                    expected_amendment_sha256=amendment_hash,
                    import_scan_passed=False,
                )
            with self.assertRaisesRegex(ReliabilityExecutionHarnessError, "identities"):
                write_calibration_lock(
                    root / "invalid-lock.json",
                    approved_amendment_sha256="not-a-hash",
                    implementation_commit="fixture-commit",
                    exact_input_hashes={"input": "a" * 64},
                    selected_settings={},
                    calibration_metrics={},
                    evaluation_identity_hashes=("b" * 64,),
                    invariance_results={},
                )

    def test_all_eleven_gaps_are_implemented_without_outcome_module_imports(self) -> None:
        surface = implementation_surface()
        self.assertEqual(
            set(key for key in surface if key.startswith("XG-")),
            {f"XG-{index:02d}" for index in range(1, 12)},
        )
        self.assertFalse(surface["official_values_accessed"])
        self.assertFalse(surface["evaluation_results_accessed"])
        source = inspect.getsource(harness_module)
        tree = ast.parse(source)
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertFalse(any("transmission" in name for name in imported))

    def test_hostile_invalid_controls_fail_closed(self) -> None:
        with self.assertRaisesRegex(ReliabilityExecutionHarnessError, "subset"):
            matrix = build_origin_matrix(
                (PanelCell("2020-01", "A", 1.0, "2019-12"),),
                ("2020-01",),
                ("A",),
            )
            apply_slow_release_stress(matrix, ("B",))
        with self.assertRaisesRegex(ReliabilityExecutionHarnessError, "penalty"):
            fit_observed_stable_pcp(np.eye(3), lambda_multiplier=3.0)
        with self.assertRaisesRegex(ReliabilityExecutionHarnessError, "contract"):
            make_noncircular_block_plan(5, 6, 1)


if __name__ == "__main__":
    unittest.main()
