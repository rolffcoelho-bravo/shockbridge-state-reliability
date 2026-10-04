import unittest

import numpy as np

from shockbridge_state_risk.transmission.spline import (
    SplineError,
    TensorSplineSpecification,
    fit_penalized_spline,
    fit_tensor_spline_specification,
    select_penalty_expanding_window,
    tensor_second_difference_penalty,
    tensor_spline_design,
)


class TensorSplineTests(unittest.TestCase):
    @staticmethod
    def _fixture(rows: int = 120) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        index = np.arange(rows, dtype=np.float64)
        shocks = np.linspace(-2.0, 2.0, rows)
        states = np.sin(index / 13.0)
        outcomes = 0.5 * shocks + 0.3 * states + 0.2 * shocks * states + 0.05 * np.cos(index)
        return shocks, states, outcomes

    def test_minimal_cubic_tensor_basis_and_penalty_are_valid(self) -> None:
        shocks, states, _ = self._fixture()
        specification = fit_tensor_spline_specification(shocks, states)
        self.assertEqual(specification.shock_basis_count, 5)
        self.assertEqual(specification.state_basis_count, 5)
        self.assertEqual(specification.tensor_basis_count, 25)
        design = tensor_spline_design(shocks, states, specification)
        self.assertEqual(design.shape, (120, 25))
        np.testing.assert_allclose(np.sum(design, axis=1), 1.0, atol=1e-12)
        self.assertTrue(np.all(design >= 0.0))
        penalty = tensor_second_difference_penalty(specification)
        np.testing.assert_allclose(penalty, penalty.T)
        self.assertGreaterEqual(float(np.min(np.linalg.eigvalsh(penalty))), -1e-12)

    def test_penalty_selection_is_forward_only_and_reproducible(self) -> None:
        shocks, states, outcomes = self._fixture()
        specification = fit_tensor_spline_specification(shocks, states)
        design = tensor_spline_design(shocks, states, specification)
        curvature = tensor_second_difference_penalty(specification)
        penalties = (0.01, 0.1, 1.0, 10.0, 100.0)
        first = select_penalty_expanding_window(design, outcomes, curvature, penalties, 60, 20)
        second = select_penalty_expanding_window(
            design.copy(), outcomes.copy(), curvature.copy(), penalties, 60, 20
        )
        self.assertEqual(first, second)
        self.assertEqual([fold.validation_start for fold in first.folds], [60, 80, 100])
        self.assertIn(first.selected_penalty, penalties)
        self.assertEqual(
            first.basis_freeze_requirement,
            "FROZEN_FROM_OUTER_DEVELOPMENT_BLOCK",
        )
        coefficients = fit_penalized_spline(design, outcomes, curvature, first.selected_penalty)
        self.assertEqual(coefficients.shape, (25,))
        self.assertTrue(np.all(np.isfinite(coefficients)))

    def test_invalid_spline_inputs_fail_closed(self) -> None:
        shocks, states, outcomes = self._fixture()
        with self.assertRaisesRegex(SplineError, "25 paired"):
            fit_tensor_spline_specification(shocks[:20], states[:20])
        with self.assertRaisesRegex(SplineError, "cubic"):
            fit_tensor_spline_specification(shocks, states, degree=2)
        with self.assertRaisesRegex(SplineError, "quantiles"):
            fit_tensor_spline_specification(shocks, states, interior_quantiles=(0.5, 0.5))
        specification = fit_tensor_spline_specification(shocks, states)
        with self.assertRaisesRegex(SplineError, "outside frozen"):
            tensor_spline_design(np.asarray([3.0]), np.asarray([0.0]), specification)
        malformed = TensorSplineSpecification(3, (1.0, -1.0), (-1.0, 1.0), (0.0,), (0.0,))
        with self.assertRaisesRegex(SplineError, "boundaries"):
            tensor_second_difference_penalty(malformed)
        design = tensor_spline_design(shocks, states, specification)
        curvature = tensor_second_difference_penalty(specification)
        with self.assertRaisesRegex(SplineError, "finite and positive"):
            fit_penalized_spline(design, outcomes, curvature, 0.0)
        asymmetric = curvature.copy()
        asymmetric[0, 1] += 1.0
        with self.assertRaisesRegex(SplineError, "symmetric"):
            fit_penalized_spline(design, outcomes, asymmetric, 1.0)
        with self.assertRaisesRegex(SplineError, "strictly increasing"):
            select_penalty_expanding_window(design, outcomes, curvature, (1.0, 0.1), 60, 20)


if __name__ == "__main__":
    unittest.main()
