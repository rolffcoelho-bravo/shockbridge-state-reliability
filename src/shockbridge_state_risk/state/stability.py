"""Prospective, outcome-blind stability metrics and gates for Run 007."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from shockbridge_state_risk.state.hmm import FloatArray


class StabilityError(ValueError):
    """Raised when stability inputs cannot support the declared diagnostics."""


@dataclass(frozen=True)
class StabilityThresholds:
    minimum_pearson_correlation: float
    minimum_spearman_correlation: float
    maximum_sign_disagreement_rate: float
    maximum_standardized_mean_absolute_difference: float
    minimum_median_loading_cosine: float
    minimum_loading_cosine: float
    minimum_anchor_tenth_percentile: float
    weak_anchor_cutoff: float
    maximum_weak_anchor_rate: float


@dataclass(frozen=True)
class StabilityAudit:
    pearson_correlation: float
    spearman_correlation: float
    sign_disagreement_rate: float
    standardized_mean_absolute_difference: float
    median_loading_cosine: float
    minimum_loading_cosine: float
    anchor_tenth_percentile: float
    weak_anchor_rate: float
    gates: tuple[tuple[str, bool], ...]

    @property
    def passed(self) -> bool:
        return all(value for _, value in self.gates)


def _average_ranks(values: FloatArray) -> FloatArray:
    order = np.argsort(values, kind="stable")
    ranks = np.empty(values.size, dtype=np.float64)
    start = 0
    while start < values.size:
        stop = start + 1
        while stop < values.size and values[order[stop]] == values[order[start]]:
            stop += 1
        ranks[order[start:stop]] = 0.5 * (start + stop - 1)
        start = stop
    return ranks


def _correlation(left: FloatArray, right: FloatArray) -> float:
    left_centered = left - np.mean(left)
    right_centered = right - np.mean(right)
    denominator = float(np.sqrt(np.sum(left_centered**2) * np.sum(right_centered**2)))
    if denominator <= 1e-14:
        raise StabilityError("Stability correlations require variation in both series.")
    return float(np.sum(left_centered * right_centered) / denominator)


def _validate_thresholds(thresholds: StabilityThresholds) -> None:
    values = tuple(thresholds.__dict__.values())
    if any(not np.isfinite(value) for value in values):
        raise StabilityError("Stability thresholds must be finite.")
    unit_interval = (
        thresholds.minimum_pearson_correlation,
        thresholds.minimum_spearman_correlation,
        thresholds.maximum_sign_disagreement_rate,
        thresholds.minimum_median_loading_cosine,
        thresholds.minimum_loading_cosine,
        thresholds.maximum_weak_anchor_rate,
    )
    if any(not 0.0 <= value <= 1.0 for value in unit_interval):
        raise StabilityError("Correlation, cosine, and rate thresholds must lie in [0, 1].")
    if (
        thresholds.maximum_standardized_mean_absolute_difference < 0
        or thresholds.minimum_anchor_tenth_percentile < 0
        or thresholds.weak_anchor_cutoff < 0
    ):
        raise StabilityError("Difference and anchor thresholds cannot be negative.")
    if thresholds.minimum_loading_cosine > thresholds.minimum_median_loading_cosine:
        raise StabilityError("The minimum loading cosine cannot exceed the median threshold.")


def evaluate_factor_stability(
    expanding_factors: FloatArray,
    rolling_factors: FloatArray,
    expanding_loadings: FloatArray,
    rolling_loadings: FloatArray,
    expanding_anchors: FloatArray,
    rolling_anchors: FloatArray,
    thresholds: StabilityThresholds,
) -> StabilityAudit:
    """Evaluate paired-window consistency without consulting response outcomes."""
    _validate_thresholds(thresholds)
    expanding = np.asarray(expanding_factors, dtype=np.float64)
    rolling = np.asarray(rolling_factors, dtype=np.float64)
    left_loadings = np.asarray(expanding_loadings, dtype=np.float64)
    right_loadings = np.asarray(rolling_loadings, dtype=np.float64)
    left_anchors = np.asarray(expanding_anchors, dtype=np.float64)
    right_anchors = np.asarray(rolling_anchors, dtype=np.float64)
    if expanding.ndim != 1 or rolling.shape != expanding.shape or expanding.size < 3:
        raise StabilityError("Factor stability requires paired one-dimensional series.")
    if (
        left_loadings.ndim != 2
        or right_loadings.shape != left_loadings.shape
        or left_loadings.shape[0] != expanding.size
    ):
        raise StabilityError("Loading stability requires paired origin-by-feature matrices.")
    if left_anchors.shape != expanding.shape or right_anchors.shape != expanding.shape:
        raise StabilityError("Anchor stability requires one paired value per origin.")
    arrays = (expanding, rolling, left_loadings, right_loadings, left_anchors, right_anchors)
    if any(np.any(~np.isfinite(array)) for array in arrays):
        raise StabilityError("Stability inputs must be finite.")
    if np.any(left_anchors < 0) or np.any(right_anchors < 0):
        raise StabilityError("Sign-anchored loadings cannot have negative anchor values.")

    pearson = _correlation(expanding, rolling)
    spearman = _correlation(_average_ranks(expanding), _average_ranks(rolling))
    sign_disagreement = float(np.mean(np.sign(expanding) != np.sign(rolling)))
    pooled_scale = float(np.sqrt((np.var(expanding) + np.var(rolling)) / 2.0))
    if pooled_scale <= 1e-14:
        raise StabilityError("Standardized factor differences require pooled variation.")
    standardized_mad = float(np.mean(np.abs(expanding - rolling)) / pooled_scale)

    left_norms = np.linalg.norm(left_loadings, axis=1)
    right_norms = np.linalg.norm(right_loadings, axis=1)
    if np.any(left_norms <= 1e-14) or np.any(right_norms <= 1e-14):
        raise StabilityError("Loading vectors must have nonzero norm.")
    cosines = np.clip(
        np.sum(left_loadings * right_loadings, axis=1) / (left_norms * right_norms),
        -1.0,
        1.0,
    )
    anchor_tenth_percentile = min(
        float(np.percentile(left_anchors, 10.0)),
        float(np.percentile(right_anchors, 10.0)),
    )
    weak_anchor_rate = max(
        float(np.mean(left_anchors < thresholds.weak_anchor_cutoff)),
        float(np.mean(right_anchors < thresholds.weak_anchor_cutoff)),
    )
    median_cosine = float(np.median(cosines))
    minimum_cosine = float(np.min(cosines))
    gates = (
        ("pearson_correlation", pearson >= thresholds.minimum_pearson_correlation),
        ("spearman_correlation", spearman >= thresholds.minimum_spearman_correlation),
        (
            "sign_disagreement_rate",
            sign_disagreement <= thresholds.maximum_sign_disagreement_rate,
        ),
        (
            "standardized_mean_absolute_difference",
            standardized_mad <= thresholds.maximum_standardized_mean_absolute_difference,
        ),
        ("median_loading_cosine", median_cosine >= thresholds.minimum_median_loading_cosine),
        ("minimum_loading_cosine", minimum_cosine >= thresholds.minimum_loading_cosine),
        (
            "anchor_tenth_percentile",
            anchor_tenth_percentile >= thresholds.minimum_anchor_tenth_percentile,
        ),
        ("weak_anchor_rate", weak_anchor_rate <= thresholds.maximum_weak_anchor_rate),
    )
    return StabilityAudit(
        pearson_correlation=pearson,
        spearman_correlation=spearman,
        sign_disagreement_rate=sign_disagreement,
        standardized_mean_absolute_difference=standardized_mad,
        median_loading_cosine=median_cosine,
        minimum_loading_cosine=minimum_cosine,
        anchor_tenth_percentile=anchor_tenth_percentile,
        weak_anchor_rate=weak_anchor_rate,
        gates=gates,
    )
