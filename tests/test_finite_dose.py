import unittest

import numpy as np

from shockbridge_state_risk.transmission.finite_dose import (
    QUADRATIC_TENSOR_TERMS,
    FiniteDoseError,
    SurfaceScaling,
    audit_joint_support,
    evaluate_expected_finite_dose_contrast,
    evaluate_finite_dose_contrast,
    expected_quadratic_tensor_design,
    finite_dose_contrast_design,
    fit_surface_scaling,
    linear_interaction_design,
    observed_support_mask,
    quadratic_tensor_design,
)


class FiniteDoseSurfaceTests(unittest.TestCase):
    @staticmethod
    def _fixture() -> tuple[np.ndarray, np.ndarray]:
        shocks = np.asarray([-2.0, -1.4, -0.8, -0.2, 0.1, 0.5, 0.9, 1.3, 2.1])
        states = np.asarray([-1.5, -1.0, -0.6, -0.2, 0.0, 0.3, 0.7, 1.1, 1.6])
        return shocks, states

    def test_quadratic_surface_contains_linear_interaction_benchmark(self) -> None:
        shocks, states = self._fixture()
        scaling = fit_surface_scaling(shocks, states)
        quadratic = quadratic_tensor_design(shocks, states, scaling)
        linear = linear_interaction_design(shocks, states, scaling)
        self.assertEqual(quadratic.shape, (9, len(QUADRATIC_TENSOR_TERMS)))
        np.testing.assert_allclose(quadratic[:, [0, 1, 3, 4]], linear)
        self.assertAlmostEqual(float(np.mean(shocks - scaling.shock_location)), 0.0)
        self.assertAlmostEqual(float(np.mean(states - scaling.state_location)), 0.0)

    def test_finite_dose_contrast_matches_surface_prediction_difference(self) -> None:
        shocks, states = self._fixture()
        scaling = fit_surface_scaling(shocks, states)
        coefficients = np.arange(1.0, 10.0)
        doses = np.asarray([-1.0, 0.5, 1.5])
        evaluation_states = np.asarray([-0.7, 0.0, 0.9])
        contrast = evaluate_finite_dose_contrast(
            coefficients, evaluation_states, doses, scaling, baseline_dose=0.0
        )
        direct = (
            quadratic_tensor_design(doses, evaluation_states, scaling)
            - quadratic_tensor_design(np.zeros(3), evaluation_states, scaling)
        ) @ coefficients
        np.testing.assert_allclose(contrast, direct)
        design = finite_dose_contrast_design(evaluation_states, doses, scaling)
        np.testing.assert_allclose(design[:, :3], 0.0)

    def test_support_mask_blocks_rectangular_extrapolation(self) -> None:
        shocks, states = self._fixture()
        mask = observed_support_mask(
            np.asarray([-1.0, 0.0, 2.0]),
            np.asarray([-1.0, 0.0, 0.5]),
            states,
            shocks,
        )
        np.testing.assert_array_equal(mask, np.asarray([True, True, False]))

    def test_state_uncertainty_is_integrated_analytically(self) -> None:
        shocks, states = self._fixture()
        scaling = fit_surface_scaling(shocks, states)
        means = np.asarray([-0.5, 0.0, 0.8])
        variances = np.asarray([0.0, 0.2, 0.5])
        doses = np.asarray([-1.0, 0.5, 1.5])
        expected = expected_quadratic_tensor_design(doses, means, variances, scaling)
        point = quadratic_tensor_design(doses, means, scaling)
        np.testing.assert_allclose(expected[0], point[0])
        adjustment = variances / scaling.state_scale**2
        np.testing.assert_allclose(expected[:, 2] - point[:, 2], adjustment)
        np.testing.assert_allclose(expected[:, 5] - point[:, 5], expected[:, 3] * adjustment)
        np.testing.assert_allclose(expected[:, 8] - point[:, 8], expected[:, 6] * adjustment)
        coefficients = np.arange(1.0, 10.0)
        contrast = evaluate_expected_finite_dose_contrast(
            coefficients, means, variances, doses, scaling
        )
        self.assertTrue(np.all(np.isfinite(contrast)))

    def test_joint_support_requires_both_endpoints_and_local_ess(self) -> None:
        grid = np.asarray([-1.0, 0.0, 1.0])
        observed_shocks, observed_states = np.meshgrid(grid, grid)
        shocks = observed_shocks.ravel()
        states = observed_states.ravel()
        scaling = fit_surface_scaling(shocks, states)
        audit = audit_joint_support(
            states=np.asarray([0.0, 0.0, 1.5]),
            doses=np.asarray([0.5, 2.0, 0.0]),
            observed_states=states,
            observed_shocks=shocks,
            scaling=scaling,
            bandwidth_standard_deviations=1.0,
            minimum_local_effective_sample_size=2.0,
        )
        np.testing.assert_array_equal(audit.eligible, np.asarray([True, False, False]))
        self.assertTrue(audit.treated_inside_convex_hull[0])
        self.assertFalse(audit.treated_inside_convex_hull[1])
        self.assertFalse(audit.baseline_inside_convex_hull[2])
        self.assertGreater(audit.treated_local_effective_sample_size[0], 2.0)

    def test_invalid_inputs_fail_closed(self) -> None:
        shocks, states = self._fixture()
        scaling = fit_surface_scaling(shocks, states)
        with self.assertRaisesRegex(FiniteDoseError, "at least nine"):
            fit_surface_scaling(shocks[:-1], states[:-1])
        with self.assertRaisesRegex(FiniteDoseError, "both vary"):
            fit_surface_scaling(shocks, np.ones_like(states))
        with self.assertRaisesRegex(FiniteDoseError, "paired one-dimensional"):
            quadratic_tensor_design(shocks[:-1], states, scaling)
        with self.assertRaisesRegex(FiniteDoseError, "paired one-dimensional"):
            quadratic_tensor_design(shocks[:, None], states[:, None], scaling)
        invalid_scaling = SurfaceScaling(np.nan, 1.0, 0.0, 1.0)
        with self.assertRaisesRegex(FiniteDoseError, "parameters must be finite"):
            quadratic_tensor_design(shocks, states, invalid_scaling)
        with self.assertRaisesRegex(FiniteDoseError, "nine finite"):
            evaluate_finite_dose_contrast(np.ones(8), states, shocks, scaling)
        with self.assertRaisesRegex(FiniteDoseError, "cannot be negative"):
            expected_quadratic_tensor_design(shocks, states, -np.ones(9), scaling)
        with self.assertRaisesRegex(FiniteDoseError, "invalid shapes"):
            observed_support_mask(states[:-1], shocks, states, shocks)
        with self.assertRaisesRegex(FiniteDoseError, "bandwidth and ESS"):
            audit_joint_support(states, shocks, states, shocks, scaling, 0.0, 2.0)


if __name__ == "__main__":
    unittest.main()
