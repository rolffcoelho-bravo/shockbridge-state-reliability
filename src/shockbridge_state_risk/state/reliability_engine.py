"""Deterministic numerical kernel for the frozen information-set reliability design.

The module is deliberately value agnostic: it accepts in-memory arrays, performs no
retrieval or file I/O, and has no access to transmission outcomes.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from shockbridge_state_risk.state.hmm import FloatArray

BoolArray = NDArray[np.bool_]
IntArray = NDArray[np.int64]


class ReliabilityEngineError(ValueError):
    """Raised when an input or numerical result violates the frozen contract."""


@dataclass(frozen=True)
class StandardizedMatrix:
    values: FloatArray
    observed: BoolArray
    means: FloatArray
    scales: FloatArray
    counts: IntArray


@dataclass(frozen=True)
class ChannelMap:
    matrix: FloatArray
    weights: FloatArray
    channel_order: tuple[str, ...]
    series_channels: tuple[str, ...]


@dataclass(frozen=True)
class EMPCAFit:
    rank: int
    scores: FloatArray
    loadings: FloatArray
    completed_matrix: FloatArray
    singular_values: FloatArray
    observed_variance: float
    iterations: int
    converged: bool


@dataclass(frozen=True)
class EMPCARankSelection:
    selected: EMPCAFit
    fits: tuple[EMPCAFit, ...]
    criteria: tuple[float, ...]


@dataclass(frozen=True)
class ProjectorComparison:
    spectral_distance: float
    normalized_frobenius_distance: float
    left_rank: int
    right_rank: int


@dataclass(frozen=True)
class ScenarioInput:
    scenario_id: str
    eligibility_mask: BoolArray
    standardized_observed_matrix: FloatArray


@dataclass(frozen=True)
class DeduplicatedScenario:
    representative_id: str
    member_ids: tuple[str, ...]
    canonical_key: str


def _matrix(value: object, label: str, *, allow_nan: bool) -> FloatArray:
    matrix = np.asarray(value, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] < 2 or matrix.shape[1] < 1:
        raise ReliabilityEngineError(f"{label} must be a nonempty two-dimensional history")
    if np.any(np.isinf(matrix)) or (not allow_nan and np.any(~np.isfinite(matrix))):
        raise ReliabilityEngineError(f"{label} contains a prohibited nonfinite value")
    return matrix


def standardize_observed_matrix(
    values: object,
    *,
    minimum_coverage: float = 0.80,
    minimum_observations: int = 24,
) -> StandardizedMatrix:
    """Standardize retained series using observed expanding-history moments only."""
    matrix = _matrix(values, "Training matrix", allow_nan=True)
    if (
        not np.isfinite(minimum_coverage)
        or minimum_coverage <= 0.0
        or minimum_coverage > 1.0
        or type(minimum_observations) is not int
        or minimum_observations < 2
    ):
        raise ReliabilityEngineError("Coverage and observation thresholds are invalid")
    observed = np.isfinite(matrix)
    counts = observed.sum(axis=0)
    coverage = counts / matrix.shape[0]
    if np.any(counts < minimum_observations) or np.any(coverage < minimum_coverage):
        raise ReliabilityEngineError("Every retained series must pass count and coverage gates")
    means = np.sum(np.where(observed, matrix, 0.0), axis=0) / counts
    centered = np.where(observed, matrix - means, 0.0)
    variances = np.sum(centered**2, axis=0) / (counts - 1)
    scales = np.sqrt(variances)
    if np.any(~np.isfinite(scales)) or np.any(scales <= np.finfo(np.float64).eps):
        raise ReliabilityEngineError("Every retained series requires finite positive scale")
    standardized = np.where(observed, (matrix - means) / scales, np.nan)
    return StandardizedMatrix(
        values=np.asarray(standardized, dtype=np.float64),
        observed=observed,
        means=np.asarray(means, dtype=np.float64),
        scales=np.asarray(scales, dtype=np.float64),
        counts=np.asarray(counts, dtype=np.int64),
    )


def build_channel_map(
    series_channels: Sequence[str],
    signs: object,
    *,
    channel_order: Sequence[str] | None = None,
) -> ChannelMap:
    """Build the signed inverse-square-root channel map used exactly once."""
    channels = tuple(series_channels)
    direction = np.asarray(signs)
    if not channels or any(not isinstance(value, str) or not value.strip() for value in channels):
        raise ReliabilityEngineError("Series channels must be nonempty strings")
    if direction.shape != (len(channels),) or not np.issubdtype(direction.dtype, np.integer):
        raise ReliabilityEngineError("Signs must be an integer vector matching the series")
    direction_float = direction.astype(np.float64)
    if np.any((direction_float != -1.0) & (direction_float != 1.0)):
        raise ReliabilityEngineError("Signs must be exactly -1 or 1")
    order = tuple(channel_order) if channel_order is not None else tuple(sorted(set(channels)))
    if (
        not order
        or len(set(order)) != len(order)
        or any(not isinstance(value, str) or not value.strip() for value in order)
        or not set(channels).issubset(order)
    ):
        raise ReliabilityEngineError(
            "Channel order must be unique and contain every series channel"
        )
    counts = {channel: channels.count(channel) for channel in set(channels)}
    weights = np.asarray(
        [
            direction_float[index] / np.sqrt(counts[channel])
            for index, channel in enumerate(channels)
        ],
        dtype=np.float64,
    )
    mapping = np.zeros((len(order), len(channels)), dtype=np.float64)
    locations = {channel: index for index, channel in enumerate(order)}
    for column, channel in enumerate(channels):
        mapping[locations[channel], column] = weights[column]
    return ChannelMap(
        matrix=mapping,
        weights=weights,
        channel_order=order,
        series_channels=channels,
    )


def _canonicalize_svd_signs(left: FloatArray, right: FloatArray) -> None:
    for component in range(right.shape[0]):
        pivot = int(np.argmax(np.abs(right[component])))
        if right[component, pivot] < 0.0:
            left[:, component] *= -1.0
            right[component] *= -1.0


def _validate_fit_inputs(
    standardized: object, channel_weights: object, rank: int
) -> tuple[FloatArray, FloatArray, BoolArray, int]:
    matrix = _matrix(standardized, "Standardized matrix", allow_nan=True)
    weights = np.asarray(channel_weights, dtype=np.float64)
    if (
        weights.shape != (matrix.shape[1],)
        or np.any(~np.isfinite(weights))
        or np.any(weights == 0.0)
    ):
        raise ReliabilityEngineError(
            "Channel weights must be finite, nonzero, and match the series"
        )
    if type(rank) is not int or rank < 1 or rank >= matrix.shape[1]:
        raise ReliabilityEngineError("EM-PCA rank must be positive and below the series count")
    observed = np.isfinite(matrix)
    if np.any(observed.sum(axis=0) < 2):
        raise ReliabilityEngineError("Every retained standardized series requires observations")
    initialized = np.where(observed, matrix * weights, 0.0)
    observed_rank = int(np.linalg.matrix_rank(initialized))
    if rank > observed_rank:
        raise ReliabilityEngineError("EM-PCA rank exceeds the observed initialized rank")
    return matrix, weights, observed, observed_rank


def fit_em_pca_rank(
    standardized: object,
    channel_weights: object,
    rank: int,
    *,
    tolerance: float = 1e-8,
    maximum_iterations: int = 1000,
) -> EMPCAFit:
    """Fit one deterministic channel-weighted EM-PCA rank on observed entries."""
    matrix, weights, observed, _ = _validate_fit_inputs(standardized, channel_weights, rank)
    if (
        not np.isfinite(tolerance)
        or tolerance <= 0.0
        or type(maximum_iterations) is not int
        or maximum_iterations < 2
    ):
        raise ReliabilityEngineError("EM-PCA convergence controls are invalid")
    observed_weighted = np.where(observed, matrix * weights, 0.0)
    completed_weighted = observed_weighted.copy()
    observed_weight_sum = float(np.sum(np.broadcast_to(weights**2, matrix.shape)[observed]))
    if observed_weight_sum <= 0.0:
        raise ReliabilityEngineError("Observed channel weight is zero")
    previous_loss: float | None = None
    converged = False
    singular_values = np.empty(0, dtype=np.float64)
    left = np.empty((matrix.shape[0], 0), dtype=np.float64)
    right = np.empty((0, matrix.shape[1]), dtype=np.float64)
    loss = float("nan")
    for _iteration in range(1, maximum_iterations + 1):
        left_full, singular_full, right_full = np.linalg.svd(
            completed_weighted, full_matrices=False
        )
        left = np.asarray(left_full[:, :rank], dtype=np.float64)
        singular_values = np.asarray(singular_full[:rank], dtype=np.float64)
        right = np.asarray(right_full[:rank], dtype=np.float64)
        _canonicalize_svd_signs(left, right)
        reconstruction = (left * singular_values) @ right
        residual = observed_weighted[observed] - reconstruction[observed]
        loss = float(np.sum(residual**2) / observed_weight_sum)
        if not np.isfinite(loss):
            raise ReliabilityEngineError("EM-PCA produced nonfinite observed loss")
        if previous_loss is not None:
            denominator = max(abs(previous_loss), float(np.finfo(np.float64).eps))
            if abs(loss - previous_loss) / denominator <= tolerance:
                converged = True
                completed_weighted = np.where(observed, observed_weighted, reconstruction)
                break
        completed_weighted = np.where(observed, observed_weighted, reconstruction)
        previous_loss = loss
    if not converged:
        raise ReliabilityEngineError("EM-PCA did not converge within the frozen iteration limit")
    scores = left * singular_values
    loadings = right.T / weights[:, None]
    completed = np.where(observed, matrix, completed_weighted / weights)
    if not np.array_equal(completed[observed], matrix[observed]):
        raise ReliabilityEngineError("EM-PCA changed an observed standardized entry")
    return EMPCAFit(
        rank=rank,
        scores=np.asarray(scores, dtype=np.float64),
        loadings=np.asarray(loadings, dtype=np.float64),
        completed_matrix=np.asarray(completed, dtype=np.float64),
        singular_values=singular_values,
        observed_variance=loss,
        iterations=_iteration,
        converged=True,
    )


def select_em_pca_rank(
    standardized: object,
    channel_weights: object,
    *,
    candidate_ranks: Iterable[int] = (1, 2, 3),
    tolerance: float = 1e-8,
    maximum_iterations: int = 1000,
) -> EMPCARankSelection:
    """Select the lower-tie deterministic rank using the frozen ICp2 adaptation."""
    matrix = _matrix(standardized, "Standardized matrix", allow_nan=True)
    weights = np.asarray(channel_weights, dtype=np.float64)
    if weights.shape != (matrix.shape[1],):
        raise ReliabilityEngineError("Channel weights do not match the standardized matrix")
    initialized = np.where(np.isfinite(matrix), matrix * weights, 0.0)
    maximum_rank = min(matrix.shape[1] - 1, int(np.linalg.matrix_rank(initialized)))
    ranks = tuple(sorted(set(candidate_ranks)))
    if not ranks or any(type(rank) is not int or rank < 1 for rank in ranks):
        raise ReliabilityEngineError("Candidate ranks must be unique positive integers")
    eligible = tuple(rank for rank in ranks if rank <= maximum_rank)
    if not eligible:
        raise ReliabilityEngineError("No candidate rank is identified by the observed matrix")
    fits = tuple(
        fit_em_pca_rank(
            matrix,
            weights,
            rank,
            tolerance=tolerance,
            maximum_iterations=maximum_iterations,
        )
        for rank in eligible
    )
    rows, columns = matrix.shape
    effective_sample_size = (columns * rows) / (columns + rows)
    if effective_sample_size <= 1.0:
        raise ReliabilityEngineError("ICp2 requires NT/(N+T) greater than one")
    penalty_scale = ((columns + rows) / (columns * rows)) * np.log(effective_sample_size)
    criteria = tuple(
        float(
            np.log(max(fit.observed_variance, float(np.finfo(np.float64).eps)))
            + fit.rank * penalty_scale
        )
        for fit in fits
    )
    selected_index = min(range(len(fits)), key=lambda index: (criteria[index], fits[index].rank))
    return EMPCARankSelection(
        selected=fits[selected_index],
        fits=fits,
        criteria=criteria,
    )


def _projector_from_columns(matrix: FloatArray, label: str) -> FloatArray:
    if matrix.ndim != 2 or matrix.shape[1] < 1 or np.any(~np.isfinite(matrix)):
        raise ReliabilityEngineError(f"{label} must be a finite matrix with at least one column")
    left, singular_values, _ = np.linalg.svd(matrix, full_matrices=False)
    tolerance = max(matrix.shape) * np.finfo(np.float64).eps * singular_values[0]
    numerical_rank = int(np.sum(singular_values > tolerance))
    if numerical_rank < 1:
        raise ReliabilityEngineError(f"{label} has zero numerical rank")
    basis = left[:, :numerical_rank]
    projector = basis @ basis.T
    return np.asarray(0.5 * (projector + projector.T), dtype=np.float64)


def score_projector(scores: object) -> FloatArray:
    """Return the rotation-invariant projector of centered common-calendar scores."""
    matrix = _matrix(scores, "Score matrix", allow_nan=False)
    centered = matrix - matrix.mean(axis=0)
    return _projector_from_columns(centered, "Centered score matrix")


def channel_projector(loadings: object, channel_map: object) -> FloatArray:
    """Map original-coordinate loadings once and return their channel projector."""
    loading_matrix = _matrix(loadings, "Loading matrix", allow_nan=False)
    mapping = np.asarray(channel_map, dtype=np.float64)
    if (
        mapping.ndim != 2
        or mapping.shape[1] != loading_matrix.shape[0]
        or np.any(~np.isfinite(mapping))
    ):
        raise ReliabilityEngineError("Channel map must be finite and match loading rows")
    return _projector_from_columns(mapping @ loading_matrix, "Channel loading matrix")


def _validate_projector(value: object, label: str) -> tuple[FloatArray, int]:
    matrix = np.asarray(value, dtype=np.float64)
    if (
        matrix.ndim != 2
        or matrix.shape[0] != matrix.shape[1]
        or np.any(~np.isfinite(matrix))
        or not np.allclose(matrix, matrix.T, rtol=0.0, atol=1e-9)
        or not np.allclose(matrix @ matrix, matrix, rtol=0.0, atol=1e-8)
    ):
        raise ReliabilityEngineError(f"{label} must be a finite symmetric idempotent matrix")
    rank = int(np.linalg.matrix_rank(matrix, tol=1e-8))
    if rank < 1:
        raise ReliabilityEngineError(f"{label} must have positive rank")
    return matrix, rank


def compare_projectors(left: object, right: object) -> ProjectorComparison:
    """Compute frozen spectral and unequal-rank-normalized Frobenius distances."""
    left_matrix, left_rank = _validate_projector(left, "Left projector")
    right_matrix, right_rank = _validate_projector(right, "Right projector")
    if left_matrix.shape != right_matrix.shape:
        raise ReliabilityEngineError("Compared projectors must use the same coordinate space")
    difference = left_matrix - right_matrix
    return ProjectorComparison(
        spectral_distance=float(np.linalg.norm(difference, ord=2)),
        normalized_frobenius_distance=float(
            np.linalg.norm(difference, ord="fro") / np.sqrt(left_rank + right_rank)
        ),
        left_rank=left_rank,
        right_rank=right_rank,
    )


def align_scores_procrustes(reference: object, target: object) -> FloatArray:
    """Align equal-rank scores using only their common rows."""
    reference_matrix = _matrix(reference, "Reference scores", allow_nan=False)
    target_matrix = _matrix(target, "Target scores", allow_nan=False)
    if reference_matrix.shape != target_matrix.shape:
        raise ReliabilityEngineError("Procrustes alignment requires equal rows and ranks")
    reference_centered = reference_matrix - reference_matrix.mean(axis=0)
    target_centered = target_matrix - target_matrix.mean(axis=0)
    if (
        np.linalg.matrix_rank(reference_centered) < reference_centered.shape[1]
        or np.linalg.matrix_rank(target_centered) < target_centered.shape[1]
    ):
        raise ReliabilityEngineError("Procrustes score matrices must have full column rank")
    left, _, right = np.linalg.svd(target_centered.T @ reference_centered)
    return np.asarray(target_centered @ (left @ right), dtype=np.float64)


def canonical_scenario_key(eligibility_mask: object, standardized_observed_matrix: object) -> str:
    """Hash a scenario's exact mask and canonical 12-significant-digit observations."""
    mask = np.asarray(eligibility_mask)
    matrix = np.asarray(standardized_observed_matrix, dtype=np.float64)
    if mask.dtype != np.bool_ or mask.ndim != 2 or mask.shape != matrix.shape:
        raise ReliabilityEngineError("Scenario mask must be boolean and match the matrix")
    if np.any(~np.isfinite(matrix[mask])) or np.any(~np.isnan(matrix[~mask])):
        raise ReliabilityEngineError(
            "Scenario observations must be finite and excluded cells missing"
        )

    def formatted(value: float) -> str:
        return "0" if value == 0.0 else format(value, ".12g")

    payload = {
        "shape": list(matrix.shape),
        "mask": "".join("1" if value else "0" for value in mask.ravel(order="C")),
        "observed": [formatted(float(value)) for value in matrix[mask]],
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def deduplicate_scenarios(scenarios: Iterable[ScenarioInput]) -> tuple[DeduplicatedScenario, ...]:
    """Collapse exact scenario duplicates with lexical, order-independent representatives."""
    values = tuple(scenarios)
    if not values:
        raise ReliabilityEngineError("At least one scenario is required")
    ids = [scenario.scenario_id for scenario in values]
    if any(not isinstance(value, str) or not value.strip() for value in ids) or len(
        set(ids)
    ) != len(ids):
        raise ReliabilityEngineError("Scenario identifiers must be unique nonempty strings")
    groups: dict[str, list[str]] = {}
    for scenario in values:
        key = canonical_scenario_key(
            scenario.eligibility_mask, scenario.standardized_observed_matrix
        )
        groups.setdefault(key, []).append(scenario.scenario_id)
    representatives = [
        DeduplicatedScenario(
            representative_id=min(member_ids),
            member_ids=tuple(sorted(member_ids)),
            canonical_key=key,
        )
        for key, member_ids in groups.items()
    ]
    return tuple(sorted(representatives, key=lambda item: item.representative_id))
