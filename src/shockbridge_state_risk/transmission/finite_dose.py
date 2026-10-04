"""Prospective finite-dose quadratic shock-by-state response surface."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from shockbridge_state_risk.state.hmm import FloatArray


class FiniteDoseError(ValueError):
    """Raised when a finite-dose surface violates its frozen design contract."""


QUADRATIC_TENSOR_TERMS = (
    "intercept",
    "state",
    "state_squared",
    "shock",
    "shock_by_state",
    "shock_by_state_squared",
    "shock_squared",
    "shock_squared_by_state",
    "shock_squared_by_state_squared",
)

LINEAR_INTERACTION_TERMS = (
    "intercept",
    "state",
    "shock",
    "shock_by_state",
)


@dataclass(frozen=True)
class SurfaceScaling:
    shock_location: float
    shock_scale: float
    state_location: float
    state_scale: float


@dataclass(frozen=True)
class JointSupportAudit:
    treated_inside_convex_hull: NDArray[np.bool_]
    baseline_inside_convex_hull: NDArray[np.bool_]
    treated_local_effective_sample_size: FloatArray
    baseline_local_effective_sample_size: FloatArray
    eligible: NDArray[np.bool_]
    bandwidth_standard_deviations: float
    minimum_local_effective_sample_size: float


def fit_surface_scaling(shocks: FloatArray, states: FloatArray) -> SurfaceScaling:
    """Fit outcome-blind scaling moments on the admissible analysis sample."""
    shock = np.asarray(shocks, dtype=np.float64)
    state = np.asarray(states, dtype=np.float64)
    if shock.ndim != 1 or state.shape != shock.shape or shock.size < 9:
        raise FiniteDoseError("Surface scaling requires paired vectors with at least nine rows.")
    if np.any(~np.isfinite(shock)) or np.any(~np.isfinite(state)):
        raise FiniteDoseError("Surface scaling inputs must be finite.")
    shock_scale = float(np.std(shock))
    state_scale = float(np.std(state))
    if shock_scale <= 1e-12 or state_scale <= 1e-12:
        raise FiniteDoseError("Shock and state must both vary in the analysis sample.")
    return SurfaceScaling(
        shock_location=float(np.mean(shock)),
        shock_scale=shock_scale,
        state_location=float(np.mean(state)),
        state_scale=state_scale,
    )


def _standardize(
    shocks: FloatArray, states: FloatArray, scaling: SurfaceScaling
) -> tuple[FloatArray, FloatArray]:
    shock = np.asarray(shocks, dtype=np.float64)
    state = np.asarray(states, dtype=np.float64)
    if shock.ndim != 1 or state.shape != shock.shape:
        raise FiniteDoseError("Shock and state arrays must be paired one-dimensional vectors.")
    if np.any(~np.isfinite(shock)) or np.any(~np.isfinite(state)):
        raise FiniteDoseError("Finite-dose inputs must be finite.")
    scaling_values = (
        scaling.shock_location,
        scaling.shock_scale,
        scaling.state_location,
        scaling.state_scale,
    )
    if any(not np.isfinite(value) for value in scaling_values):
        raise FiniteDoseError("Finite-dose scaling parameters must be finite.")
    if scaling.shock_scale <= 0 or scaling.state_scale <= 0:
        raise FiniteDoseError("Finite-dose scales must be positive.")
    return (
        (shock - scaling.shock_location) / scaling.shock_scale,
        (state - scaling.state_location) / scaling.state_scale,
    )


def quadratic_tensor_design(
    shocks: FloatArray, states: FloatArray, scaling: SurfaceScaling
) -> FloatArray:
    """Return the frozen hierarchical 3-by-3 polynomial tensor basis."""
    shock, state = _standardize(shocks, states, scaling)
    return np.column_stack(
        (
            np.ones(shock.size),
            state,
            state**2,
            shock,
            shock * state,
            shock * state**2,
            shock**2,
            shock**2 * state,
            shock**2 * state**2,
        )
    )


def linear_interaction_design(
    shocks: FloatArray, states: FloatArray, scaling: SurfaceScaling
) -> FloatArray:
    """Return the transparent linear shock-by-state benchmark basis."""
    shock, state = _standardize(shocks, states, scaling)
    return np.column_stack((np.ones(shock.size), state, shock, shock * state))


def finite_dose_contrast_design(
    states: FloatArray,
    doses: FloatArray,
    scaling: SurfaceScaling,
    baseline_dose: float = 0.0,
) -> FloatArray:
    """Return basis differences g(dose, state) - g(baseline, state)."""
    state = np.asarray(states, dtype=np.float64)
    dose = np.asarray(doses, dtype=np.float64)
    if state.shape != dose.shape:
        raise FiniteDoseError("Dose contrasts require paired state and dose arrays.")
    baseline = np.full(dose.shape, baseline_dose, dtype=np.float64)
    return quadratic_tensor_design(dose, state, scaling) - quadratic_tensor_design(
        baseline, state, scaling
    )


def evaluate_finite_dose_contrast(
    coefficients: FloatArray,
    states: FloatArray,
    doses: FloatArray,
    scaling: SurfaceScaling,
    baseline_dose: float = 0.0,
) -> FloatArray:
    """Evaluate a finite-dose contrast from nine surface coefficients."""
    beta = np.asarray(coefficients, dtype=np.float64)
    if beta.shape != (len(QUADRATIC_TENSOR_TERMS),) or np.any(~np.isfinite(beta)):
        raise FiniteDoseError("The quadratic response surface requires nine finite coefficients.")
    return finite_dose_contrast_design(states, doses, scaling, baseline_dose) @ beta


def expected_quadratic_tensor_design(
    shocks: FloatArray,
    state_means: FloatArray,
    state_variances: FloatArray,
    scaling: SurfaceScaling,
) -> FloatArray:
    """Integrate the quadratic basis over a state distribution's first two moments."""
    shock, state_mean = _standardize(shocks, state_means, scaling)
    variance = np.asarray(state_variances, dtype=np.float64)
    if variance.shape != state_mean.shape or np.any(~np.isfinite(variance)):
        raise FiniteDoseError("State variances must be finite and paired with state means.")
    if np.any(variance < 0):
        raise FiniteDoseError("State variances cannot be negative.")
    standardized_second_moment = state_mean**2 + variance / scaling.state_scale**2
    return np.column_stack(
        (
            np.ones(shock.size),
            state_mean,
            standardized_second_moment,
            shock,
            shock * state_mean,
            shock * standardized_second_moment,
            shock**2,
            shock**2 * state_mean,
            shock**2 * standardized_second_moment,
        )
    )


