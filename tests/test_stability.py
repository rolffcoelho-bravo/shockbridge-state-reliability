import unittest

import numpy as np

from shockbridge_state_risk.state.stability import (
    StabilityError,
    StabilityThresholds,
    evaluate_factor_stability,
)


class FactorStabilityTests(unittest.TestCase):
    @staticmethod
    def _thresholds() -> StabilityThresholds:
        return StabilityThresholds(
            minimum_pearson_correlation=0.80,
            minimum_spearman_correlation=0.80,
            maximum_sign_disagreement_rate=0.10,
            maximum_standardized_mean_absolute_difference=0.35,
            minimum_median_loading_cosine=0.90,
            minimum_loading_cosine=0.75,
            minimum_anchor_tenth_percentile=0.20,
            weak_anchor_cutoff=0.10,
            maximum_weak_anchor_rate=0.05,
        )

    def test_stable_factor_passes_all_declared_gates(self) -> None:
        expanding = np.asarray([-1.2, -0.7, -0.1, 0.2, 0.8, 1.3])
        rolling = expanding + np.asarray([0.02, -0.03, 0.01, -0.01, 0.03, -0.02])
        base = np.asarray([-0.3, -0.6, 0.7, 0.2])
        expanding_loadings = np.tile(base, (expanding.size, 1))
        rolling_loadings = expanding_loadings + 0.01
        anchors = np.full(expanding.size, 1.3)
        audit = evaluate_factor_stability(
            expanding,
            rolling,
            expanding_loadings,
            rolling_loadings,
            anchors,
            anchors - 0.02,
            self._thresholds(),
        )
        self.assertTrue(audit.passed)
        self.assertTrue(all(value for _, value in audit.gates))
        self.assertGreater(audit.pearson_correlation, 0.99)
        self.assertEqual(audit.sign_disagreement_rate, 0.0)

    def test_unstable_factor_fails_without_hiding_individual_metrics(self) -> None:
        expanding = np.asarray([-2.0, -1.0, -0.5, 0.5, 1.0, 2.0])
        rolling = np.asarray([2.0, 1.0, 0.5, -0.5, -1.0, -2.0])
        expanding_loadings = np.tile(np.asarray([-0.3, -0.6, 0.7, 0.2]), (6, 1))
        rolling_loadings = -expanding_loadings
        anchors = np.full(6, 0.05)
        audit = evaluate_factor_stability(
            expanding,
            rolling,
            expanding_loadings,
            rolling_loadings,
            anchors,
            anchors,
            self._thresholds(),
        )
        self.assertFalse(audit.passed)
        self.assertEqual(audit.sign_disagreement_rate, 1.0)
        self.assertAlmostEqual(audit.minimum_loading_cosine, -1.0)
        self.assertEqual(audit.weak_anchor_rate, 1.0)

    def test_anchor_gate_uses_the_weaker_window(self) -> None:
        expanding = np.asarray([-1.0, -0.5, 0.2, 0.7, 1.1])
        rolling = expanding + 0.01
        loadings = np.tile(np.asarray([-0.3, -0.6, 0.7, 0.2]), (5, 1))
        audit = evaluate_factor_stability(
            expanding,
            rolling,
            loadings,
            loadings,
            np.full(5, 1.0),
            np.asarray([0.05, 0.05, 0.05, 0.3, 0.3]),
            self._thresholds(),
        )
        self.assertFalse(audit.passed)
        self.assertEqual(audit.weak_anchor_rate, 0.6)
        self.assertLess(audit.anchor_tenth_percentile, 0.20)

    def test_invalid_stability_inputs_and_thresholds_fail_closed(self) -> None:
        factor = np.asarray([-1.0, 0.0, 1.0])
        loadings = np.tile(np.asarray([-0.3, -0.6, 0.7]), (3, 1))
        anchors = np.ones(3)
        invalid_thresholds = StabilityThresholds(
            minimum_pearson_correlation=1.1,
            minimum_spearman_correlation=0.8,
            maximum_sign_disagreement_rate=0.1,
            maximum_standardized_mean_absolute_difference=0.3,
            minimum_median_loading_cosine=0.9,
            minimum_loading_cosine=0.75,
            minimum_anchor_tenth_percentile=0.2,
            weak_anchor_cutoff=0.1,
            maximum_weak_anchor_rate=0.05,
        )
        with self.assertRaisesRegex(StabilityError, "\[0, 1\]"):
            evaluate_factor_stability(
                factor, factor, loadings, loadings, anchors, anchors, invalid_thresholds
            )
        nonfinite_thresholds = StabilityThresholds(
            minimum_pearson_correlation=0.8,
            minimum_spearman_correlation=0.8,
            maximum_sign_disagreement_rate=0.1,
            maximum_standardized_mean_absolute_difference=np.nan,
            minimum_median_loading_cosine=0.9,
            minimum_loading_cosine=0.75,
            minimum_anchor_tenth_percentile=0.2,
            weak_anchor_cutoff=0.1,
            maximum_weak_anchor_rate=0.05,
        )
        with self.assertRaisesRegex(StabilityError, "thresholds must be finite"):
            evaluate_factor_stability(
                factor, factor, loadings, loadings, anchors, anchors, nonfinite_thresholds
            )
        with self.assertRaisesRegex(StabilityError, "paired one-dimensional"):
            evaluate_factor_stability(
                factor[:2], factor, loadings, loadings, anchors, anchors, self._thresholds()
            )
        with self.assertRaisesRegex(StabilityError, "negative anchor"):
            evaluate_factor_stability(
                factor,
                factor + 0.01,
                loadings,
                loadings,
                -anchors,
                anchors,
                self._thresholds(),
            )
        with self.assertRaisesRegex(StabilityError, "variation"):
            evaluate_factor_stability(
                np.ones(3),
                np.ones(3),
                loadings,
                loadings,
                anchors,
                anchors,
                self._thresholds(),
            )


if __name__ == "__main__":
    unittest.main()
