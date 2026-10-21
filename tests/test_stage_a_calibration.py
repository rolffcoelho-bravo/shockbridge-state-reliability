from __future__ import annotations

import unittest

import numpy as np

from shockbridge_state_risk.state.calibration_orchestration import expected_calibration_months
from shockbridge_state_risk.state.stage_a_calibration import (
    B3_LAMBDA_MULTIPLIERS,
    GeometryRecord,
    StageACalibrationError,
    authorization_vector,
    build_candidates,
    calibrate_b3,
    run_stage_a_transaction,
    threshold_grid,
    transaction_summary,
)


def geometry(
    score: float = 0.1,
    channel: float = 0.1,
    capture: float = 0.8,
    count: int = 3,
) -> tuple[GeometryRecord, ...]:
    return tuple(
        GeometryRecord(month, score, channel, capture, count, True)
        for month in expected_calibration_months()
    )


class StageACalibrationTests(unittest.TestCase):
    def test_grid_is_exact_complete_and_ordered(self) -> None:
        grid = threshold_grid()
        self.assertEqual(len(grid), 144)
        self.assertEqual(grid[0], (0.05, 0.05, 0.5))
        self.assertEqual(grid[-1], (0.3, 0.3, 0.8))
        self.assertEqual(len(set(grid)), 144)

    def test_authorization_is_label_free_and_requires_scenario_support(self) -> None:
        records = list(geometry())
        records[0] = GeometryRecord(records[0].origin_month, 0.01, 0.01, 0.9, 1, True)
        actions = authorization_vector(
            records,
            score_cutoff=0.1,
            channel_cutoff=0.1,
            orientation_floor=0.8,
            minimum_scenarios=2,
        )
        self.assertFalse(actions[0])
        self.assertTrue(np.all(actions[1:]))

    def test_candidate_materialization_is_complete_and_hash_stable(self) -> None:
        labels = np.zeros(60, dtype=bool)
        first = build_candidates("primary", geometry(), labels, minimum_scenarios=2)
        second = build_candidates("primary", geometry(), labels, minimum_scenarios=2)
        self.assertEqual(len(first), 144)
        self.assertEqual(
            [item.authorization_sha256 for item in first],
            [item.authorization_sha256 for item in second],
        )

    def test_b3_requires_all_penalties_and_breaks_ties_to_lower_multiplier(self) -> None:
        labels = np.zeros(60, dtype=bool)
        records = {value: geometry(count=1) for value in B3_LAMBDA_MULTIPLIERS}
        result = calibrate_b3(records, labels, participation_target=1.0)
        self.assertEqual(result.lambda_multiplier, 0.5)
        with self.assertRaisesRegex(StageACalibrationError, "three"):
            calibrate_b3({0.5: geometry(count=1)}, labels, participation_target=1.0)

    def test_transaction_uses_calibration_only_and_records_controls(self) -> None:
        labels = np.asarray([False] * 54 + [True] * 6)
        nc3_labels = np.roll(labels, 12)
        b1 = geometry(score=0.2, channel=0.2, capture=0.6, count=1)
        primary = list(geometry(score=0.1, channel=0.1, capture=0.8))
        for index in range(54, 60):
            primary[index] = GeometryRecord(primary[index].origin_month, 0.31, 0.31, 0.49, 3, True)
        degraded = geometry(score=0.31, channel=0.31, capture=0.49)
        transaction = run_stage_a_transaction(
            labels=labels,
            primary=primary,
            B1=b1,
            B2=primary,
            B3={value: b1 for value in B3_LAMBDA_MULTIPLIERS},
            NC1=degraded,
            NC2=degraded,
            NC3_labels=nc3_labels,
        )
        summary = transaction_summary(transaction)
        self.assertEqual(summary["candidate_grid_count"], 144)
        self.assertEqual(
            set(summary["methods"]), {"primary", "B1", "B2", "B3", "NC1", "NC2", "NC3"}
        )
        self.assertNotIn("labels", summary)
        self.assertTrue(transaction.control_gate.nc1_degraded)
        self.assertTrue(transaction.control_gate.nc2_degraded)

    def test_hostile_inputs_fail_closed(self) -> None:
        labels = np.zeros(60, dtype=bool)
        with self.assertRaisesRegex(StageACalibrationError, "60 calibration origins"):
            build_candidates("primary", geometry()[:-1], labels, minimum_scenarios=2)
        with self.assertRaisesRegex(StageACalibrationError, "Boolean"):
            build_candidates("primary", geometry(), labels.astype(int), minimum_scenarios=2)
        with self.assertRaisesRegex(StageACalibrationError, "frozen grid"):
            authorization_vector(
                geometry(),
                score_cutoff=0.11,
                channel_cutoff=0.1,
                orientation_floor=0.8,
                minimum_scenarios=2,
            )
        bad = list(geometry())
        bad[0] = GeometryRecord(bad[0].origin_month, float("nan"), 0.1, 0.8, 3, True)
        with self.assertRaisesRegex(StageACalibrationError, "invalid geometry"):
            build_candidates("primary", bad, labels, minimum_scenarios=2)


if __name__ == "__main__":
    unittest.main()