def expected_finite_dose_contrast_design(
    state_means: FloatArray,
    state_variances: FloatArray,
    doses: FloatArray,
    scaling: SurfaceScaling,
    baseline_dose: float = 0.0,
) -> FloatArray:
    """Return finite-dose contrasts integrated over filtered state uncertainty."""
    dose = np.asarray(doses, dtype=np.float64)
    baseline = np.full(dose.shape, baseline_dose, dtype=np.float64)
    return expected_quadratic_tensor_design(
        dose, state_means, state_variances, scaling
    ) - expected_quadratic_tensor_design(baseline, state_means, state_variances, scaling)


def evaluate_expected_finite_dose_contrast(
    coefficients: FloatArray,
    state_means: FloatArray,
    state_variances: FloatArray,
    doses: FloatArray,
    scaling: SurfaceScaling,
    baseline_dose: float = 0.0,
) -> FloatArray:
    """Evaluate an uncertainty-integrated finite-dose response contrast."""
    beta = np.asarray(coefficients, dtype=np.float64)
    if beta.shape != (len(QUADRATIC_TENSOR_TERMS),) or np.any(~np.isfinite(beta)):
        raise FiniteDoseError("The quadratic response surface requires nine finite coefficients.")
    return (
        expected_finite_dose_contrast_design(
            state_means,
            state_variances,
            doses,
            scaling,
            baseline_dose,
        )
        @ beta
    )


def observed_support_mask(
    states: FloatArray,
    doses: FloatArray,
    observed_states: FloatArray,
    observed_shocks: FloatArray,
) -> NDArray[np.bool_]:
    """Identify requested state-dose points inside the rectangular observed support."""
    state = np.asarray(states, dtype=np.float64)
    dose = np.asarray(doses, dtype=np.float64)
    historical_state = np.asarray(observed_states, dtype=np.float64)
    historical_shock = np.asarray(observed_shocks, dtype=np.float64)
    arrays = (state, dose, historical_state, historical_shock)
    if (
        state.ndim != 1
        or dose.shape != state.shape
        or historical_state.ndim != 1
        or historical_shock.shape != historical_state.shape
    ):
        raise FiniteDoseError("Observed-support inputs have invalid shapes.")
    if historical_state.size == 0 or historical_shock.size == 0:
        raise FiniteDoseError("Observed support cannot be empty.")
    if any(np.any(~np.isfinite(array)) for array in arrays):
        raise FiniteDoseError("Observed-support inputs must be finite.")
    return (
        (state >= np.min(historical_state))
        & (state <= np.max(historical_state))
        & (dose >= np.min(historical_shock))
        & (dose <= np.max(historical_shock))
    )


def _cross(origin: FloatArray, left: FloatArray, right: FloatArray) -> float:
    return float(
        (left[0] - origin[0]) * (right[1] - origin[1])
        - (left[1] - origin[1]) * (right[0] - origin[0])
    )


