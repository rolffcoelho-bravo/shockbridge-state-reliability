import unittest

import numpy as np

from shockbridge_state_risk.state.redesign import (
    StateRedesignError,
    estimate_continuous_factor,
    estimate_exact_factor_states,
)


class StateRedesignTests(unittest.TestCase):
    @staticmethod
    def _fixture(rows: int = 80) -> np.ndarray:
        index = np.arange(rows, dtype=np.float64)
        cycle = np.sin(index / 8.0)
        values = np.column_stack(
            (
                2.0 + 0.3 * cycle,
                1.0 - 1.2 * cycle,
                8.0 + 0.8 * cycle,
                0.5 + 0.2 * np.cos(index / 10.0),
            )
        )
        values[7, 0] = np.nan
        values[15, 2] = np.nan
        return values

    def test_continuous_factor_is_finite_sign_anchored_and_deterministic(self) -> None:
        train = self._fixture()
        current = np.asarray([2.1, 0.2, 8.6, 0.4])
        first = estimate_continuous_factor(train, current)
        second = estimate_continuous_factor(train, current)
        np.testing.assert_array_equal(first.loadings, second.loadings)
        np.testing.assert_array_equal(
            first.historical_standardized_factors,
            second.historical_standardized_factors,
        )
        self.assertGreaterEqual(first.sign_anchor_value, -1e-12)
        self.assertAlmostEqual(float(np.mean(first.historical_standardized_factors)), 0.0)
        self.assertAlmostEqual(float(np.std(first.historical_standardized_factors)), 1.0)
        self.assertGreater(first.standardized_factor_variance, 0.0)
        self.assertGreater(first.factor_innovation_variance, 0.0)
        self.assertTrue(np.all(first.idiosyncratic_variances > 0.0))
        self.assertTrue(np.isfinite(first.feature_log_predictive_score))

        standardized_current = (current - first.feature_means) / first.feature_scales
        prior_mean = first.ar_coefficient * (
            first.historical_standardized_factors[-1] * first.factor_scale + first.factor_location
        )
        covariance = np.diag(
            first.idiosyncratic_variances
        ) + first.factor_innovation_variance * np.outer(first.loadings, first.loadings)
        difference = standardized_current - first.loadings * prior_mean
        sign, log_determinant = np.linalg.slogdet(covariance)
        self.assertEqual(sign, 1.0)
        expected_score = -0.5 * (
            current.size * np.log(2.0 * np.pi)
            + log_determinant
            + difference @ np.linalg.solve(covariance, difference)
        )
        self.assertAlmostEqual(first.feature_log_predictive_score, expected_score)

    def test_exact_factor_states_are_valid_and_have_no_restart_claim(self) -> None:
        prediction = estimate_exact_factor_states(
            self._fixture(), np.asarray([2.1, 0.2, 8.6, 0.4]), 2
        )
        self.assertAlmostEqual(float(np.sum(prediction.probabilities)), 1.0)
        self.assertEqual(prediction.state_profiles.shape, (2, 4))
        self.assertEqual(len(np.unique(prediction.exact_fit.labels)), 2)
        self.assertEqual(sorted(prediction.semantic_order), [0, 1])
        self.assertEqual(prediction.optimization_status, "EXACT_GLOBAL_1D_WITHINSS_OPTIMUM")
        self.assertTrue(np.isfinite(prediction.factor_mixture_log_score))

    def test_invalid_factor_inputs_fail_closed(self) -> None:
        train = self._fixture()
        current = np.asarray([2.1, 0.2, 8.6, 0.4])
        cases = (
            (train[:3], current, 0.05, 1, 2),
            (train, current[:3], 0.05, 1, 2),
            (train, current, 0.0, 1, 2),
            (train, np.full(4, np.nan), 0.05, 1, 2),
            (train, current, 0.05, 1, 1),
            (train, current, 0.05, 1, 8),
        )
        for historical, observation, floor, production, unemployment in cases:
            with self.subTest(floor=floor, production=production, unemployment=unemployment):
                with self.assertRaises(StateRedesignError):
                    estimate_continuous_factor(
                        historical,
                        observation,
                        floor,
                        production,
                        unemployment,
                    )


if __name__ == "__main__":
    unittest.main()
