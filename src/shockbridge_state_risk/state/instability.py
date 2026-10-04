"""Finite-dimensional diagnostics for the prospective Run 009 instability audit."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
from numpy.typing import NDArray

from shockbridge_state_risk.state.hmm import FloatArray


class InstabilityError(ValueError):
    """Raised when an instability diagnostic cannot satisfy its contract."""


@dataclass(frozen=True)
class GramGeometry:
    expanding_gram: FloatArray
    rolling_gram: FloatArray
    expanding_eigenvalues: FloatArray
    rolling_eigenvalues: FloatArray
    principal_cosines: FloatArray
    normalized_projector_distance: float
    gram_spectral_distance: float
    gram_normalized_frobenius_distance: float
    expanding_absolute_eigengap: float
    rolling_absolute_eigengap: float
    expanding_relative_eigengap: float
    rolling_relative_eigengap: float
    perturbation_to_minimum_eigengap_ratio: float
    upper_triangle_drift_contribution: FloatArray


@dataclass(frozen=True)
class StandardizationDrift:
    location_shift: FloatArray
    log_scale_ratio: FloatArray
    expanding_missing_rate: FloatArray
    rolling_missing_rate: FloatArray


@dataclass(frozen=True)
class SignMateriality:
    observations: int
    disagreements: int
    disagreement_rate: float
    substantive_disagreements: int
    substantive_disagreement_rate: float
    substantive_share_of_disagreements: float


@dataclass(frozen=True)
class BreachEpisode:
    start_month: str
    end_month: str
    duration_months: int
    breach_months: int
    open_at_sample_end: bool


def _history(values: FloatArray, context: str) -> FloatArray:
    matrix = np.asarray(values, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] < 8 or matrix.shape[1] < 2:
        raise InstabilityError(f"{context} must be a two-dimensional feature history.")
    if np.any(np.isinf(matrix)):
        raise InstabilityError(f"{context} cannot contain infinities.")
    if np.any(np.sum(np.isfinite(matrix), axis=0) < 2):
        raise InstabilityError(f"Every {context} feature needs two observations.")
    return matrix


def _moments(values: FloatArray) -> tuple[FloatArray, FloatArray, FloatArray]:
    means = np.nanmean(values, axis=0)
    scales = np.nanstd(values, axis=0)
    if np.any(scales < 1e-8):
        raise InstabilityError("Instability diagnostics require variable features.")
    standardized = (values - means) / scales
    filled = np.where(np.isfinite(standardized), standardized, 0.0)
    return means, scales, filled


def _gram(values: FloatArray) -> tuple[FloatArray, FloatArray, FloatArray]:
    means, scales, standardized = _moments(values)
    gram = standardized.T @ standardized / values.shape[0]
    return means, scales, np.asarray(gram, dtype=np.float64)


def gram_geometry(
    expanding: FloatArray,
    rolling: FloatArray,
    factor_dimension: int = 2,
) -> GramGeometry:
    """Compare the exact standardized Gram matrices underlying window-specific PCA."""
    left = _history(expanding, "expanding history")
    right = _history(rolling, "rolling history")
    if left.shape[1] != right.shape[1]:
        raise InstabilityError("Compared histories must have the same features.")
    if (
        isinstance(factor_dimension, bool)
        or factor_dimension < 1
        or factor_dimension >= left.shape[1]
    ):
        raise InstabilityError("The diagnostic factor dimension is invalid.")
    _, _, left_gram = _gram(left)
    _, _, right_gram = _gram(right)
    left_values, left_vectors = np.linalg.eigh(left_gram)
    right_values, right_vectors = np.linalg.eigh(right_gram)
    left_order = np.argsort(left_values)[::-1]
    right_order = np.argsort(right_values)[::-1]
    left_values = left_values[left_order]
    right_values = right_values[right_order]
    left_basis = left_vectors[:, left_order[:factor_dimension]]
    right_basis = right_vectors[:, right_order[:factor_dimension]]
    principal_cosines = np.clip(
        np.linalg.svd(left_basis.T @ right_basis, compute_uv=False), 0.0, 1.0
    )
    left_projector = left_basis @ left_basis.T
    right_projector = right_basis @ right_basis.T
    projector_distance = float(
        np.linalg.norm(left_projector - right_projector, ord="fro")
        / np.sqrt(2.0 * factor_dimension)
    )
    difference = right_gram - left_gram
    spectral_distance = float(np.linalg.norm(difference, ord=2))
    normalized_frobenius = float(np.linalg.norm(difference, ord="fro") / np.sqrt(left.shape[1]))
    left_gap = float(left_values[factor_dimension - 1] - left_values[factor_dimension])
    right_gap = float(right_values[factor_dimension - 1] - right_values[factor_dimension])
    left_relative = left_gap / max(float(left_values[factor_dimension - 1]), 1e-12)
    right_relative = right_gap / max(float(right_values[factor_dimension - 1]), 1e-12)
    ratio = spectral_distance / max(min(left_gap, right_gap), 1e-12)
    squared = difference**2
    contributions = np.zeros_like(squared)
    for row in range(squared.shape[0]):
        contributions[row, row] = squared[row, row]
        for column in range(row + 1, squared.shape[1]):
            contributions[row, column] = 2.0 * squared[row, column]
    total = float(np.sum(contributions))
    if total > 0.0:
        contributions /= total
    return GramGeometry(
        expanding_gram=left_gram,
        rolling_gram=right_gram,
        expanding_eigenvalues=left_values,
        rolling_eigenvalues=right_values,
        principal_cosines=principal_cosines,
        normalized_projector_distance=projector_distance,
        gram_spectral_distance=spectral_distance,
        gram_normalized_frobenius_distance=normalized_frobenius,
        expanding_absolute_eigengap=left_gap,
        rolling_absolute_eigengap=right_gap,
        expanding_relative_eigengap=left_relative,
        rolling_relative_eigengap=right_relative,
        perturbation_to_minimum_eigengap_ratio=ratio,
        upper_triangle_drift_contribution=contributions,
    )


def standardization_drift(
    expanding: FloatArray,
    rolling: FloatArray,
) -> StandardizationDrift:
    """Measure window-specific location, scale, and missingness drift by feature."""
    left = _history(expanding, "expanding history")
    right = _history(rolling, "rolling history")
    if left.shape[1] != right.shape[1]:
        raise InstabilityError("Compared histories must have the same features.")
    left_means, left_scales, _ = _moments(left)
    right_means, right_scales, _ = _moments(right)
    pooled_scales = np.sqrt((left_scales**2 + right_scales**2) / 2.0)
    return StandardizationDrift(
        location_shift=(right_means - left_means) / pooled_scales,
        log_scale_ratio=np.log(right_scales / left_scales),
        expanding_missing_rate=np.mean(~np.isfinite(left), axis=0),
        rolling_missing_rate=np.mean(~np.isfinite(right), axis=0),
    )


def sign_materiality(
    expanding: FloatArray,
    rolling: FloatArray,
    minimum_absolute_magnitude: float,
) -> SignMateriality:
    """Separate near-zero sign changes from prespecified substantive disagreements."""
    left = np.asarray(expanding, dtype=np.float64)
    right = np.asarray(rolling, dtype=np.float64)
    if (
        left.ndim != 1
        or right.shape != left.shape
        or left.size == 0
        or np.any(~np.isfinite(left))
        or np.any(~np.isfinite(right))
        or not np.isfinite(minimum_absolute_magnitude)
        or minimum_absolute_magnitude < 0.0
    ):
        raise InstabilityError("Sign-materiality inputs are invalid.")
    disagreement = np.sign(left) != np.sign(right)
    substantive = disagreement & (
        np.minimum(np.abs(left), np.abs(right)) >= minimum_absolute_magnitude
    )
    disagreements = int(np.sum(disagreement))
    substantive_count = int(np.sum(substantive))
    return SignMateriality(
        observations=left.size,
        disagreements=disagreements,
        disagreement_rate=disagreements / left.size,
        substantive_disagreements=substantive_count,
        substantive_disagreement_rate=substantive_count / left.size,
        substantive_share_of_disagreements=(
            substantive_count / disagreements if disagreements else 0.0
        ),
    )


def monetary_regimes(rates: FloatArray, zero_tolerance: float = 1e-12) -> tuple[str, ...]:
    """Classify policy-rate signs without using future observations or external labels."""
    values = np.asarray(rates, dtype=np.float64)
    if (
        values.ndim != 1
        or np.any(~np.isfinite(values))
        or not np.isfinite(zero_tolerance)
        or zero_tolerance < 0.0
    ):
        raise InstabilityError("Monetary-regime inputs are invalid.")
    return tuple(
        "negative" if value < -zero_tolerance else "positive" if value > zero_tolerance else "zero"
        for value in values
    )


def _month_number(month_id: str) -> int:
    try:
        prefix, year_text, month_text = month_id.split("-")
        year = int(year_text)
        month = int(month_text)
        if prefix != "month" or not 1 <= month <= 12:
            raise ValueError
        date(year, month, 1)
    except (TypeError, ValueError) as error:
        raise InstabilityError(f"Invalid monthly identifier: {month_id}") from error
    return year * 12 + month - 1


def detect_breach_episodes(
    month_ids: tuple[str, ...],
    breaches: NDArray[np.bool_],
    minimum_consecutive_breaches: int = 3,
    recovery_consecutive_stable: int = 3,
) -> tuple[BreachEpisode, ...]:
    """Date persistent breach episodes using a frozen onset and recovery rule."""
    flags = np.asarray(breaches)
    if (
        flags.ndim != 1
        or flags.size == 0
        or flags.size != len(month_ids)
        or flags.dtype.kind != "b"
        or isinstance(minimum_consecutive_breaches, bool)
        or isinstance(recovery_consecutive_stable, bool)
        or minimum_consecutive_breaches < 1
        or recovery_consecutive_stable < 1
    ):
        raise InstabilityError("Episode inputs or persistence rules are invalid.")
    numbers = [_month_number(month_id) for month_id in month_ids]
    if len(set(numbers)) != len(numbers) or any(
        current != previous + 1 for previous, current in zip(numbers, numbers[1:])
    ):
        raise InstabilityError("Episode months must form a unique consecutive calendar.")
    episodes: list[BreachEpisode] = []
    index = 0
    while index <= flags.size - minimum_consecutive_breaches:
        if not np.all(flags[index : index + minimum_consecutive_breaches]):
            index += 1
            continue
        start = index
        search = index + minimum_consecutive_breaches
        while search <= flags.size - recovery_consecutive_stable:
            if np.all(~flags[search : search + recovery_consecutive_stable]):
                end = search - 1
                episodes.append(
                    BreachEpisode(
                        start_month=month_ids[start],
                        end_month=month_ids[end],
                        duration_months=end - start + 1,
                        breach_months=int(np.sum(flags[start : end + 1])),
                        open_at_sample_end=False,
                    )
                )
                index = search + recovery_consecutive_stable
                break
            search += 1
        else:
            end = flags.size - 1
            episodes.append(
                BreachEpisode(
                    start_month=month_ids[start],
                    end_month=month_ids[end],
                    duration_months=end - start + 1,
                    breach_months=int(np.sum(flags[start : end + 1])),
                    open_at_sample_end=True,
                )
            )
            return tuple(episodes)
    return tuple(episodes)
