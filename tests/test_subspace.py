import unittest

import numpy as np

from shockbridge_state_risk.state.subspace import (
    AnchoredSubspaceEstimate,
    SubspaceError,
    align_basis_to_anchors,
    compare_subspaces,
    economic_anchor_matrix,
    estimate_anchored_subspace,
    estimate_anchored_two_factor,
    estimate_fixed_loading_factor,
)


class SubspaceTests(unittest.TestCase):
    @staticmethod
    def _fixture(rows: int = 160) -> np.ndarray:
        index = np.arange(rows, dtype=np.float64)
        slack = np.sin(index / 8.0) + 0.25 * np.cos(index / 19.0)
        tightness = np.cos(index / 13.0) - 0.15 * np.sin(index / 5.0)
        values = np.column_stack(
            (
                2.0 - 0.8 * tightness + 0.05 * slack,
                1.0 - 1.1 * slack + 0.05 * tightness,
                7.0 + 0.9 * slack - 0.05 * tightness,
                1.5 + 0.9 * tightness + 0.05 * slack,
            )
        )
        values[11, 0] = np.nan
        values[37, 2] = np.nan
        return values

    def test_anchor_matrix_and_alignment_are_rotation_invariant(self) -> None:
        anchors = economic_anchor_matrix()
        self.assertTrue(np.allclose(anchors.T @ anchors, np.eye(2)))
        rotation = np.asarray([[0.6, -0.8], [0.8, 0.6]])
        first, first_capture, _ = align_basis_to_anchors(anchors, anchors)
        second, second_capture, _ = align_basis_to_anchors(anchors @ rotation, anchors)
        np.testing.assert_allclose(first, second, atol=1e-12)
        np.testing.assert_allclose(first_capture, second_capture, atol=1e-12)

    def test_subspace_estimate_and_comparison_are_deterministic(self) -> None:
        anchors = economic_anchor_matrix()
        first = estimate_anchored_subspace(self._fixture(), anchors)
        second = estimate_anchored_subspace(self._fixture(), anchors)
        np.testing.assert_array_equal(first.basis, second.basis)
        np.testing.assert_allclose(first.basis.T @ first.basis, np.eye(2), atol=1e-12)
        np.testing.assert_allclose(
            first.anchored_basis.T @ first.anchored_basis, np.eye(2), atol=1e-12
        )
        self.assertTrue(np.all((first.anchor_capture >= 0) & (first.anchor_capture <= 1)))
        self.assertGreater(float(np.sum(first.explained_variance_ratio)), 0.9)
        comparison = compare_subspaces(first, second)
        np.testing.assert_allclose(comparison.principal_cosines, np.ones(2), atol=1e-12)
        np.testing.assert_allclose(comparison.anchored_loading_cosines, np.ones(2), atol=1e-12)
        self.assertAlmostEqual(comparison.root_mean_square_projector_distance, 0.0)

    def test_fixed_and_two_factor_filters_are_finite_and_use_missing_marginalization(self) -> None:
        train = self._fixture()
        current = np.asarray([2.2, -0.1, np.nan, 2.0])
        anchors = economic_anchor_matrix()
        development = estimate_anchored_subspace(train[:120], anchors)
        fixed = estimate_fixed_loading_factor(train, current, development.anchored_basis[:, 0])
        self.assertTrue(np.isfinite(fixed.feature_log_predictive_score))
        self.assertGreater(fixed.filtered_factor_variance, 0.0)
        self.assertAlmostEqual(float(np.std(fixed.historical_standardized_factors)), 1.0)
        two = estimate_anchored_two_factor(train, current, anchors)
        self.assertTrue(np.isfinite(two.feature_log_predictive_score))
        self.assertTrue(np.all(np.linalg.eigvalsh(two.filtered_factor_covariance) > 0))
        self.assertTrue(np.all(np.linalg.eigvalsh(two.innovation_covariance) > 0))
        self.assertLessEqual(max(abs(np.linalg.eigvals(two.transition))), 0.98 + 1e-12)
        self.assertEqual(two.historical_standardized_factors.shape, (160, 2))

    def test_invalid_contracts_fail_closed(self) -> None:
        train = self._fixture()
        anchors = economic_anchor_matrix()
        invalid_anchor = anchors.copy()
        invalid_anchor[:, 1] = invalid_anchor[:, 0]
        with self.assertRaises(SubspaceError):
            align_basis_to_anchors(anchors, invalid_anchor)
        with self.assertRaises(SubspaceError):
            align_basis_to_anchors(np.ones(4), anchors)
        with self.assertRaises(SubspaceError):
            align_basis_to_anchors(anchors[:, :1], anchors)
        with self.assertRaises(SubspaceError):
            economic_anchor_matrix(4, 0, 1, 1, 3)
        with self.assertRaises(SubspaceError):
            estimate_anchored_subspace(train[:7], anchors)
        with self.assertRaises(SubspaceError):
            estimate_anchored_subspace(train, anchors, 4)
        with self.assertRaises(SubspaceError):
            estimate_anchored_subspace(np.ones((20, 4)), anchors)
        infinite = train.copy()
        infinite[0, 0] = np.inf
        with self.assertRaises(SubspaceError):
            estimate_anchored_subspace(infinite, anchors)
        with self.assertRaises(SubspaceError):
            estimate_anchored_subspace(train, anchors[:, :1])
        sparse = train.copy()
        sparse[:, 0] = np.nan
        with self.assertRaises(SubspaceError):
            estimate_anchored_subspace(sparse, anchors)
        with self.assertRaises(SubspaceError):
            estimate_fixed_loading_factor(train, np.ones(4), np.ones(4))
        with self.assertRaises(SubspaceError):
            estimate_fixed_loading_factor(train[:7], np.ones(4), anchors[:, 0])
        with self.assertRaises(SubspaceError):
            estimate_fixed_loading_factor(train, np.ones(3), anchors[:, 0])
        with self.assertRaises(SubspaceError):
            estimate_fixed_loading_factor(train, np.full(4, np.nan), anchors[:, 0])
        with self.assertRaises(SubspaceError):
            estimate_fixed_loading_factor(np.ones((20, 4)), np.ones(4), anchors[:, 0])
        with self.assertRaises(SubspaceError):
            estimate_anchored_two_factor(train, np.ones(4), anchors, transition_ridge=-1.0)
        with self.assertRaises(SubspaceError):
            estimate_anchored_two_factor(train, np.ones(4), anchors, variance_floor=np.nan)

        estimate = estimate_anchored_subspace(train, anchors)
        malformed = AnchoredSubspaceEstimate(
            basis=estimate.basis[:, :1],
            anchored_basis=estimate.anchored_basis[:, :1],
            projector=estimate.projector,
            feature_means=estimate.feature_means,
            feature_scales=estimate.feature_scales,
            singular_values=estimate.singular_values[:1],
            explained_variance_ratio=estimate.explained_variance_ratio[:1],
            anchor_capture=estimate.anchor_capture[:1],
            anchor_alignment=estimate.anchor_alignment[:1],
        )
        with self.assertRaises(SubspaceError):
            compare_subspaces(estimate, malformed)
        malformed_anchored = AnchoredSubspaceEstimate(
            basis=estimate.basis,
            anchored_basis=estimate.anchored_basis[:, :1],
            projector=estimate.projector,
            feature_means=estimate.feature_means,
            feature_scales=estimate.feature_scales,
            singular_values=estimate.singular_values,
            explained_variance_ratio=estimate.explained_variance_ratio,
            anchor_capture=estimate.anchor_capture,
            anchor_alignment=estimate.anchor_alignment,
        )
        with self.assertRaises(SubspaceError):
            compare_subspaces(estimate, malformed_anchored)


if __name__ == "__main__":
    unittest.main()
