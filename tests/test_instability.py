import unittest

import numpy as np

from shockbridge_state_risk.state.instability import (
    InstabilityError,
    detect_breach_episodes,
    gram_geometry,
    monetary_regimes,
    sign_materiality,
    standardization_drift,
)
from shockbridge_state_risk.state.subspace import (
    compare_subspaces,
    economic_anchor_matrix,
    estimate_anchored_subspace,
)


class InstabilityTests(unittest.TestCase):
    @staticmethod
    def _fixture(rows: int = 180) -> np.ndarray:
        index = np.arange(rows, dtype=np.float64)
        first = np.sin(index / 9.0) + 0.2 * np.cos(index / 23.0)
        second = np.cos(index / 14.0) - 0.1 * np.sin(index / 4.0)
        values = np.column_stack(
            (
                first + 0.2 * second,
                -1.1 * first + 0.1 * second,
                0.9 * first - 0.1 * second,
                second + 0.1 * first,
            )
        )
        values[7, 0] = np.nan
        values[18, 2] = np.nan
        return values

    def test_gram_geometry_is_deterministic_and_matches_identical_histories(self) -> None:
        values = self._fixture()
        first = gram_geometry(values, values)
        second = gram_geometry(values, values)
        np.testing.assert_array_equal(first.expanding_gram, second.expanding_gram)
        np.testing.assert_allclose(first.principal_cosines, np.ones(2), atol=1e-12)
        self.assertAlmostEqual(first.normalized_projector_distance, 0.0)
        self.assertAlmostEqual(first.gram_spectral_distance, 0.0)
        self.assertAlmostEqual(float(np.sum(first.upper_triangle_drift_contribution)), 0.0)
        self.assertGreater(first.expanding_absolute_eigengap, 0.0)

    def test_geometry_and_standardization_drift_detect_changed_window(self) -> None:
        values = self._fixture()
        rolling = values[-120:].copy()
        rolling[:, 3] = 2.5 * rolling[:, 3] + 4.0
        rolling[:, 0] += 0.6 * rolling[:, 3]
        geometry = gram_geometry(values, rolling)
        comparison = compare_subspaces(
            estimate_anchored_subspace(values, economic_anchor_matrix()),
            estimate_anchored_subspace(rolling, economic_anchor_matrix()),
        )
        np.testing.assert_allclose(
            geometry.principal_cosines, comparison.principal_cosines, atol=1e-12
        )
        self.assertAlmostEqual(
            geometry.normalized_projector_distance,
            comparison.root_mean_square_projector_distance,
        )
        self.assertGreater(geometry.gram_spectral_distance, 0.0)
        self.assertGreater(geometry.normalized_projector_distance, 0.0)
        self.assertAlmostEqual(float(np.sum(geometry.upper_triangle_drift_contribution)), 1.0)
        self.assertTrue(
            np.all(geometry.upper_triangle_drift_contribution[np.tril_indices(4, -1)] == 0)
        )
        drift = standardization_drift(values, rolling)
        self.assertEqual(drift.location_shift.shape, (4,))
        self.assertGreater(abs(float(drift.log_scale_ratio[3])), 0.5)
        self.assertGreater(float(drift.expanding_missing_rate[0]), 0.0)

    def test_sign_materiality_and_monetary_regimes(self) -> None:
        left = np.asarray([-1.0, -0.05, 0.4, 0.0, 0.8])
        right = np.asarray([0.8, 0.04, 0.2, 0.0, -0.6])
        audit = sign_materiality(left, right, 0.25)
        self.assertEqual(audit.disagreements, 3)
        self.assertEqual(audit.substantive_disagreements, 2)
        self.assertAlmostEqual(audit.substantive_disagreement_rate, 0.4)
        self.assertEqual(
            monetary_regimes(np.asarray([-0.1, -1e-13, 0.0, 1e-13, 0.2])),
            ("negative", "zero", "zero", "zero", "positive"),
        )

    def test_episode_hysteresis_and_open_episode(self) -> None:
        months = tuple(f"month-2020-{month:02d}" for month in range(1, 13))
        flags = np.asarray(
            [False, True, True, True, False, True, False, False, False, True, True, True]
        )
        episodes = detect_breach_episodes(months, flags, 3, 3)
        self.assertEqual(len(episodes), 2)
        self.assertEqual(episodes[0].start_month, "month-2020-02")
        self.assertEqual(episodes[0].end_month, "month-2020-06")
        self.assertEqual(episodes[0].breach_months, 4)
        self.assertFalse(episodes[0].open_at_sample_end)
        self.assertEqual(episodes[1].end_month, "month-2020-12")
        self.assertTrue(episodes[1].open_at_sample_end)

    def test_invalid_inputs_fail_closed(self) -> None:
        values = self._fixture()
        with self.assertRaises(InstabilityError):
            gram_geometry(values[:7], values[-120:])
        with self.assertRaises(InstabilityError):
            gram_geometry(values, values[:, :3])
        with self.assertRaises(InstabilityError):
            gram_geometry(values, values, factor_dimension=4)
        with self.assertRaises(InstabilityError):
            gram_geometry(values, values, factor_dimension=True)
        infinite = values.copy()
        infinite[0, 0] = np.inf
        with self.assertRaises(InstabilityError):
            gram_geometry(values, infinite)
        constant = values.copy()
        constant[:, 0] = 1.0
        with self.assertRaises(InstabilityError):
            standardization_drift(values, constant)
        with self.assertRaises(InstabilityError):
            sign_materiality(np.ones(3), np.ones(2), 0.25)
        with self.assertRaises(InstabilityError):
            sign_materiality(np.ones(3), np.ones(3), -0.1)
        with self.assertRaises(InstabilityError):
            monetary_regimes(np.asarray([np.nan]))
        with self.assertRaises(InstabilityError):
            detect_breach_episodes(("month-2020-01", "month-2020-03"), np.zeros(2, dtype=bool))
        with self.assertRaises(InstabilityError):
            detect_breach_episodes(("bad",), np.zeros(1, dtype=bool))
        with self.assertRaises(InstabilityError):
            detect_breach_episodes((), np.zeros(0, dtype=bool))
        with self.assertRaises(InstabilityError):
            detect_breach_episodes(("month-2020-01",), np.zeros(1), 0, 1)
        with self.assertRaises(InstabilityError):
            detect_breach_episodes(("month-2020-01",), np.zeros(1, dtype=bool), True, 1)


if __name__ == "__main__":
    unittest.main()
