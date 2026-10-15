import inspect
import unittest

import numpy as np

import shockbridge_state_risk.state.reliability_engine as engine_module
from shockbridge_state_risk.state.reliability_engine import (
    ReliabilityEngineError,
    ScenarioInput,
    align_scores_procrustes,
    build_channel_map,
    canonical_scenario_key,
    channel_projector,
    compare_projectors,
    deduplicate_scenarios,
    fit_em_pca_rank,
    score_projector,
    select_em_pca_rank,
    standardize_observed_matrix,
)


class ReliabilityEngineTests(unittest.TestCase):
    """Software-only numerical fixtures; none are empirical research evidence."""

    def _fixture(self) -> tuple[np.ndarray, np.ndarray]:
        index = np.arange(48, dtype=np.float64)
        factors = np.column_stack(((index - index.mean()) / 12.0, np.sin(index / 5.0)))
        loadings = np.asarray([[1.0, 0.2], [-0.6, 0.9], [0.8, -0.4], [0.3, 1.1]], dtype=np.float64)
        values = factors @ loadings.T
        values[:, 2] += 0.03 * np.cos(index / 3.0)
        values[::7, 0] = np.nan
        values[2::9, 1] = np.nan
        values[4::8, 2] = np.nan
        values[1::10, 3] = np.nan
        standardized = standardize_observed_matrix(values).values
        channel_map = build_channel_map(
            ("activity", "activity", "prices", "policy"),
            np.asarray([1, -1, 1, 1], dtype=np.int64),
            channel_order=("prices", "activity", "policy", "credit"),
        )
        return standardized, channel_map.weights

    def test_standardization_uses_observed_sample_moments_and_preserves_missingness(self) -> None:
        values = np.asarray([[1.0, 2.0], [2.0, np.nan], [3.0, 4.0], [4.0, 5.0]], dtype=np.float64)
        result = standardize_observed_matrix(values, minimum_coverage=0.70, minimum_observations=3)
        self.assertTrue(np.array_equal(np.isnan(result.values), np.isnan(values)))
        for column in range(2):
            observed = result.values[np.isfinite(result.values[:, column]), column]
            self.assertAlmostEqual(float(observed.mean()), 0.0)
            self.assertAlmostEqual(float(observed.std(ddof=1)), 1.0)
        self.assertTrue(np.array_equal(result.counts, np.asarray([4, 3])))

    def test_standardization_fails_closed_on_coverage_scale_and_controls(self) -> None:
        with self.assertRaisesRegex(ReliabilityEngineError, "count and coverage"):
            standardize_observed_matrix(
                [[1.0, np.nan], [2.0, np.nan], [3.0, 1.0]],
                minimum_coverage=0.5,
                minimum_observations=2,
            )
        with self.assertRaisesRegex(ReliabilityEngineError, "positive scale"):
            standardize_observed_matrix(
                [[1.0, 4.0], [2.0, 4.0], [3.0, 4.0]],
                minimum_coverage=1.0,
                minimum_observations=3,
            )
        with self.assertRaisesRegex(ReliabilityEngineError, "thresholds"):
            standardize_observed_matrix([[1.0], [2.0]], minimum_coverage=1.1)
        with self.assertRaisesRegex(ReliabilityEngineError, "nonfinite"):
            standardize_observed_matrix([[1.0], [np.inf]])

    def test_channel_map_has_unit_channel_energy_and_explicit_empty_rows(self) -> None:
        result = build_channel_map(
            ("a", "a", "b"),
            np.asarray([1, -1, 1], dtype=np.int64),
            channel_order=("a", "b", "c"),
        )
        self.assertTrue(np.allclose(np.sum(result.matrix**2, axis=1), [1.0, 1.0, 0.0]))
        self.assertTrue(np.allclose(result.weights, [1 / np.sqrt(2), -1 / np.sqrt(2), 1]))
        self.assertEqual(result.channel_order, ("a", "b", "c"))

    def test_channel_map_rejects_invalid_signs_or_channel_order(self) -> None:
        for signs in ([1, 0], [True, False], [1]):
            with self.subTest(signs=signs), self.assertRaises(ReliabilityEngineError):
                build_channel_map(("a", "b"), np.asarray(signs))
        with self.assertRaisesRegex(ReliabilityEngineError, "contain every"):
            build_channel_map(("a", "b"), np.asarray([1, 1]), channel_order=("a",))

    def test_channel_map_accepts_all_numpy_integer_widths(self) -> None:
        for dtype in (np.int8, np.int16, np.int32, np.int64):
            with self.subTest(dtype=dtype):
                result = build_channel_map(("a", "b"), np.asarray([1, -1], dtype=dtype))
                self.assertTrue(np.array_equal(result.weights, np.asarray([1.0, -1.0])))

    def test_rank_fit_is_deterministic_preserves_observed_entries_and_imputes_missing(self) -> None:
        standardized, weights = self._fixture()
        first = fit_em_pca_rank(standardized, weights, 2)
        second = fit_em_pca_rank(standardized, weights, 2)
        observed = np.isfinite(standardized)
        self.assertTrue(first.converged)
        self.assertTrue(np.array_equal(first.completed_matrix[observed], standardized[observed]))
        self.assertTrue(np.all(np.isfinite(first.completed_matrix)))
        for left, right in (
            (first.scores, second.scores),
            (first.loadings, second.loadings),
            (first.completed_matrix, second.completed_matrix),
        ):
            self.assertEqual(left.tobytes(), right.tobytes())

    def test_rank_fit_fails_closed_on_rank_weights_and_nonconvergence(self) -> None:
        standardized, weights = self._fixture()
        with self.assertRaisesRegex(ReliabilityEngineError, "below the series count"):
            fit_em_pca_rank(standardized, weights, 4)
        with self.assertRaisesRegex(ReliabilityEngineError, "Channel weights"):
            fit_em_pca_rank(standardized, [1.0, 1.0], 1)
        with self.assertRaisesRegex(ReliabilityEngineError, "convergence controls"):
            fit_em_pca_rank(standardized, weights, 1, maximum_iterations=1)
        with self.assertRaisesRegex(ReliabilityEngineError, "did not converge"):
            fit_em_pca_rank(standardized, weights, 1, tolerance=1e-30, maximum_iterations=2)

    def test_rank_selection_returns_identified_fixed_rank_sensitivities(self) -> None:
        standardized, weights = self._fixture()
        complete_fixture = np.where(np.isfinite(standardized), standardized, 0.0)
        result = select_em_pca_rank(complete_fixture, weights, candidate_ranks=(3, 2, 1, 2))
        self.assertEqual(tuple(fit.rank for fit in result.fits), (1, 2, 3))
        self.assertIn(result.selected.rank, (1, 2, 3))
        self.assertEqual(len(result.criteria), 3)
        self.assertTrue(np.all(np.isfinite(result.criteria)))
        with self.assertRaisesRegex(ReliabilityEngineError, "Candidate ranks"):
            select_em_pca_rank(complete_fixture, weights, candidate_ranks=(0,))

    def test_rank_selection_rejects_unidentified_icp2_penalty(self) -> None:
        with self.assertRaisesRegex(ReliabilityEngineError, "ICp2"):
            select_em_pca_rank(
                np.asarray([[1.0, -1.0], [-1.0, 1.0]]),
                np.asarray([1.0, 1.0]),
                candidate_ranks=(1,),
            )

    def test_score_projector_is_rotation_invariant(self) -> None:
        index = np.arange(12, dtype=np.float64)
        scores = np.column_stack((index, np.sin(index)))
        angle = 0.7
        rotation = np.asarray([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        left = score_projector(scores)
        right = score_projector(scores @ rotation)
        comparison = compare_projectors(left, right)
        self.assertAlmostEqual(comparison.spectral_distance, 0.0, places=12)
        self.assertAlmostEqual(comparison.normalized_frobenius_distance, 0.0, places=12)

    def test_unequal_rank_projector_distance_is_defined_and_bounded(self) -> None:
        index = np.arange(20, dtype=np.float64)
        rank_one = score_projector(index[:, None])
        rank_two = score_projector(np.column_stack((index, np.sin(index))))
        result = compare_projectors(rank_one, rank_two)
        self.assertEqual((result.left_rank, result.right_rank), (1, 2))
        self.assertGreaterEqual(result.spectral_distance, 0.0)
        self.assertLessEqual(result.spectral_distance, 1.0 + 1e-10)
        self.assertTrue(np.isfinite(result.normalized_frobenius_distance))

    def test_projector_preserves_numerical_rank_under_near_collinearity(self) -> None:
        index = np.arange(30, dtype=np.float64)
        scores = np.column_stack((index, index + 1e-8 * np.sin(index)))
        projector = score_projector(scores)
        self.assertEqual(np.linalg.matrix_rank(projector, tol=1e-8), 2)
        self.assertTrue(np.allclose(projector @ projector, projector, rtol=0.0, atol=1e-12))

    def test_channel_projector_uses_original_coordinate_loadings_once(self) -> None:
        mapping = build_channel_map(
            ("a", "a", "b", "c"),
            np.asarray([1, -1, 1, 1], dtype=np.int64),
            channel_order=("a", "b", "c"),
        )
        loadings = np.asarray([[1.0, 0.2], [-0.5, 0.7], [0.3, 1.0], [0.8, -0.4]], dtype=np.float64)
        angle = 0.4
        rotation = np.asarray([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        left = channel_projector(loadings, mapping.matrix)
        right = channel_projector(loadings @ rotation, mapping.matrix)
        self.assertAlmostEqual(compare_projectors(left, right).spectral_distance, 0.0, places=12)

    def test_procrustes_alignment_recovers_rotated_centered_scores(self) -> None:
        index = np.arange(16, dtype=np.float64)
        reference = np.column_stack((index / 4.0, np.cos(index / 3.0)))
        rotation = np.asarray([[0.0, -1.0], [1.0, 0.0]])
        target = reference @ rotation + np.asarray([10.0, -4.0])
        aligned = align_scores_procrustes(reference, target)
        centered = reference - reference.mean(axis=0)
        self.assertTrue(np.allclose(aligned, centered, rtol=0.0, atol=1e-12))
        with self.assertRaisesRegex(ReliabilityEngineError, "equal rows and ranks"):
            align_scores_procrustes(reference, target[:, :1])

    def test_projector_helpers_reject_invalid_coordinates(self) -> None:
        with self.assertRaisesRegex(ReliabilityEngineError, "zero numerical rank"):
            score_projector(np.ones((5, 1)))
        with self.assertRaisesRegex(ReliabilityEngineError, "match loading rows"):
            channel_projector(np.eye(3), np.eye(2))
        with self.assertRaisesRegex(ReliabilityEngineError, "symmetric idempotent"):
            compare_projectors(np.ones((2, 2)), np.eye(2))
        with self.assertRaisesRegex(ReliabilityEngineError, "same coordinate"):
            compare_projectors(np.eye(2), np.eye(3))

    def test_canonical_scenario_key_uses_mask_and_twelve_digit_serialization(self) -> None:
        mask = np.asarray([[True, False], [True, True]])
        base = np.asarray([[1.0, np.nan], [-0.0, 2.12345678901234]])
        rounded_equivalent = np.asarray([[1.0, np.nan], [0.0, 2.12345678901235]])
        self.assertEqual(
            canonical_scenario_key(mask, base),
            canonical_scenario_key(mask, rounded_equivalent),
        )
        changed = base.copy()
        changed[1, 2 - 1] = 2.1234568
        self.assertNotEqual(
            canonical_scenario_key(mask, base), canonical_scenario_key(mask, changed)
        )

    def test_scenario_deduplication_is_order_independent_and_lexical(self) -> None:
        mask = np.asarray([[True, False], [True, True]])
        matrix = np.asarray([[1.0, np.nan], [0.0, 2.0]])
        changed = np.asarray([[1.0, np.nan], [0.0, 3.0]])
        scenarios = (
            ScenarioInput("z_duplicate", mask, matrix),
            ScenarioInput("a_representative", mask.copy(), matrix.copy()),
            ScenarioInput("m_distinct", mask, changed),
        )
        forward = deduplicate_scenarios(scenarios)
        reverse = deduplicate_scenarios(reversed(scenarios))
        self.assertEqual(forward, reverse)
        self.assertEqual(len(forward), 2)
        self.assertEqual(forward[0].representative_id, "a_representative")
        self.assertEqual(forward[0].member_ids, ("a_representative", "z_duplicate"))

    def test_scenario_contract_rejects_hidden_values_and_duplicate_ids(self) -> None:
        mask = np.asarray([[True, False], [True, True]])
        hidden = np.asarray([[1.0, 99.0], [0.0, 2.0]])
        with self.assertRaisesRegex(ReliabilityEngineError, "excluded cells missing"):
            canonical_scenario_key(mask, hidden)
        valid = np.asarray([[1.0, np.nan], [0.0, 2.0]])
        with self.assertRaisesRegex(ReliabilityEngineError, "unique nonempty"):
            deduplicate_scenarios(
                (ScenarioInput("same", mask, valid), ScenarioInput("same", mask, valid))
            )

    def test_engine_has_no_retrieval_or_filesystem_surface(self) -> None:
        source = inspect.getsource(engine_module)
        for prohibited in ("urllib", "requests", "httpx", "Path(", "open(", "socket"):
            self.assertNotIn(prohibited, source)


if __name__ == "__main__":
    unittest.main()
