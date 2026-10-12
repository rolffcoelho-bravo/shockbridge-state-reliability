import unittest

import numpy as np

from shockbridge_state_risk.state.abstention import (
    AbstentionError,
    authorization_actions,
    conservative_thresholds,
    future_any_breach,
    geometry_risk_score,
    moving_block_indices,
    negative_control_scores,
    policy_metrics,
    select_threshold,
)


class AbstentionTests(unittest.TestCase):
    """Software-only tests; these arrays are not empirical observations."""

    def test_geometry_score_zero_matches_joint_boundary(self) -> None:
        scores = geometry_risk_score(
            np.asarray([0.75, 0.90, 0.70]),
            np.asarray([0.20, 0.35, 0.30]),
        )
        np.testing.assert_allclose(scores, [0.0, 0.0, (0.75 - 0.70) / 0.75])
        np.testing.assert_array_equal(scores > 0.0, [False, False, True])

    def test_future_label_is_strictly_forward_and_requires_full_horizon(self) -> None:
        labels = future_any_breach(
            np.asarray([True, False, False, True, False, False], dtype=np.bool_), 2
        )
        np.testing.assert_array_equal(labels, [False, True, True, False])
        with self.assertRaisesRegex(AbstentionError, "invalid"):
            future_any_breach(np.asarray([False], dtype=np.bool_), 1)

    def test_selected_threshold_is_never_less_conservative_than_zero(self) -> None:
        scores = np.asarray([-0.4, -0.3, -0.2, -0.1, 0.2])
        future = np.asarray([False, False, True, True, True], dtype=np.bool_)
        threshold, metrics = select_threshold(scores, future, 0.25)
        self.assertLessEqual(threshold, 0.0)
        self.assertIn(threshold, conservative_thresholds(scores))
        self.assertGreaterEqual(metrics.abstention_rate, 0.0)

    def test_always_abstain_keeps_selective_risk_undefined(self) -> None:
        actions = authorization_actions(np.asarray([-0.2, 0.1]), -np.inf)
        metrics = policy_metrics(actions, np.asarray([False, True], dtype=np.bool_), 0.25)
        self.assertEqual(metrics.coverage, 0.0)
        self.assertIsNone(metrics.selective_risk)
        self.assertEqual(metrics.mean_loss, 0.25)

    def test_negative_controls_preserve_values_and_reject_unknown_control(self) -> None:
        scores = np.arange(46, dtype=np.float64)
        for control in ("reverse_time", "rotate_23"):
            transformed = negative_control_scores(scores, control)
            np.testing.assert_array_equal(np.sort(transformed), scores)
            self.assertFalse(np.array_equal(transformed, scores))
        with self.assertRaisesRegex(AbstentionError, "Unknown"):
            negative_control_scores(scores, "unknown")

    def test_moving_blocks_are_reproducible_consecutive_and_in_bounds(self) -> None:
        first = moving_block_indices(46, 12, 31, 18012026)
        second = moving_block_indices(46, 12, 31, 18012026)
        np.testing.assert_array_equal(first, second)
        self.assertEqual(first.shape, (31, 46))
        self.assertTrue(np.all((first >= 0) & (first < 46)))
        for row in first:
            for start in range(0, 46, 12):
                block = row[start : min(start + 12, 46)]
                self.assertTrue(np.all(np.diff(block) == 1))

    def test_invalid_geometry_input_fails_closed(self) -> None:
        with self.assertRaisesRegex(AbstentionError, "invalid"):
            geometry_risk_score(np.asarray([0.5]), np.asarray([np.nan]))


if __name__ == "__main__":
    unittest.main()
