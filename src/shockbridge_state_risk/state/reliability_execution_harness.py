"""Value-agnostic primitives for the approved Run 027 execution amendment.

The module implements the eleven operational resolutions without loading an
official panel, fitting calibration values, reading evaluation results, or
importing any monetary-policy outcome module. Arrays used by its tests are
software fixtures only.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from numpy.typing import NDArray

from shockbridge_state_risk.state.hmm import FloatArray
from shockbridge_state_risk.state.reliability_engine import (
    EMPCAFit,
    ReliabilityEngineError,
    canonical_scenario_key,
    compare_projectors,
    select_em_pca_rank,
)

BoolArray = NDArray[np.bool_]
IntArray = NDArray[np.int64]


class ReliabilityExecutionHarnessError(ValueError):
    """Raised when an amended execution rule cannot be applied uniquely."""


@dataclass(frozen=True)
class PanelCell:
    origin_month: str
    series_id: str
    transformed_value: float | None
    observation_period: str
    missing_reason: str = ""


@dataclass(frozen=True)
class OriginMatrix:
    origins: tuple[str, ...]
    series_ids: tuple[str, ...]
    values: FloatArray
    observed: BoolArray
    observation_periods: tuple[tuple[str, ...], ...]
    missing_reasons: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class RecoveredFactorFit:
    rank: int
    loadings: FloatArray
    final_window_scores: FloatArray
    complete_row_indices: IntArray
    fit: EMPCAFit


@dataclass(frozen=True)
class SeriesRedundancyMetadata:
    series_id: str
    channel: str
    timing_strength: int
    revision_exposure: int
    first_usable_origin: int
    training_missingness: float
    manifest_order: int


@dataclass(frozen=True)
class RedundancyResolution:
    retained_indices: tuple[int, ...]
    components: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class AnchorState:
    capture: float
    scalar_scores: FloatArray
    standardized_scores: FloatArray
    coefficient: FloatArray


@dataclass(frozen=True)
class HistoryFitSummary:
    converged: bool
    channel_count: int
    final_scores_identified: bool
    anchor_capture: float
    score_projector: FloatArray
    channel_projector: FloatArray


@dataclass(frozen=True)
class WithinScenarioGate:
    passed: bool
    score_distance: float
    channel_distance: float
    minimum_anchor_capture: float
    failures: tuple[str, ...]


@dataclass(frozen=True)
class RobustPCAFit:
    low_rank: FloatArray
    sparse: FloatArray
    iterations: int
    converged: bool
    relative_primal_error: float


@dataclass(frozen=True)
class ThresholdCandidate:
    candidate_id: str
    loss: float
    participation: float
    score_cutoff: float
    channel_cutoff: float
    orientation_floor: float


@dataclass(frozen=True)
class ControlAssessment:
    passed: bool
    primary_loss: float
    nc1_loss: float
    nc2_loss: float
    nc3_jointly_reproduced: bool
    reason: str


@dataclass(frozen=True)
class BootstrapPlan:
    sample_size: int
    block_length: int
    draws: int
    seed: int
    indices: IntArray


@dataclass(frozen=True)
class BootstrapIntervals:
    point_estimate: FloatArray
    standard_error: FloatArray
    simultaneous_lower: FloatArray
    simultaneous_upper: FloatArray
    critical_value: float


def _finite_matrix(value: object, label: str, *, allow_nan: bool = False) -> FloatArray:
    matrix = np.asarray(value, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] < 2 or matrix.shape[1] < 1:
        raise ReliabilityExecutionHarnessError(f"{label} must be a nonempty matrix")
    if np.any(np.isinf(matrix)) or (not allow_nan and np.any(~np.isfinite(matrix))):
        raise ReliabilityExecutionHarnessError(f"{label} contains prohibited nonfinite values")
    return matrix


def validate_approved_amendment(approval_path: Path, proposal_path: Path) -> str:
    """Verify that the approval binds the unchanged Run 027 proposal bytes."""
    approval = yaml.safe_load(approval_path.read_text(encoding="utf-8"))
    if not isinstance(approval, dict):
        raise ReliabilityExecutionHarnessError("Approval record must be a mapping")
    if approval.get("status") != "APPROVED_FOR_IMPLEMENTATION_AND_HOSTILE_SOFTWARE_TESTS_ONLY":
        raise ReliabilityExecutionHarnessError("Amendment is not approved for implementation")
    bound = approval.get("approved_amendment")
    if not isinstance(bound, dict):
        raise ReliabilityExecutionHarnessError("Approval lacks the bound amendment")
    raw = proposal_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if (
        bound.get("bytes") != len(raw)
        or bound.get("sha256") != digest
        or bound.get("incorporated_by_reference_without_modification") is not True
    ):
        raise ReliabilityExecutionHarnessError("Approved amendment byte identity changed")
    scope = approval.get("approval_scope")
    if (
        not isinstance(scope, dict)
        or scope.get("implement_all_eleven_executable_resolutions") is not True
        or scope.get("hostile_software_tests_with_synthetic_fixtures") is not True
        or any(
            scope.get(field) is not False
            for field in (
                "official_calibration_fit_allowed_in_this_run",
                "official_evaluation_access_allowed_in_this_run",
                "transmission_outcome_access_allowed",
                "synthetic_empirical_observations_allowed",
            )
        )
    ):
        raise ReliabilityExecutionHarnessError("Approval firewall is not sealed")
    return digest


def build_origin_matrix(
    cells: Sequence[PanelCell], origins: Sequence[str], series_ids: Sequence[str]
) -> OriginMatrix:
    """Build the unique monthly-origin by manifest-series matrix (XG-01)."""
    origin_order = tuple(origins)
    series_order = tuple(series_ids)
    if (
        not origin_order
        or not series_order
        or len(set(origin_order)) != len(origin_order)
        or len(set(series_order)) != len(series_order)
    ):
        raise ReliabilityExecutionHarnessError("Origin and series coordinates must be unique")
    row = {value: index for index, value in enumerate(origin_order)}
    column = {value: index for index, value in enumerate(series_order)}
    values = np.full((len(origin_order), len(series_order)), np.nan, dtype=np.float64)
    periods = [["" for _ in series_order] for _ in origin_order]
    reasons = [["unregistered_cell" for _ in series_order] for _ in origin_order]
    seen: set[tuple[str, str]] = set()
    for cell in cells:
        key = (cell.origin_month, cell.series_id)
        if key in seen:
            raise ReliabilityExecutionHarnessError("Duplicate origin-series cell")
        seen.add(key)
        if cell.origin_month not in row or cell.series_id not in column:
            raise ReliabilityExecutionHarnessError("Cell is outside the frozen coordinates")
        i, j = row[cell.origin_month], column[cell.series_id]
        periods[i][j] = cell.observation_period
        if cell.transformed_value is None:
            reasons[i][j] = cell.missing_reason or "missing"
        elif not np.isfinite(cell.transformed_value):
            raise ReliabilityExecutionHarnessError("Observed cell must be finite")
        else:
            values[i, j] = float(cell.transformed_value)
            reasons[i][j] = ""
    if len(seen) != len(origin_order) * len(series_order):
        raise ReliabilityExecutionHarnessError("Frozen origin-series grid is incomplete")
    observed = np.isfinite(values)
    return OriginMatrix(
        origins=origin_order,
        series_ids=series_order,
        values=values,
        observed=observed,
        observation_periods=tuple(tuple(item) for item in periods),
        missing_reasons=tuple(tuple(item) for item in reasons),
    )


def apply_slow_release_stress(matrix: OriginMatrix, affected_series: Sequence[str]) -> OriginMatrix:
    """Shift complete class-B paths one monthly origin forward (XG-02)."""
    affected = set(affected_series)
    if not affected or not affected.issubset(matrix.series_ids):
        raise ReliabilityExecutionHarnessError(
            "Affected series must be a nonempty registered subset"
        )
    values = matrix.values.copy()
    periods = [list(row) for row in matrix.observation_periods]
    reasons = [list(row) for row in matrix.missing_reasons]
    for j, series_id in enumerate(matrix.series_ids):
        if series_id not in affected:
            continue
        values[1:, j] = matrix.values[:-1, j]
        values[0, j] = np.nan
        for i in range(len(matrix.origins) - 1, 0, -1):
            periods[i][j] = matrix.observation_periods[i - 1][j]
            reasons[i][j] = matrix.missing_reasons[i - 1][j]
        periods[0][j] = ""
        reasons[0][j] = "slow_release_boundary"
    return OriginMatrix(
        origins=matrix.origins,
        series_ids=matrix.series_ids,
        values=values,
        observed=np.isfinite(values),
        observation_periods=tuple(tuple(row) for row in periods),
        missing_reasons=tuple(tuple(row) for row in reasons),
    )


def recover_complete_case_scores(
    standardized: object,
    channel_weights: object,
    *,
    candidate_ranks: Sequence[int] = (1, 2, 3),
    minimum_complete_rows: int = 60,
    final_window_rows: int = 120,
) -> RecoveredFactorFit:
    """Fit complete rows and recover every final-window score by weighted LS (XG-03)."""
    matrix = _finite_matrix(standardized, "Standardized matrix", allow_nan=True)
    weights = np.asarray(channel_weights, dtype=np.float64)
    if weights.shape != (matrix.shape[1],) or np.any(~np.isfinite(weights)):
        raise ReliabilityExecutionHarnessError("Channel weights do not match the matrix")
    if final_window_rows < 2 or matrix.shape[0] < final_window_rows:
        raise ReliabilityExecutionHarnessError("The declared final calendar window is unavailable")
    complete = np.all(np.isfinite(matrix), axis=1)
    indices = np.flatnonzero(complete).astype(np.int64)
    if indices.size < minimum_complete_rows:
        raise ReliabilityExecutionHarnessError("Fewer than 60 complete training rows")
    try:
        selection = select_em_pca_rank(matrix[complete], weights, candidate_ranks=candidate_ranks)
    except ReliabilityEngineError as error:
        raise ReliabilityExecutionHarnessError(str(error)) from error
    fit = selection.selected
    recovered = np.empty((final_window_rows, fit.rank), dtype=np.float64)
    window = matrix[-final_window_rows:]
    for i, values in enumerate(window):
        observed = np.isfinite(values)
        design = fit.loadings[observed] * weights[observed, None]
        target = values[observed] * weights[observed]
        if observed.sum() < fit.rank or np.linalg.matrix_rank(design) < fit.rank:
            raise ReliabilityExecutionHarnessError("Final-window score row is unidentified")
        recovered[i] = np.linalg.lstsq(design, target, rcond=None)[0]
    return RecoveredFactorFit(
        rank=fit.rank,
        loadings=fit.loadings,
        final_window_scores=recovered,
        complete_row_indices=indices,
        fit=fit,
    )


def resolve_near_duplicates(
    standardized: object,
    metadata: Sequence[SeriesRedundancyMetadata],
    *,
    correlation_threshold: float = 0.98,
    minimum_pairwise_months: int = 60,
) -> RedundancyResolution:
    """Resolve within-channel correlation components deterministically (XG-04)."""
    matrix = _finite_matrix(standardized, "Training matrix", allow_nan=True)
    records = tuple(metadata)
    if len(records) != matrix.shape[1] or len({item.series_id for item in records}) != len(records):
        raise ReliabilityExecutionHarnessError("Series metadata must uniquely match columns")
    if not 0.0 < correlation_threshold <= 1.0 or minimum_pairwise_months < 2:
        raise ReliabilityExecutionHarnessError("Near-duplicate controls are invalid")
    adjacency = [set([index]) for index in range(len(records))]
    for left in range(len(records)):
        for right in range(left + 1, len(records)):
            if records[left].channel != records[right].channel:
                continue
            observed = np.isfinite(matrix[:, left]) & np.isfinite(matrix[:, right])
            if int(observed.sum()) < minimum_pairwise_months:
                continue
            correlation = float(np.corrcoef(matrix[observed, left], matrix[observed, right])[0, 1])
            if np.isfinite(correlation) and abs(correlation) > correlation_threshold:
                adjacency[left].add(right)
                adjacency[right].add(left)
    components: list[tuple[int, ...]] = []
    unseen = set(range(len(records)))
    while unseen:
        stack = [min(unseen)]
        component: set[int] = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(sorted(adjacency[current] - component, reverse=True))
        unseen -= component
        components.append(tuple(sorted(component)))

    def priority(index: int) -> tuple[float | int | str, ...]:
        item = records[index]
        if (
            not np.isfinite(item.training_missingness)
            or not 0.0 <= item.training_missingness <= 1.0
        ):
            raise ReliabilityExecutionHarnessError("Training missingness must be in [0, 1]")
        return (
            -item.timing_strength,
            item.revision_exposure,
            item.first_usable_origin,
            item.training_missingness,
            item.manifest_order,
            item.series_id,
        )

    retained = tuple(sorted(min(component, key=priority) for component in components))
    named = tuple(
        tuple(records[index].series_id for index in component) for component in components
    )
    return RedundancyResolution(retained_indices=retained, components=named)


def rank_invariant_anchor_state(
    scores: object,
    loadings: object,
    channel_map: object,
    *,
    anchor: object | None = None,
) -> AnchorState:
    """Construct the rank- and rotation-invariant channel-anchor scalar (XG-05)."""
    score_matrix = _finite_matrix(scores, "Score matrix")
    loading_matrix = _finite_matrix(loadings, "Loading matrix")
    mapping = np.asarray(channel_map, dtype=np.float64)
    if score_matrix.shape[1] != loading_matrix.shape[1]:
        raise ReliabilityExecutionHarnessError("Scores and loadings must have equal rank")
    if mapping.ndim != 2 or mapping.shape[1] != loading_matrix.shape[0]:
        raise ReliabilityExecutionHarnessError("Channel map does not match loading rows")
    channel_loadings = mapping @ loading_matrix
    channel_count = channel_loadings.shape[0]
    direction = (
        np.full(channel_count, 1.0 / np.sqrt(channel_count), dtype=np.float64)
        if anchor is None
        else np.asarray(anchor, dtype=np.float64)
    )
    if direction.shape != (channel_count,) or np.any(~np.isfinite(direction)):
        raise ReliabilityExecutionHarnessError("Anchor must match the channel coordinate")
    if not np.isclose(np.linalg.norm(direction), 1.0, rtol=0.0, atol=1e-12):
        raise ReliabilityExecutionHarnessError("Anchor must have unit Euclidean norm")
    coefficient = np.linalg.lstsq(channel_loadings, direction, rcond=None)[0]
    projected = channel_loadings @ coefficient
    capture = float(np.linalg.norm(projected))
    scalar = score_matrix @ coefficient
    scale = float(np.std(scalar, ddof=1))
    if not np.isfinite(scale) or scale <= np.finfo(np.float64).eps:
        raise ReliabilityExecutionHarnessError("Anchor scalar has zero training scale")
    standardized = (scalar - float(np.mean(scalar))) / scale
    return AnchorState(
        capture=capture,
        scalar_scores=np.asarray(scalar, dtype=np.float64),
        standardized_scores=np.asarray(standardized, dtype=np.float64),
        coefficient=np.asarray(coefficient, dtype=np.float64),
    )


def scenario_history_key(
    expanding_mask: object,
    expanding_matrix: object,
    rolling_mask: object,
    rolling_matrix: object,
) -> str:
    """Hash both history masks and matrices before lexical deduplication (XG-06)."""
    expanding = np.asarray(expanding_matrix, dtype=np.float64)
    rolling = np.asarray(rolling_matrix, dtype=np.float64)
    if (
        expanding.ndim != 2
        or rolling.ndim != 2
        or expanding.shape[0] < 120
        or rolling.shape[0] != 120
        or expanding.shape[1] != rolling.shape[1]
    ):
        raise ReliabilityExecutionHarnessError(
            "Scenario identity requires expanding and exact 120-row rolling histories"
        )
    keys = (
        canonical_scenario_key(expanding_mask, expanding),
        canonical_scenario_key(rolling_mask, rolling),
    )
    return hashlib.sha256("|".join(keys).encode("ascii")).hexdigest()


def evaluate_within_scenario_gate(
    expanding: HistoryFitSummary,
    rolling: HistoryFitSummary,
    *,
    score_threshold: float,
    channel_threshold: float,
    orientation_floor: float,
    minimum_channels: int = 5,
) -> WithinScenarioGate:
    """Evaluate every binary expanding-versus-rolling gate (XG-06)."""
    if (
        not np.isfinite(score_threshold)
        or not np.isfinite(channel_threshold)
        or not np.isfinite(orientation_floor)
        or score_threshold < 0.0
        or channel_threshold < 0.0
        or not 0.0 <= orientation_floor <= 1.0
        or minimum_channels < 1
        or not np.isfinite(expanding.anchor_capture)
        or not np.isfinite(rolling.anchor_capture)
    ):
        raise ReliabilityExecutionHarnessError("Within-scenario gate controls are invalid")
    score = compare_projectors(expanding.score_projector, rolling.score_projector)
    channel = compare_projectors(expanding.channel_projector, rolling.channel_projector)
    minimum_capture = min(expanding.anchor_capture, rolling.anchor_capture)
    failures: list[str] = []
    if not expanding.converged or not rolling.converged:
        failures.append("nonconvergence")
    if min(expanding.channel_count, rolling.channel_count) < minimum_channels:
        failures.append("insufficient_channels")
    if not expanding.final_scores_identified or not rolling.final_scores_identified:
        failures.append("unidentified_final_scores")
    if score.spectral_distance > score_threshold:
        failures.append("score_distance")
    if channel.spectral_distance > channel_threshold:
        failures.append("channel_distance")
    if minimum_capture < orientation_floor:
        failures.append("anchor_capture")
    return WithinScenarioGate(
        passed=not failures,
        score_distance=score.spectral_distance,
        channel_distance=channel.spectral_distance,
        minimum_anchor_capture=minimum_capture,
        failures=tuple(failures),
    )


def fit_observed_stable_pcp(
    values: object,
    *,
    lambda_multiplier: float = 1.0,
    tolerance: float = 1e-8,
    maximum_iterations: int = 2000,
) -> RobustPCAFit:
    """Fit deterministic observed-entry stable PCP for comparator B3 (XG-07)."""
    matrix = _finite_matrix(values, "Robust-PCA matrix", allow_nan=True)
    observed = np.isfinite(matrix)
    data = np.where(observed, matrix, 0.0)
    if (
        not np.any(observed)
        or lambda_multiplier not in (0.5, 1.0, 2.0)
        or not np.isfinite(tolerance)
        or tolerance <= 0.0
        or type(maximum_iterations) is not int
        or maximum_iterations < 1
    ):
        raise ReliabilityExecutionHarnessError("Robust-PCA penalty is outside the frozen grid")
    lam = lambda_multiplier / np.sqrt(max(matrix.shape))
    epsilon = float(np.finfo(np.float64).eps)
    spectral = float(np.linalg.norm(data, ord=2))
    scaled_max = float(np.max(np.abs(data))) / lam
    dual_norm = max(spectral, scaled_max, epsilon)
    dual = data / dual_norm
    low_rank = np.zeros_like(data)
    sparse = np.zeros_like(data)
    mu = 1.25 / max(spectral, epsilon)
    rho = 1.5
    observed_norm = max(float(np.linalg.norm(data[observed])), epsilon)
    error = float("inf")
    for iteration in range(1, maximum_iterations + 1):
        left, singular, right = np.linalg.svd(data - sparse + dual / mu, full_matrices=False)
        shrunk = np.maximum(singular - 1.0 / mu, 0.0)
        low_rank = (left * shrunk) @ right
        residual_for_sparse = data - low_rank + dual / mu
        sparse = np.where(
            observed,
            np.sign(residual_for_sparse) * np.maximum(np.abs(residual_for_sparse) - lam / mu, 0.0),
            0.0,
        )
        primal = np.where(observed, data - low_rank - sparse, 0.0)
        error = float(np.linalg.norm(primal[observed]) / observed_norm)
        if error <= tolerance:
            return RobustPCAFit(
                low_rank=np.asarray(low_rank, dtype=np.float64),
                sparse=np.asarray(sparse, dtype=np.float64),
                iterations=iteration,
                converged=True,
                relative_primal_error=error,
            )
        dual += mu * primal
        mu *= rho
    raise ReliabilityExecutionHarnessError("Robust PCA did not converge")


def select_calibration_threshold(candidates: Sequence[ThresholdCandidate]) -> ThresholdCandidate:
    """Select a threshold using calibration loss and the frozen tie-break only (XG-07)."""
    values = tuple(candidates)
    if not values or any(
        not np.isfinite(item.loss)
        or not np.isfinite(item.participation)
        or not np.isfinite(item.score_cutoff)
        or not np.isfinite(item.channel_cutoff)
        or not np.isfinite(item.orientation_floor)
        or not 0.0 <= item.participation <= 1.0
        or item.score_cutoff < 0.0
        or item.channel_cutoff < 0.0
        or not 0.0 <= item.orientation_floor <= 1.0
        for item in values
    ):
        raise ReliabilityExecutionHarnessError("Calibration candidates are invalid")
    return min(
        values,
        key=lambda item: (
            item.loss,
            -item.participation,
            item.score_cutoff,
            item.channel_cutoff,
            -item.orientation_floor,
            item.candidate_id,
        ),
    )


def match_calibration_participation(
    candidates: Sequence[ThresholdCandidate], target: float
) -> ThresholdCandidate:
    """Match comparator participation on calibration values only (XG-07)."""
    if not np.isfinite(target) or not 0.0 <= target <= 1.0:
        raise ReliabilityExecutionHarnessError("Participation target must be in [0, 1]")
    values = tuple(candidates)
    if not values or any(
        not np.isfinite(item.loss)
        or not np.isfinite(item.participation)
        or not 0.0 <= item.participation <= 1.0
        for item in values
    ):
        raise ReliabilityExecutionHarnessError("Comparator candidates are empty")
    return min(
        values,
        key=lambda item: (
            abs(item.participation - target),
            item.loss,
            item.score_cutoff,
            item.channel_cutoff,
            -item.orientation_floor,
            item.candidate_id,
        ),
    )


def rotate_series_channel_assignments(
    series_channels: Sequence[str], represented_channel_order: Sequence[str]
) -> tuple[str, ...]:
    """Break series-to-channel structure without a common row relabeling (XG-08)."""
    order = tuple(represented_channel_order)
    if len(order) < 2 or len(set(order)) != len(order) or not set(series_channels).issubset(order):
        raise ReliabilityExecutionHarnessError("Represented channel order is invalid")
    rotated = {channel: order[(index + 1) % len(order)] for index, channel in enumerate(order)}
    return tuple(rotated[channel] for channel in series_channels)


def cyclic_shift_within_blocks(
    values: object, block_ids: Sequence[str], *, shift: int = 24
) -> FloatArray:
    """Shift timing paths separately inside frozen calibration/evaluation blocks (XG-08)."""
    array = np.asarray(values, dtype=np.float64)
    blocks = tuple(block_ids)
    if array.ndim != 1 or len(blocks) != array.size or shift < 1:
        raise ReliabilityExecutionHarnessError("Timing-path shift inputs are invalid")
    result = array.copy()
    for block in dict.fromkeys(blocks):
        indices = np.asarray([index for index, value in enumerate(blocks) if value == block])
        result[indices] = np.roll(array[indices], shift % len(indices))
    return np.asarray(result, dtype=np.float64)


def permute_label_blocks(
    labels: object, *, block_length: int = 12, seed: int = 2602719
) -> NDArray[np.generic]:
    """Permute complete calibration-label blocks using PCG64 (XG-08)."""
    array = np.asarray(labels)
    if array.ndim != 1 or array.size < block_length or array.size % block_length != 0:
        raise ReliabilityExecutionHarnessError("Labels must form complete frozen blocks")
    blocks = array.reshape(-1, block_length)
    order = np.arange(blocks.shape[0])
    np.random.Generator(np.random.PCG64(seed)).shuffle(order)
    return np.asarray(blocks[order].reshape(-1))


def assess_negative_controls(
    *,
    primary_loss: float,
    primary_success: bool,
    nc1_loss: float,
    nc1_success: bool,
    nc2_loss: float,
    nc2_success: bool,
    primary_threshold_and_loss: str,
    nc3_threshold_and_loss: str,
) -> ControlAssessment:
    """Apply the predeclared numerical control failure rule (XG-09)."""
    values = (primary_loss, nc1_loss, nc2_loss)
    if any(not np.isfinite(value) for value in values):
        raise ReliabilityExecutionHarnessError("Control losses must be finite")
    nc1_degrades = nc1_loss >= primary_loss and not nc1_success
    nc2_degrades = nc2_loss >= primary_loss and not nc2_success
    nc3_reproduced = primary_threshold_and_loss == nc3_threshold_and_loss
    passed = (nc1_degrades or nc2_degrades) and not nc3_reproduced
    reason = "passed" if passed else "negative_control_requirement_failed"
    if not primary_success:
        reason = f"{reason};primary_not_successful"
    return ControlAssessment(
        passed=passed,
        primary_loss=primary_loss,
        nc1_loss=nc1_loss,
        nc2_loss=nc2_loss,
        nc3_jointly_reproduced=nc3_reproduced,
        reason=reason,
    )


def make_noncircular_block_plan(
    sample_size: int, block_length: int, draws: int, seed: int = 2602719
) -> BootstrapPlan:
    """Create deterministic overlapping non-circular block draws (XG-10)."""
    if (
        type(sample_size) is not int
        or type(block_length) is not int
        or type(draws) is not int
        or sample_size < 2
        or block_length < 2
        or block_length > sample_size
        or draws < 2
    ):
        raise ReliabilityExecutionHarnessError("Moving-block contract is invalid")
    starts = np.arange(sample_size - block_length + 1, dtype=np.int64)
    offsets = np.arange(block_length, dtype=np.int64)
    blocks_per_draw = int(np.ceil(sample_size / block_length))
    generator = np.random.Generator(np.random.PCG64(seed))
    indices = np.empty((draws, sample_size), dtype=np.int64)
    for draw in range(draws):
        selected = generator.choice(starts, size=blocks_per_draw, replace=True)
        indices[draw] = np.concatenate([start + offsets for start in selected])[:sample_size]
    return BootstrapPlan(sample_size, block_length, draws, seed, indices)


def simultaneous_bootstrap_intervals(
    bootstrap_estimates: object, point_estimate: object
) -> BootstrapIntervals:
    """Compute the frozen simultaneous studentized intervals (XG-10)."""
    estimates = _finite_matrix(bootstrap_estimates, "Bootstrap estimates")
    point = np.asarray(point_estimate, dtype=np.float64)
    if point.shape != (estimates.shape[1],) or np.any(~np.isfinite(point)):
        raise ReliabilityExecutionHarnessError("Point estimate does not match contrasts")
    standard_error = np.std(estimates, axis=0, ddof=1)
    centered = estimates - point
    studentized = np.zeros_like(centered)
    positive = standard_error > np.finfo(np.float64).eps
    studentized[:, positive] = centered[:, positive] / standard_error[positive]
    maxima = np.max(np.abs(studentized), axis=1)
    critical = float(np.quantile(maxima, 0.95, method="higher"))
    radius = critical * standard_error
    lower = np.where(positive, point - radius, point)
    upper = np.where(positive, point + radius, point)
    return BootstrapIntervals(point, standard_error, lower, upper, critical)


def _canonical_json(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _atomic_create(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise ReliabilityExecutionHarnessError(
            f"refusing to overwrite immutable file: {path}"
        ) from error
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def write_calibration_lock(
    path: Path,
    *,
    approved_amendment_sha256: str,
    implementation_commit: str,
    exact_input_hashes: Mapping[str, str],
    selected_settings: Mapping[str, Any],
    calibration_metrics: Mapping[str, Any],
    evaluation_identity_hashes: Sequence[str],
    invariance_results: Mapping[str, Any],
) -> str:
    """Create the immutable Stage-A lock and return its body hash (XG-11)."""

    def valid_sha(value: str) -> bool:
        return len(value) == 64 and all(character in "0123456789abcdef" for character in value)

    if (
        not valid_sha(approved_amendment_sha256)
        or not implementation_commit
        or not exact_input_hashes
        or any(not key or not valid_sha(value) for key, value in exact_input_hashes.items())
        or not evaluation_identity_hashes
        or any(not valid_sha(value) for value in evaluation_identity_hashes)
    ):
        raise ReliabilityExecutionHarnessError("Calibration lock identities are invalid")
    body: dict[str, Any] = {
        "stage": "calibration_lock",
        "approved_amendment_sha256": approved_amendment_sha256,
        "implementation_commit": implementation_commit,
        "exact_input_hashes": dict(sorted(exact_input_hashes.items())),
        "selected_settings": dict(selected_settings),
        "calibration_metrics": dict(calibration_metrics),
        "evaluation_identity_hashes": sorted(evaluation_identity_hashes),
        "invariance_results": dict(invariance_results),
    }
    body_hash = hashlib.sha256(_canonical_json(body)).hexdigest()
    outer = {**body, "stage_A_sha256": body_hash}
    _atomic_create(path, _canonical_json(outer))
    return body_hash


def start_evaluation_once(
    lock_path: Path,
    marker_path: Path,
    *,
    expected_amendment_sha256: str,
    import_scan_passed: bool,
) -> str:
    """Verify Stage A and atomically create the single-use Stage-B marker (XG-11)."""
    if not import_scan_passed:
        raise ReliabilityExecutionHarnessError("Outcome-module import scan did not pass")
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ReliabilityExecutionHarnessError("Calibration lock must be a mapping")
    registered = payload.pop("stage_A_sha256", None)
    calculated = hashlib.sha256(_canonical_json(payload)).hexdigest()
    if registered != calculated:
        raise ReliabilityExecutionHarnessError("Calibration lock hash mismatch")
    if payload.get("approved_amendment_sha256") != expected_amendment_sha256:
        raise ReliabilityExecutionHarnessError("Approved amendment hash mismatch")
    marker = {
        "stage": "evaluation_started",
        "stage_A_sha256": calculated,
        "marker_version": 1,
    }
    content = _canonical_json(marker)
    _atomic_create(marker_path, content)
    return hashlib.sha256(content).hexdigest()


def implementation_surface() -> dict[str, object]:
    """Return the value-free executable coverage record for the eleven gaps."""
    return {
        "XG-01": build_origin_matrix.__name__,
        "XG-02": apply_slow_release_stress.__name__,
        "XG-03": recover_complete_case_scores.__name__,
        "XG-04": resolve_near_duplicates.__name__,
        "XG-05": rank_invariant_anchor_state.__name__,
        "XG-06": (scenario_history_key.__name__, evaluate_within_scenario_gate.__name__),
        "XG-07": (
            fit_observed_stable_pcp.__name__,
            select_calibration_threshold.__name__,
            match_calibration_participation.__name__,
        ),
        "XG-08": (
            rotate_series_channel_assignments.__name__,
            cyclic_shift_within_blocks.__name__,
            permute_label_blocks.__name__,
        ),
        "XG-09": assess_negative_controls.__name__,
        "XG-10": (
            make_noncircular_block_plan.__name__,
            simultaneous_bootstrap_intervals.__name__,
        ),
        "XG-11": (write_calibration_lock.__name__, start_evaluation_once.__name__),
        "official_values_accessed": False,
        "evaluation_results_accessed": False,
        "outcome_modules_imported": False,
    }
