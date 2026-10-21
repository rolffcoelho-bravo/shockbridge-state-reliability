from __future__ import annotations

import unittest

import numpy as np

from shockbridge_state_risk.state.calibration_orchestration import (
    SeriesDescriptor,
    prepare_history,
)
from shockbridge_state_risk.state.stage_a_geometry import (
    CHANNEL_ORDER,
    StageAGeometryError,
    b2_record,
    envelope_record,
    fit_history_geometry,
    fit_scenario_pair,
    single_scenario_record,
)


def descriptors() -> tuple[SeriesDescriptor, ...]:
    return tuple(
        SeriesDescriptor(
            f"S{index}",
            CHANNEL_ORDER[index],
            "A_REPLAY_ELIGIBLE",
            "archived_policy_concept_vintages",
            "2003-01",
            index,
            1,
        )
        for index in range(6)
    )


def values(rows: int = 132) -> np.ndarray:
    time = np.arange(rows, dtype=float)
    return np.column_stack(
        [
            np.sin(time / (5.0 + index)) + np.cos(time / (11.0 + index)) + 0.01 * index * time
            for index in range(6)
        ]
    )


class StageAGeometryTests(unittest.TestCase):
    def test_ragged_pair_constructs_common_geometry(self) -> None:
        matrix = values()
        matrix[0, 0] = np.nan
        result = fit_scenario_pair(
            "panel__clock__registered__ragged__full",
            matrix,
            matrix[-120:],
            descriptors(),
            missingness_policy="observed_ragged_edge",
        )
        self.assertEqual(result.expanding.standardized_anchor_scalar.shape, (120,))
        self.assertEqual(result.rolling.channel_projector.shape, (8, 8))
        self.assertGreaterEqual(result.expanding.selected_rank, 1)
        self.assertTrue(0.0 <= result.score_distance <= 1.0 + 1e-10)

    def test_complete_case_pair_uses_training_scale_and_exact_final_calendar(self) -> None:
        matrix = values(140)
        matrix[5, 0] = np.nan
        result = fit_scenario_pair(
            "panel__clock__registered__complete__full",
            matrix,
            matrix[-120:],
            descriptors(),
            missingness_policy="complete_case_common_window",
        )
        self.assertEqual(result.expanding.standardized_anchor_scalar.shape, (120,))
        self.assertTrue(np.all(np.isfinite(result.expanding.standardized_anchor_scalar)))

    def test_primary_envelope_and_b2_use_unique_analytic_identities(self) -> None:
        matrix = values()
        first = fit_scenario_pair(
            "a",
            matrix,
            matrix[-120:],
            descriptors(),
            missingness_policy="observed_ragged_edge",
        )
        altered = matrix.copy()
        altered[:, -1] += 0.05 * np.sin(np.arange(matrix.shape[0]) / 3.0)
        second = fit_scenario_pair(
            "b",
            altered,
            altered[-120:],
            descriptors(),
            missingness_policy="observed_ragged_edge",
        )
        envelope = envelope_record("2013-01", (first, second, first))
        combination = b2_record("2013-01", (first, second, first))
        self.assertEqual(envelope.analytic_scenario_count, 2)
        self.assertEqual(combination.analytic_scenario_count, 2)
        self.assertTrue(envelope.nondegenerate)
        self.assertTrue(combination.nondegenerate)

    def test_single_scenario_and_hostile_inputs(self) -> None:
        matrix = values()
        fit = fit_scenario_pair(
            "single",
            matrix,
            matrix[-120:],
            descriptors(),
            missingness_policy="observed_ragged_edge",
        )
        record = single_scenario_record("2013-01", fit)
        self.assertEqual(record.analytic_scenario_count, 1)
        self.assertFalse(envelope_record("2013-01", (fit, fit)).nondegenerate)
        self.assertFalse(b2_record("2013-01", (fit, fit)).nondegenerate)
        rotated = tuple(CHANNEL_ORDER[(index + 1) % 7] for index in range(6))
        controlled = fit_scenario_pair(
            "controlled",
            matrix,
            matrix[-120:],
            descriptors(),
            missingness_policy="observed_ragged_edge",
            channel_assignments=rotated,
        )
        self.assertEqual(controlled.expanding.channel_count, 6)
        pcp = fit_scenario_pair(
            "pcp",
            matrix,
            matrix[-120:],
            descriptors(),
            missingness_policy="observed_ragged_edge",
            pcp_lambda_multiplier=1.0,
        )
        self.assertEqual(pcp.expanding.standardized_anchor_scalar.shape, (120,))
        with self.assertRaisesRegex(StageAGeometryError, "Missingness"):
            fit_scenario_pair(
                "bad",
                matrix,
                matrix[-120:],
                descriptors(),
                missingness_policy="invented",
            )
        with self.assertRaisesRegex(StageAGeometryError, "PCP"):
            fit_scenario_pair(
                "bad-pcp",
                matrix,
                matrix[-120:],
                descriptors(),
                missingness_policy="complete_case_common_window",
                pcp_lambda_multiplier=1.0,
            )
        with self.assertRaisesRegex(StageAGeometryError, "descriptors"):
            fit_scenario_pair(
                "bad-channels",
                matrix,
                matrix[-120:],
                descriptors(),
                missingness_policy="observed_ragged_edge",
                channel_assignments=("prices_and_expectations",),
            )
        short = prepare_history(values(119), descriptors())
        with self.assertRaisesRegex(StageAGeometryError, "120-month"):
            fit_history_geometry(short, missingness_policy="observed_ragged_edge")
        history = prepare_history(matrix, descriptors())
        with self.assertRaisesRegex(StageAGeometryError, "retained series"):
            fit_history_geometry(
                history,
                missingness_policy="observed_ragged_edge",
                channel_assignments=("prices_and_expectations",),
            )


if __name__ == "__main__":
    unittest.main()