def _convex_hull(points: FloatArray) -> FloatArray:
    unique = np.unique(points, axis=0)
    if unique.shape[0] < 3:
        raise FiniteDoseError("Joint support requires at least three distinct points.")
    order = np.lexsort((unique[:, 1], unique[:, 0]))
    ordered = unique[order]
    lower: list[FloatArray] = []
    for point in ordered:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper: list[FloatArray] = []
    for point in ordered[::-1]:
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    hull = np.asarray([*lower[:-1], *upper[:-1]], dtype=np.float64)
    if hull.shape[0] < 3:
        raise FiniteDoseError("Joint support points are collinear.")
    return hull


def _inside_convex_hull(points: FloatArray, hull: FloatArray) -> NDArray[np.bool_]:
    inside = np.ones(points.shape[0], dtype=np.bool_)
    tolerance = 1e-12
    for index in range(hull.shape[0]):
        start = hull[index]
        stop = hull[(index + 1) % hull.shape[0]]
        crosses = (stop[0] - start[0]) * (points[:, 1] - start[1]) - (stop[1] - start[1]) * (
            points[:, 0] - start[0]
        )
        inside &= crosses >= -tolerance
    return inside


def _local_effective_sample_size(
    queries: FloatArray, observations: FloatArray, bandwidth: float
) -> FloatArray:
    squared_distances = np.sum((queries[:, None, :] - observations[None, :, :]) ** 2, axis=2)
    weights = np.exp(-0.5 * squared_distances / bandwidth**2)
    sums = np.sum(weights, axis=1)
    squared_sums = np.sum(weights**2, axis=1)
    return np.asarray(
        np.divide(
            sums**2,
            squared_sums,
            out=np.zeros_like(sums),
            where=squared_sums > 0,
        ),
        dtype=np.float64,
    )


def audit_joint_support(
    states: FloatArray,
    doses: FloatArray,
    observed_states: FloatArray,
    observed_shocks: FloatArray,
    scaling: SurfaceScaling,
    bandwidth_standard_deviations: float,
    minimum_local_effective_sample_size: float,
    baseline_dose: float = 0.0,
) -> JointSupportAudit:
    """Require convex-hull membership and local support at both contrast endpoints."""
    state = np.asarray(states, dtype=np.float64)
    dose = np.asarray(doses, dtype=np.float64)
    historical_state = np.asarray(observed_states, dtype=np.float64)
    historical_shock = np.asarray(observed_shocks, dtype=np.float64)
    if (
        state.ndim != 1
        or dose.shape != state.shape
        or historical_state.ndim != 1
        or historical_shock.shape != historical_state.shape
        or historical_state.size < 3
    ):
        raise FiniteDoseError("Joint-support inputs have invalid shapes.")
    arrays = (state, dose, historical_state, historical_shock)
    if any(np.any(~np.isfinite(array)) for array in arrays):
        raise FiniteDoseError("Joint-support inputs must be finite.")
    if (
        not np.isfinite(bandwidth_standard_deviations)
        or bandwidth_standard_deviations <= 0
        or not np.isfinite(minimum_local_effective_sample_size)
        or minimum_local_effective_sample_size <= 0
        or minimum_local_effective_sample_size > historical_state.size
    ):
        raise FiniteDoseError("Joint-support bandwidth and ESS threshold are invalid.")
    standardized_shocks, standardized_states = _standardize(
        historical_shock, historical_state, scaling
    )
    observations = np.column_stack((standardized_shocks, standardized_states))
    hull = _convex_hull(observations)
    treated_shocks, query_states = _standardize(dose, state, scaling)
    baseline_shocks, _ = _standardize(
        np.full(dose.shape, baseline_dose, dtype=np.float64), state, scaling
    )
    treated_queries = np.column_stack((treated_shocks, query_states))
    baseline_queries = np.column_stack((baseline_shocks, query_states))
    treated_inside = _inside_convex_hull(treated_queries, hull)
    baseline_inside = _inside_convex_hull(baseline_queries, hull)
    treated_ess = _local_effective_sample_size(
        treated_queries, observations, bandwidth_standard_deviations
    )
    baseline_ess = _local_effective_sample_size(
        baseline_queries, observations, bandwidth_standard_deviations
    )
    eligible = (
        treated_inside
        & baseline_inside
        & (treated_ess >= minimum_local_effective_sample_size)
        & (baseline_ess >= minimum_local_effective_sample_size)
    )
    return JointSupportAudit(
        treated_inside_convex_hull=treated_inside,
        baseline_inside_convex_hull=baseline_inside,
        treated_local_effective_sample_size=treated_ess,
        baseline_local_effective_sample_size=baseline_ess,
        eligible=eligible,
        bandwidth_standard_deviations=bandwidth_standard_deviations,
        minimum_local_effective_sample_size=minimum_local_effective_sample_size,
    )
