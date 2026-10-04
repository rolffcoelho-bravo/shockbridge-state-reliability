"""Outcome-blind latent-state benchmark models on a regular monthly calendar."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Optional

import numpy as np
from numpy.typing import NDArray

from shockbridge_state_risk.state.hmm import (
    FloatArray,
    alignment_order,
    filter_next,
    fit_hmm_restarts,
    reorder_fit,
)


class BenchmarkError(ValueError):
    """Raised when a benchmark cannot produce an auditable prediction."""


IntArray = NDArray[np.int64]


@dataclass(frozen=True)
class BenchmarkPrediction:
    probabilities: FloatArray
    log_predictive_score: float
    restart_agreement: Optional[float]
    converged: bool
    state_profiles: FloatArray


@dataclass(frozen=True)
class KMeansRestartRecord:
    seed: int
    inertia: float
    objective_gap_from_best: float
    aligned_hard_assignments: tuple[int, ...]
    agreement_with_best: float


@dataclass(frozen=True)
class KMeansFit:
    labels: IntArray
    centers: FloatArray
    inertia: float
    restart_agreement: float
    restart_records: tuple[KMeansRestartRecord, ...]


def expanding_standardize(
    train: FloatArray, current: FloatArray
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    means = np.nanmean(train, axis=0)
    scales = np.nanstd(train, axis=0)
    scales = np.where(scales < 1e-8, 1.0, scales)
    return (train - means) / scales, (current - means) / scales, means, scales


def _logsumexp(values: FloatArray) -> float:
    maximum = float(np.max(values))
    return maximum + float(np.log(np.sum(np.exp(values - maximum))))


def _softmax_log(log_values: FloatArray) -> tuple[FloatArray, float]:
    normalizer = _logsumexp(log_values)
    return np.exp(log_values - normalizer), normalizer


def _kmeans_once(
    values: FloatArray, n_states: int, seed: int, max_iterations: int = 100
) -> tuple[IntArray, FloatArray, float]:
    if values.ndim != 2 or values.shape[0] < n_states:
        raise BenchmarkError("K-means needs at least one row per state.")
    generator = np.random.default_rng(seed)
    chosen = [int(generator.integers(values.shape[0]))]
    while len(chosen) < n_states:
        distances = np.min(
            np.sum((values[:, None, :] - values[np.asarray(chosen)][None, :, :]) ** 2, axis=2),
            axis=1,
        )
        if float(np.sum(distances)) <= 1e-12:
            remaining = [index for index in range(values.shape[0]) if index not in chosen]
            chosen.append(remaining[0])
        else:
            probabilities = distances / np.sum(distances)
            chosen.append(int(generator.choice(values.shape[0], p=probabilities)))
    centers = values[np.asarray(chosen)].copy()
    labels = np.zeros(values.shape[0], dtype=np.int64)
    for _ in range(max_iterations):
        distances = np.sum((values[:, None, :] - centers[None, :, :]) ** 2, axis=2)
        updated_labels = np.argmin(distances, axis=1)
        updated_centers = centers.copy()
        for state in range(n_states):
            selection = updated_labels == state
            if np.any(selection):
                updated_centers[state] = np.mean(values[selection], axis=0)
            else:
                farthest = int(np.argmax(np.min(distances, axis=1)))
                updated_centers[state] = values[farthest]
        if np.array_equal(updated_labels, labels) and np.allclose(updated_centers, centers):
            labels = updated_labels
            centers = updated_centers
            break
        labels = updated_labels
        centers = updated_centers
    inertia = float(np.sum((values - centers[labels]) ** 2))
    return labels, centers, inertia


def _center_order(reference: FloatArray, candidate: FloatArray) -> tuple[int, ...]:
    return min(
        permutations(range(reference.shape[0])),
        key=lambda order: float(np.sum((reference - candidate[np.asarray(order), :]) ** 2)),
    )


def fit_kmeans_restarts(values: FloatArray, n_states: int, restarts: int, seed: int) -> KMeansFit:
    if restarts < 2:
        raise BenchmarkError("K-means stability requires at least two restarts.")
    fits = [_kmeans_once(values, n_states, seed + restart * 1009) for restart in range(restarts)]
    best_labels, best_centers, best_inertia = min(fits, key=lambda item: item[2])
    agreements: list[float] = []
    aligned_assignments: list[tuple[int, ...]] = []
    for labels, centers, _ in fits:
        order = _center_order(best_centers, centers)
        inverse = np.empty(n_states, dtype=np.int64)
        for best_state, candidate_state in enumerate(order):
            inverse[candidate_state] = best_state
        aligned = inverse[labels]
        aligned_assignments.append(tuple(int(value) for value in aligned))
        agreements.append(float(np.mean(best_labels == aligned)))
    records = tuple(
        KMeansRestartRecord(
            seed=seed + restart * 1009,
            inertia=float(fit[2]),
            objective_gap_from_best=float(fit[2] - best_inertia),
            aligned_hard_assignments=aligned_assignments[restart],
            agreement_with_best=agreements[restart],
        )
        for restart, fit in enumerate(fits)
    )
    return KMeansFit(best_labels, best_centers, best_inertia, min(agreements), records)


def _state_profiles(train: FloatArray, labels: IntArray, n_states: int) -> FloatArray:
    global_means = np.nanmean(train, axis=0)
    profiles = np.empty((n_states, train.shape[1]), dtype=np.float64)
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


def semantic_order(profiles: FloatArray) -> tuple[int, ...]:
    """Order hot/strong states toward zero and slack states toward the end."""
    if profiles.shape[1] < 3:
        raise BenchmarkError("Semantic ordering requires IP and unemployment features.")
    slack_score = profiles[:, 2] - profiles[:, 1]
    return tuple(int(index) for index in np.argsort(slack_score))


def _mixture_prediction(
    train: FloatArray,
    current: FloatArray,
    labels: IntArray,
    n_states: int,
    variance_floor: float,
) -> tuple[FloatArray, float, FloatArray]:
    profiles = _state_profiles(train, labels, n_states)
    variances = np.empty_like(profiles)
    weights = np.empty(n_states, dtype=np.float64)
    global_variances = np.maximum(np.nanvar(train, axis=0), variance_floor)
    for state in range(n_states):
        selection = labels == state
        weights[state] = float(np.sum(selection)) + 0.5
        for feature in range(train.shape[1]):
            observed = selection & np.isfinite(train[:, feature])
            variances[state, feature] = (
                max(float(np.var(train[observed, feature])), variance_floor)
                if np.sum(observed) >= 2
                else global_variances[feature]
            )
    weights /= np.sum(weights)
    observed = np.isfinite(current)
    log_components = np.log(weights)
    for state in range(n_states):
        terms = np.log(2.0 * np.pi * variances[state, observed]) + (
            (current[observed] - profiles[state, observed]) ** 2 / variances[state, observed]
        )
        log_components[state] += -0.5 * float(np.sum(terms))
    probabilities, score = _softmax_log(log_components)
    return probabilities, score, profiles


def _ordered_prediction(
    probabilities: FloatArray,
    score: float,
    profiles: FloatArray,
    agreement: Optional[float],
    converged: bool = True,
) -> BenchmarkPrediction:
    order = semantic_order(profiles)
    index = np.asarray(order)
    return BenchmarkPrediction(
        probabilities=probabilities[index],
        log_predictive_score=score,
        restart_agreement=agreement,
        converged=converged,
        state_profiles=profiles[index],
    )


def predict_pca_cluster(
    train: FloatArray,
    current: FloatArray,
    n_states: int,
    components: int,
    restarts: int,
    variance_floor: float,
    seed: int,
) -> BenchmarkPrediction:
    filled = np.where(np.isfinite(train), train, 0.0)
    current_filled = np.where(np.isfinite(current), current, 0.0)
    _, _, right = np.linalg.svd(filled, full_matrices=False)
    count = min(components, right.shape[0])
    scores = filled @ right[:count].T
    _ = current_filled @ right[:count].T
    kmeans = fit_kmeans_restarts(scores, n_states, restarts, seed)
    probabilities, score, profiles = _mixture_prediction(
        train, current, kmeans.labels, n_states, variance_floor
    )
    return _ordered_prediction(probabilities, score, profiles, kmeans.restart_agreement)


def _scalar_state_prediction(
    history: FloatArray,
    current_mean: float,
    current_variance: float,
    kmeans: KMeansFit,
    raw_train: FloatArray,
    variance_floor: float,
) -> tuple[FloatArray, FloatArray]:
    n_states = kmeans.centers.shape[0]
    weights = np.asarray(
        [np.sum(kmeans.labels == state) + 0.5 for state in range(n_states)],
        dtype=np.float64,
    )
    weights /= np.sum(weights)
    log_components = np.log(weights)
    for state in range(n_states):
        selected = history[kmeans.labels == state]
        variance = max(float(np.var(selected)), variance_floor) + current_variance
        difference = current_mean - float(kmeans.centers[state, 0])
        log_components[state] += -0.5 * (np.log(2.0 * np.pi * variance) + difference**2 / variance)
    probabilities, _ = _softmax_log(log_components)
    return probabilities, _state_profiles(raw_train, kmeans.labels, n_states)


def predict_dynamic_factor(
    train: FloatArray,
    current: FloatArray,
    n_states: int,
    restarts: int,
    variance_floor: float,
    seed: int,
) -> BenchmarkPrediction:
    filled = np.where(np.isfinite(train), train, 0.0)
    _, _, right = np.linalg.svd(filled, full_matrices=False)
    loadings = right[0].copy()
    if loadings[2] - loadings[1] < 0:
        loadings *= -1.0
    factors = filled @ loadings
    denominator = float(np.sum(factors[:-1] ** 2))
    phi = float(np.sum(factors[1:] * factors[:-1]) / denominator) if denominator > 1e-10 else 0.0
    phi = float(np.clip(phi, -0.98, 0.98))
    innovations = factors[1:] - phi * factors[:-1]
    factor_variance = max(float(np.var(innovations)), variance_floor)
    residuals = train - factors[:, None] * loadings[None, :]
    idiosyncratic = np.maximum(np.nanvar(residuals, axis=0), variance_floor)
    prior_mean = phi * float(factors[-1])
    prior_variance = factor_variance
    observed = np.isfinite(current)
    predictive_means = loadings[observed] * prior_mean
    predictive_variances = idiosyncratic[observed] + (loadings[observed] ** 2 * prior_variance)
    terms = np.log(2.0 * np.pi * predictive_variances) + (
        (current[observed] - predictive_means) ** 2 / predictive_variances
    )
    score = float(-0.5 * np.sum(terms))

    precision = 1.0 / prior_variance
    information = prior_mean / prior_variance
    for feature in np.flatnonzero(observed):
        precision += loadings[feature] ** 2 / idiosyncratic[feature]
        information += loadings[feature] * current[feature] / idiosyncratic[feature]
    filtered_variance = 1.0 / precision
    filtered_mean = filtered_variance * information
    kmeans = fit_kmeans_restarts(factors[:, None], n_states, restarts, seed)
    probabilities, profiles = _scalar_state_prediction(
        factors,
        filtered_mean,
        filtered_variance,
        kmeans,
        train,
        variance_floor,
    )
    return _ordered_prediction(probabilities, score, profiles, kmeans.restart_agreement)


def predict_hidden_markov(
    train: FloatArray,
    current: FloatArray,
    n_states: int,
    restarts: int,
    max_iterations: int,
    tolerance: float,
    variance_floor: float,
    transition_prior: float,
    seed: int,
) -> BenchmarkPrediction:
    best, fits = fit_hmm_restarts(
        train,
        n_states,
        restarts,
        max_iterations,
        tolerance,
        variance_floor,
        transition_prior,
        seed,
    )
    order = semantic_order(best.parameters.means)
    best = reorder_fit(best, order)
    best_labels = np.argmax(best.filtered_probabilities, axis=1)
    agreements: list[float] = []
    for fit in fits:
        aligned_order = alignment_order(best.parameters.means, fit.parameters.means)
        aligned = reorder_fit(fit, aligned_order)
        agreements.append(
            float(np.mean(best_labels == np.argmax(aligned.filtered_probabilities, axis=1)))
        )
    probabilities, score = filter_next(best.parameters, best.filtered_probabilities[-1], current)
    return BenchmarkPrediction(
        probabilities=probabilities,
        log_predictive_score=score,
        restart_agreement=min(agreements),
        converged=best.converged,
        state_profiles=best.parameters.means,
    )


def _causal_change_signal(
    factors: FloatArray, threshold: float, minimum_segment: int
) -> tuple[FloatArray, int]:
    signals = np.empty_like(factors)
    segment_start = 0
    for index, value in enumerate(factors):
        segment = factors[segment_start:index]
        if segment.size >= minimum_segment:
            scale = max(float(np.std(segment)), 0.25)
            if abs(float(value) - float(np.mean(segment))) / scale > threshold:
                segment_start = index
        signals[index] = float(np.mean(factors[segment_start : index + 1]))
    return signals, segment_start


def predict_change_point(
    train: FloatArray,
    current: FloatArray,
    n_states: int,
    restarts: int,
    variance_floor: float,
    threshold: float,
    minimum_segment: int,
    seed: int,
) -> BenchmarkPrediction:
    filled = np.where(np.isfinite(train), train, 0.0)
    _, _, right = np.linalg.svd(filled, full_matrices=False)
    loading = right[0].copy()
    if loading[2] - loading[1] < 0:
        loading *= -1.0
    factors = filled @ loading
    signals, segment_start = _causal_change_signal(factors, threshold, minimum_segment)
    current_factor = float(np.where(np.isfinite(current), current, 0.0) @ loading)
    segment = factors[segment_start:]
    segment_scale = max(float(np.std(segment)), 0.25)
    changed = (
        segment.size >= minimum_segment
        and abs(current_factor - float(np.mean(segment))) / segment_scale > threshold
    )
    current_signal = (
        current_factor
        if changed
        else float((np.sum(segment) + current_factor) / (segment.size + 1))
    )
    segment_rows = train[segment_start:]
    global_means = np.nanmean(train, axis=0)
    global_variances = np.maximum(np.nanvar(train, axis=0), variance_floor)
    predictive_means = global_means.copy()
    predictive_variances = global_variances.copy()
    for feature in range(train.shape[1]):
        observed_segment = segment_rows[np.isfinite(segment_rows[:, feature]), feature]
        if observed_segment.size:
            predictive_means[feature] = float(np.mean(observed_segment))
        if observed_segment.size >= 2:
            predictive_variances[feature] = max(float(np.var(observed_segment)), variance_floor)
    observed = np.isfinite(current)
    terms = np.log(2.0 * np.pi * predictive_variances[observed]) + (
        (current[observed] - predictive_means[observed]) ** 2 / predictive_variances[observed]
    )
    score = float(-0.5 * np.sum(terms))
    kmeans = fit_kmeans_restarts(signals[:, None], n_states, restarts, seed)
    probabilities, profiles = _scalar_state_prediction(
        signals,
        current_signal,
        0.0,
        kmeans,
        train,
        variance_floor,
    )
    return _ordered_prediction(probabilities, score, profiles, kmeans.restart_agreement)
