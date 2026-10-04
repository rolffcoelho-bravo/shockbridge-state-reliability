"""Penalized tensor-product spline robustness model with chronological tuning."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from shockbridge_state_risk.state.hmm import FloatArray


class SplineError(ValueError):
    """Raised when a spline robustness specification is invalid."""


@dataclass(frozen=True)
class TensorSplineSpecification:
    degree: int
    shock_boundary: tuple[float, float]
    state_boundary: tuple[float, float]
    shock_interior_knots: tuple[float, ...]
    state_interior_knots: tuple[float, ...]

    @property
    def shock_basis_count(self) -> int:
        return len(self.shock_interior_knots) + self.degree + 1

    @property
    def state_basis_count(self) -> int:
        return len(self.state_interior_knots) + self.degree + 1

    @property
    def tensor_basis_count(self) -> int:
        return self.shock_basis_count * self.state_basis_count


@dataclass(frozen=True)
class SplinePenaltyFold:
    training_rows: int
    validation_start: int
    validation_stop: int
    mean_squared_errors: tuple[float, ...]


@dataclass(frozen=True)
class SplinePenaltySelection:
    penalties: tuple[float, ...]
    folds: tuple[SplinePenaltyFold, ...]
    mean_validation_errors: tuple[float, ...]
    selected_penalty: float
    basis_freeze_requirement: str = "FROZEN_FROM_OUTER_DEVELOPMENT_BLOCK"


def _validate_specification(specification: TensorSplineSpecification) -> None:
    values = (
        *specification.shock_boundary,
        *specification.state_boundary,
        *specification.shock_interior_knots,
        *specification.state_interior_knots,
    )
    if specification.degree != 3 or any(not np.isfinite(value) for value in values):
        raise SplineError("Spline specification must be finite and cubic.")
    for boundary, interior in (
        (specification.shock_boundary, specification.shock_interior_knots),
        (specification.state_boundary, specification.state_interior_knots),
    ):
        if boundary[0] >= boundary[1]:
            raise SplineError("Spline boundaries must be strictly increasing.")
        if (
            not interior
            or any(value <= boundary[0] or value >= boundary[1] for value in interior)
            or any(right <= left for left, right in zip(interior, interior[1:]))
        ):
            raise SplineError("Spline interior knots must be ordered inside the boundaries.")


def fit_tensor_spline_specification(
    shocks: FloatArray,
    states: FloatArray,
    degree: int = 3,
    interior_quantiles: tuple[float, ...] = (0.5,),
) -> TensorSplineSpecification:
    """Freeze outcome-blind knots and boundaries from an outer development block."""
    shock = np.asarray(shocks, dtype=np.float64)
    state = np.asarray(states, dtype=np.float64)
    if shock.ndim != 1 or state.shape != shock.shape or shock.size < 25:
        raise SplineError("Spline specification requires 25 paired finite observations.")
    if np.any(~np.isfinite(shock)) or np.any(~np.isfinite(state)):
        raise SplineError("Spline specification inputs must be finite.")
    if degree != 3:
        raise SplineError("The frozen robustness family uses cubic marginal splines.")
    if (
        not interior_quantiles
        or any(not np.isfinite(value) or not 0.0 < value < 1.0 for value in interior_quantiles)
        or any(right <= left for left, right in zip(interior_quantiles, interior_quantiles[1:]))
    ):
        raise SplineError("Interior-knot quantiles must be finite, unique, and increasing.")
    shock_boundary = (float(np.min(shock)), float(np.max(shock)))
    state_boundary = (float(np.min(state)), float(np.max(state)))
    if shock_boundary[0] == shock_boundary[1] or state_boundary[0] == state_boundary[1]:
        raise SplineError("Shock and state must vary for spline construction.")
    shock_knots = tuple(float(value) for value in np.quantile(shock, interior_quantiles))
    state_knots = tuple(float(value) for value in np.quantile(state, interior_quantiles))
    if len(set(shock_knots)) != len(shock_knots) or len(set(state_knots)) != len(state_knots):
        raise SplineError("Spline interior knots collapse under the observed distribution.")
    return TensorSplineSpecification(
        degree=degree,
        shock_boundary=shock_boundary,
        state_boundary=state_boundary,
        shock_interior_knots=shock_knots,
        state_interior_knots=state_knots,
    )


def _open_knot_vector(
    boundary: tuple[float, float], interior: tuple[float, ...], degree: int
) -> FloatArray:
    left, right = boundary
    values = (left,) * (degree + 1) + interior + (right,) * (degree + 1)
    return np.asarray(values, dtype=np.float64)


def _bspline_basis(
    values: FloatArray,
    boundary: tuple[float, float],
    interior: tuple[float, ...],
    degree: int,
) -> FloatArray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or np.any(~np.isfinite(array)):
        raise SplineError("Spline evaluation requires a finite one-dimensional vector.")
    left, right = boundary
    if np.any(array < left) or np.any(array > right):
        raise SplineError("Spline evaluation outside frozen boundaries is prohibited.")
    knots = _open_knot_vector(boundary, interior, degree)
    basis = np.zeros((array.size, knots.size - 1), dtype=np.float64)
    for index in range(knots.size - 1):
        basis[:, index] = (array >= knots[index]) & (array < knots[index + 1])
    for order in range(1, degree + 1):
        updated = np.zeros((array.size, basis.shape[1] - 1), dtype=np.float64)
        for index in range(updated.shape[1]):
            left_denominator = knots[index + order] - knots[index]
            right_denominator = knots[index + order + 1] - knots[index + 1]
            if left_denominator > 0:
                updated[:, index] += (array - knots[index]) / left_denominator * basis[:, index]
            if right_denominator > 0:
                updated[:, index] += (
                    (knots[index + order + 1] - array) / right_denominator * basis[:, index + 1]
                )
        basis = updated
    basis[array == right, :] = 0.0
    basis[array == right, -1] = 1.0
    return basis


def tensor_spline_design(
    shocks: FloatArray, states: FloatArray, specification: TensorSplineSpecification
) -> FloatArray:
    """Construct the row-wise tensor product of marginal cubic B-spline bases."""
    shock = np.asarray(shocks, dtype=np.float64)
    state = np.asarray(states, dtype=np.float64)
    if shock.ndim != 1 or state.shape != shock.shape:
        raise SplineError("Spline shock and state inputs must be paired vectors.")
    _validate_specification(specification)
    shock_basis = _bspline_basis(
        shock,
        specification.shock_boundary,
        specification.shock_interior_knots,
        specification.degree,
    )
    state_basis = _bspline_basis(
        state,
        specification.state_boundary,
        specification.state_interior_knots,
        specification.degree,
    )
    return np.asarray(
        np.einsum("ni,nj->nij", shock_basis, state_basis).reshape(shock.size, -1),
        dtype=np.float64,
    )


def tensor_second_difference_penalty(specification: TensorSplineSpecification) -> FloatArray:
    """Return the Kronecker-sum curvature penalty for the tensor coefficients."""
    _validate_specification(specification)
    shock_count = specification.shock_basis_count
    state_count = specification.state_basis_count

    def second_difference(count: int) -> FloatArray:
        matrix = np.zeros((count - 2, count), dtype=np.float64)
        for row in range(count - 2):
            matrix[row, row : row + 3] = (1.0, -2.0, 1.0)
        return matrix

    shock_difference = second_difference(shock_count)
    state_difference = second_difference(state_count)
    return np.asarray(
        np.kron(shock_difference.T @ shock_difference, np.eye(state_count))
        + np.kron(np.eye(shock_count), state_difference.T @ state_difference),
        dtype=np.float64,
    )


def fit_penalized_spline(
    design: FloatArray,
    outcomes: FloatArray,
    penalty_matrix: FloatArray,
    penalty: float,
) -> FloatArray:
    """Fit penalized least squares for a fixed, prospectively supplied penalty."""
    matrix = np.asarray(design, dtype=np.float64)
    target = np.asarray(outcomes, dtype=np.float64)
    curvature = np.asarray(penalty_matrix, dtype=np.float64)
    if matrix.ndim != 2 or target.shape != (matrix.shape[0],) or matrix.shape[0] == 0:
        raise SplineError("Penalized spline design and outcome shapes are invalid.")
    if curvature.shape != (matrix.shape[1], matrix.shape[1]):
        raise SplineError("Spline penalty matrix has an invalid shape.")
    if (
        np.any(~np.isfinite(matrix))
        or np.any(~np.isfinite(target))
        or np.any(~np.isfinite(curvature))
        or not np.isfinite(penalty)
        or penalty <= 0
    ):
        raise SplineError("Penalized spline inputs and penalty must be finite and positive.")
    if not np.allclose(curvature, curvature.T, rtol=0.0, atol=1e-10):
        raise SplineError("Spline penalty matrix must be symmetric.")
    eigenvalues, eigenvectors = np.linalg.eigh(curvature)
    if float(np.min(eigenvalues)) < -1e-10:
        raise SplineError("Spline penalty matrix must be positive semidefinite.")
    penalty_root = np.sqrt(penalty * np.clip(eigenvalues, 0.0, None))[:, None] * eigenvectors.T
    augmented_design = np.vstack((matrix, penalty_root))
    augmented_target = np.concatenate((target, np.zeros(matrix.shape[1], dtype=np.float64)))
    coefficients, _, rank, _ = np.linalg.lstsq(augmented_design, augmented_target, rcond=None)
    if rank < matrix.shape[1]:
        raise SplineError("Penalized spline system is not identified.")
    return np.asarray(coefficients, dtype=np.float64)


def select_penalty_expanding_window(
    design: FloatArray,
    outcomes: FloatArray,
    penalty_matrix: FloatArray,
    penalties: tuple[float, ...],
    initial_training_rows: int,
    validation_rows: int,
) -> SplinePenaltySelection:
    """Tune a basis frozen outside this routine by forward-only validation folds."""
    matrix = np.asarray(design, dtype=np.float64)
    target = np.asarray(outcomes, dtype=np.float64)
    if (
        not penalties
        or any(not np.isfinite(value) or value <= 0 for value in penalties)
        or any(right <= left for left, right in zip(penalties, penalties[1:]))
    ):
        raise SplineError("The spline penalty grid must be positive and strictly increasing.")
    if (
        matrix.ndim != 2
        or target.shape != (matrix.shape[0],)
        or initial_training_rows < matrix.shape[1]
        or validation_rows < 1
        or initial_training_rows + validation_rows > matrix.shape[0]
    ):
        raise SplineError("Expanding-window spline validation settings are invalid.")
    folds: list[SplinePenaltyFold] = []
    all_squared_error_sums = np.zeros(len(penalties), dtype=np.float64)
    total_validation_rows = 0
    for start in range(initial_training_rows, matrix.shape[0], validation_rows):
        stop = min(start + validation_rows, matrix.shape[0])
        errors: list[float] = []
        for index, penalty in enumerate(penalties):
            coefficients = fit_penalized_spline(
                matrix[:start], target[:start], penalty_matrix, penalty
            )
            residuals = target[start:stop] - matrix[start:stop] @ coefficients
            error = float(np.mean(residuals**2))
            errors.append(error)
            all_squared_error_sums[index] += float(np.sum(residuals**2))
        folds.append(SplinePenaltyFold(start, start, stop, tuple(errors)))
        total_validation_rows += stop - start
    mean_errors = tuple(float(value / total_validation_rows) for value in all_squared_error_sums)
    selected_index = int(np.argmin(mean_errors))
    return SplinePenaltySelection(
        penalties=penalties,
        folds=tuple(folds),
        mean_validation_errors=mean_errors,
        selected_penalty=penalties[selected_index],
    )
