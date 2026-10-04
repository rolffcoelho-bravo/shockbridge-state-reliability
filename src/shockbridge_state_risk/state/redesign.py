"""Prospective Run 007 continuous-factor and exact scalar-state components."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from shockbridge_state_risk.state.exact_1d import Exact1DKMeansFit, fit_exact_1d_kmeans
from shockbridge_state_risk.state.hmm import FloatArray


class StateRedesignError(ValueError):
    """Raised when a prospective state estimate violates its numerical contract."""


@dataclass(frozen=True)
class ContinuousFactorEstimate:
    filtered_factor_mean: float
    filtered_factor_variance: float
    standardized_factor_mean: float
    standardized_factor_variance: float
    historical_standardized_factors: FloatArray
    loadings: FloatArray
    feature_means: FloatArray
    feature_scales: FloatArray
    factor_location: float
    factor_scale: float
    ar_coefficient: float
    factor_innovation_variance: float
    idiosyncratic_variances: FloatArray
    feature_log_predictive_score: float
    sign_anchor_value: float


@dataclass(frozen=True)
class ExactFactorStatePrediction:
    continuous: ContinuousFactorEstimate
    probabilities: FloatArray
    state_profiles: FloatArray
    exact_fit: Exact1DKMeansFit
    semantic_order: tuple[int, ...]
    factor_mixture_log_score: float
    optimization_status: str = "EXACT_GLOBAL_1D_WITHINSS_OPTIMUM"


def _validate_factor_inputs(
    train: FloatArray,
    current: FloatArray,
    variance_floor: float,
    industrial_production_index: int,
    unemployment_index: int,
) -> None:
    if train.ndim != 2 or train.shape[0] < 4 or train.shape[1] < 3:
        raise StateRedesignError("Continuous factor training data have an invalid shape.")
    if current.ndim != 1 or current.shape[0] != train.shape[1]:
        raise StateRedesignError("Current factor observation has an invalid shape.")
    if variance_floor <= 0:
        raise StateRedesignError("The variance floor must be positive.")
    if np.any(np.isinf(train)) or np.any(np.isinf(current)):
        raise StateRedesignError("Continuous factor inputs cannot contain infinities.")
    if np.any(np.sum(np.isfinite(train), axis=0) < 2):
        raise StateRedesignError("Every factor feature requires two historical observations.")
    if not np.any(np.isfinite(current)):
        raise StateRedesignError("The current factor observation cannot be entirely missing.")
    feature_count = train.shape[1]
    for index in (industrial_production_index, unemployment_index):
        if index < 0 or index >= feature_count:
            raise StateRedesignError("The factor sign-anchor index is out of range.")
    if industrial_production_index == unemployment_index:
        raise StateRedesignError("The factor sign anchor requires distinct features.")


def _orient_loading(
    loading: FloatArray, industrial_production_index: int, unemployment_index: int
) -> tuple[FloatArray, float]:
    oriented = loading.copy()
    anchor = float(oriented[unemployment_index] - oriented[industrial_production_index])
    if anchor < -1e-12:
        oriented *= -1.0
    elif abs(anchor) <= 1e-12:
        largest = int(np.argmax(np.abs(oriented)))
        if oriented[largest] < 0:
            oriented *= -1.0
    return oriented, float(oriented[unemployment_index] - oriented[industrial_production_index])


def _factor_predictive_log_score(
    observation: FloatArray,
    loadings: FloatArray,
    idiosyncratic_variances: FloatArray,
    prior_mean: float,
    prior_variance: float,
) -> float:
    """Score observed features under their joint latent-factor predictive density."""
    predictive_mean = loadings * prior_mean
    covariance = np.diag(idiosyncratic_variances) + prior_variance * np.outer(loadings, loadings)
    sign, log_determinant = np.linalg.slogdet(covariance)
    if sign <= 0 or not np.isfinite(log_determinant):
        raise StateRedesignError("The factor predictive covariance is not positive definite.")
    difference = observation - predictive_mean
    quadratic = float(difference @ np.linalg.solve(covariance, difference))
    return float(-0.5 * (observation.size * np.log(2.0 * np.pi) + log_determinant + quadratic))


def estimate_continuous_factor(
    train: FloatArray,
    current: FloatArray,
    variance_floor: float = 0.05,
    industrial_production_index: int = 1,
    unemployment_index: int = 2,
) -> ContinuousFactorEstimate:
    """Estimate and filter a sign-anchored scalar factor using historical data only."""
    _validate_factor_inputs(
        train,
        current,
        variance_floor,
        industrial_production_index,
        unemployment_index,
    )
    feature_means = np.nanmean(train, axis=0)
    feature_scales = np.nanstd(train, axis=0)
    feature_scales = np.where(feature_scales < 1e-8, 1.0, feature_scales)
    standardized_train = (train - feature_means) / feature_scales
    standardized_current = (current - feature_means) / feature_scales
    filled = np.where(np.isfinite(standardized_train), standardized_train, 0.0)
    _, _, right = np.linalg.svd(filled, full_matrices=False)
    loadings, sign_anchor = _orient_loading(
        right[0], industrial_production_index, unemployment_index
    )
    factors = filled @ loadings
    factor_location = float(np.mean(factors))
    factor_scale = float(np.std(factors))
    if factor_scale < 1e-8:
        raise StateRedesignError("The historical factor has no usable variation.")

    denominator = float(np.sum(factors[:-1] ** 2))
    ar_coefficient = (
        float(np.sum(factors[1:] * factors[:-1]) / denominator) if denominator > 1e-10 else 0.0
    )
    ar_coefficient = float(np.clip(ar_coefficient, -0.98, 0.98))
    innovations = factors[1:] - ar_coefficient * factors[:-1]
    factor_variance = max(float(np.var(innovations)), variance_floor)
    residuals = standardized_train - factors[:, None] * loadings[None, :]
    idiosyncratic_variances = np.maximum(np.nanvar(residuals, axis=0), variance_floor)
    prior_mean = ar_coefficient * float(factors[-1])
    prior_variance = factor_variance
    observed = np.isfinite(standardized_current)
    feature_log_predictive_score = _factor_predictive_log_score(
        standardized_current[observed],
        loadings[observed],
        idiosyncratic_variances[observed],
        prior_mean,
        prior_variance,
    )

    precision = 1.0 / prior_variance
    information = prior_mean / prior_variance
    for feature in np.flatnonzero(observed):
        precision += loadings[feature] ** 2 / idiosyncratic_variances[feature]
        information += (
            loadings[feature] * standardized_current[feature] / idiosyncratic_variances[feature]
        )
    filtered_variance = float(1.0 / precision)
    filtered_mean = float(filtered_variance * information)
    return ContinuousFactorEstimate(
        filtered_factor_mean=filtered_mean,
        filtered_factor_variance=filtered_variance,
        standardized_factor_mean=(filtered_mean - factor_location) / factor_scale,
        standardized_factor_variance=filtered_variance / factor_scale**2,
        historical_standardized_factors=(factors - factor_location) / factor_scale,
        loadings=loadings,
        feature_means=feature_means,
        feature_scales=feature_scales,
        factor_location=factor_location,
        factor_scale=factor_scale,
        ar_coefficient=ar_coefficient,
        factor_innovation_variance=factor_variance,
        idiosyncratic_variances=idiosyncratic_variances,
        feature_log_predictive_score=feature_log_predictive_score,
        sign_anchor_value=sign_anchor,
    )


def _raw_state_profiles(train: FloatArray, labels: NDArray[np.int64], n_states: int) -> FloatArray:
    profiles = np.empty((n_states, train.shape[1]), dtype=np.float64)
    global_means = np.nanmean(train, axis=0)
    for state in range(n_states):
        selection = labels == state
        for feature in range(train.shape[1]):
            observed = selection & np.isfinite(train[:, feature])
            profiles[state, feature] = (
                float(np.mean(train[observed, feature]))
                if np.any(observed)
                else global_means[feature]
            )
    return profiles


def estimate_exact_factor_states(
    train: FloatArray,
    current: FloatArray,
    n_states: int,
    variance_floor: float = 0.05,
    industrial_production_index: int = 1,
    unemployment_index: int = 2,
) -> ExactFactorStatePrediction:
    """Discretize the continuous factor only as an exact, descriptive challenger."""
    continuous = estimate_continuous_factor(
        train,
        current,
        variance_floor,
        industrial_production_index,
        unemployment_index,
    )
    history = continuous.historical_standardized_factors
    exact_fit = fit_exact_1d_kmeans(history, n_states)
    weights = np.asarray(
        [np.sum(exact_fit.labels == state) + 0.5 for state in range(n_states)],
        dtype=np.float64,
    )
    weights /= np.sum(weights)
    log_components = np.log(weights)
    for state in range(n_states):
        selected = history[exact_fit.labels == state]
        variance = max(float(np.var(selected)), variance_floor)
        variance += continuous.standardized_factor_variance
        difference = continuous.standardized_factor_mean - float(exact_fit.centers[state])
        log_components[state] += -0.5 * (np.log(2.0 * np.pi * variance) + difference**2 / variance)
    maximum = float(np.max(log_components))
    factor_mixture_log_score = maximum + float(np.log(np.sum(np.exp(log_components - maximum))))
    probabilities = np.exp(log_components - factor_mixture_log_score)
    profiles = _raw_state_profiles(train, exact_fit.labels, n_states)
    slack_scores = profiles[:, unemployment_index] - profiles[:, industrial_production_index]
    order = np.argsort(slack_scores)
    return ExactFactorStatePrediction(
        continuous=continuous,
        probabilities=probabilities[order],
        state_profiles=profiles[order],
        exact_fit=exact_fit,
        semantic_order=tuple(int(value) for value in order),
        factor_mixture_log_score=factor_mixture_log_score,
    )
