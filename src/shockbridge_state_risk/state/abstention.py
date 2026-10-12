"""Selective-authorization primitives for dependent measurement diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from numpy.typing import NDArray

from shockbridge_state_risk.state.hmm import FloatArray


class AbstentionError(ValueError):
    """Raised when a selective-authorization input violates its contract."""


BoolArray = NDArray[np.bool_]
IntArray = NDArray[np.int64]


@dataclass(frozen=True)
class PolicyMetrics:
    """Observed loss and risk summaries for one fixed authorization rule."""

    observations: int
    authorized: int
    future_breaches: int
    false_authorizations: int
    coverage: float
    abstention_rate: float
    future_breach_prevalence: float
    false_authorization_rate: float
    selective_risk: Optional[float]
    mean_loss: float


def geometry_risk_score(
    second_principal_cosines: FloatArray,
    normalized_projector_distances: FloatArray,
    *,
    cosine_boundary: float = 0.75,
    projector_boundary: float = 0.35,
) -> FloatArray:
    """Return the worst relative violation of the two frozen geometry boundaries."""
    cosines = np.asarray(second_principal_cosines, dtype=np.float64)
    distances = np.asarray(normalized_projector_distances, dtype=np.float64)
    if (
        cosines.ndim != 1
        or distances.shape != cosines.shape
        or cosines.size == 0
        or np.any(~np.isfinite(cosines))
        or np.any(~np.isfinite(distances))
        or not np.isfinite(cosine_boundary)
        or not np.isfinite(projector_boundary)
        or cosine_boundary <= 0.0
        or projector_boundary <= 0.0
    ):
        raise AbstentionError("Geometry-score inputs are invalid.")
    cosine_risk = (cosine_boundary - cosines) / cosine_boundary
    projector_risk = (distances - projector_boundary) / projector_boundary
    return np.maximum(cosine_risk, projector_risk)


def future_any_breach(breaches: BoolArray, horizon: int) -> BoolArray:
    """Label whether any breach occurs strictly after each eligible origin."""
    values = np.asarray(breaches)
    if (
        values.ndim != 1
        or values.dtype.kind != "b"
        or values.size <= horizon
        or isinstance(horizon, bool)
        or horizon < 1
    ):
        raise AbstentionError("Future-breach inputs are invalid.")
    return np.asarray(
        [np.any(values[index + 1 : index + horizon + 1]) for index in range(values.size - horizon)],
        dtype=np.bool_,
    )


def authorization_actions(scores: FloatArray, threshold: float) -> BoolArray:
    """Authorize observations whose risk score does not exceed the threshold."""
    values = np.asarray(scores, dtype=np.float64)
    if values.ndim != 1 or values.size == 0 or np.any(~np.isfinite(values)):
        raise AbstentionError("Authorization scores must be a finite vector.")
    if np.isnan(threshold):
        raise AbstentionError("Authorization threshold cannot be NaN.")
    return np.asarray(values <= threshold, dtype=np.bool_)


def policy_metrics(
    actions: BoolArray,
    future_breaches: BoolArray,
    abstention_cost: float,
) -> PolicyMetrics:
    """Evaluate a fixed policy without replacing an undefined zero-coverage risk."""
    authorized = np.asarray(actions)
    future = np.asarray(future_breaches)
    if (
        authorized.ndim != 1
        or authorized.dtype.kind != "b"
        or future.shape != authorized.shape
        or future.dtype.kind != "b"
        or authorized.size == 0
        or not np.isfinite(abstention_cost)
        or not 0.0 <= abstention_cost <= 1.0
    ):
        raise AbstentionError("Policy-metric inputs are invalid.")
    false_authorization = authorized & future
    losses = false_authorization.astype(np.float64) + abstention_cost * (~authorized)
    authorization_count = int(np.sum(authorized))
    false_count = int(np.sum(false_authorization))
    observations = int(authorized.size)
    return PolicyMetrics(
        observations=observations,
        authorized=authorization_count,
        future_breaches=int(np.sum(future)),
        false_authorizations=false_count,
        coverage=authorization_count / observations,
        abstention_rate=1.0 - authorization_count / observations,
        future_breach_prevalence=float(np.mean(future)),
        false_authorization_rate=false_count / observations,
        selective_risk=(false_count / authorization_count if authorization_count else None),
        mean_loss=float(np.mean(losses)),
    )


def policy_losses(
    actions: BoolArray,
    future_breaches: BoolArray,
    abstention_cost: float,
) -> FloatArray:
    """Return per-origin losses for paired uncertainty calculations."""
    policy_metrics(actions, future_breaches, abstention_cost)
    authorized = np.asarray(actions)
    future = np.asarray(future_breaches)
    return (authorized & future).astype(np.float64) + abstention_cost * (~authorized)


def conservative_thresholds(calibration_scores: FloatArray) -> tuple[float, ...]:
    """Build the frozen candidate family, including explicit always-abstain."""
    scores = np.asarray(calibration_scores, dtype=np.float64)
    if scores.ndim != 1 or scores.size == 0 or np.any(~np.isfinite(scores)):
        raise AbstentionError("Calibration scores must be a finite vector.")
    nonpositive = sorted({float(value) for value in scores if value <= 0.0})
    if not nonpositive or nonpositive[-1] != 0.0:
        nonpositive.append(0.0)
    return (-np.inf, *nonpositive)


def select_threshold(
    calibration_scores: FloatArray,
    future_breaches: BoolArray,
    abstention_cost: float,
) -> tuple[float, PolicyMetrics]:
    """Minimize calibration loss and break exact ties toward more abstention."""
    scores = np.asarray(calibration_scores, dtype=np.float64)
    future = np.asarray(future_breaches)
    if future.shape != scores.shape:
        raise AbstentionError("Calibration scores and labels must align.")
    candidates = conservative_thresholds(scores)
    evaluated = [
        (
            threshold,
            policy_metrics(authorization_actions(scores, threshold), future, abstention_cost),
        )
        for threshold in candidates
    ]
    return min(evaluated, key=lambda item: (item[1].mean_loss, item[0]))


def negative_control_scores(scores: FloatArray, control_id: str) -> FloatArray:
    """Apply a frozen distribution-preserving calendar-misalignment control."""
    values = np.asarray(scores, dtype=np.float64)
    if values.ndim != 1 or values.size == 0 or np.any(~np.isfinite(values)):
        raise AbstentionError("Negative-control scores must be a finite vector.")
    if control_id == "reverse_time":
        transformed = values[::-1]
    elif control_id == "rotate_23":
        transformed = np.roll(values, -23)
    else:
        raise AbstentionError(f"Unknown negative control: {control_id}")
    if not np.array_equal(np.sort(values), np.sort(transformed)):
        raise AbstentionError("Negative control changed the score multiset.")
    return np.asarray(transformed, dtype=np.float64)


def moving_block_indices(
    observations: int,
    block_length: int,
    resamples: int,
    seed: int,
) -> IntArray:
    """Draw noncircular moving blocks and truncate the final sampled block."""
    if (
        isinstance(observations, bool)
        or isinstance(block_length, bool)
        or isinstance(resamples, bool)
        or isinstance(seed, bool)
        or observations < 2
        or not 1 <= block_length <= observations
        or resamples < 1
        or seed < 0
    ):
        raise AbstentionError("Moving-block bootstrap settings are invalid.")
    rng = np.random.default_rng(seed)
    blocks_needed = (observations + block_length - 1) // block_length
    starts = rng.integers(
        0,
        observations - block_length + 1,
        size=(resamples, blocks_needed),
    )
    offsets = np.arange(block_length, dtype=np.int64)
    sampled = starts[:, :, None] + offsets[None, None, :]
    return np.asarray(sampled.reshape(resamples, -1)[:, :observations], dtype=np.int64)


def percentile_interval(values: FloatArray) -> tuple[float, float]:
    """Return the frozen equal-tail 95% percentile interval."""
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or array.size == 0 or np.any(~np.isfinite(array)):
        raise AbstentionError("Interval inputs must be a finite vector.")
    lower, upper = np.quantile(array, [0.025, 0.975])
    return float(lower), float(upper)
