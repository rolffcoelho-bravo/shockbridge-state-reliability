"""Prospective coherent PCA-cluster emission model for Run 007."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from shockbridge_state_risk.state.benchmarks import (
    IntArray,
    KMeansRestartRecord,
    fit_kmeans_restarts,
    semantic_order,
)
from shockbridge_state_risk.state.hmm import FloatArray


class PCAEmissionError(ValueError):
    """Raised when the prospective PCA-emission model cannot be estimated safely."""


@dataclass(frozen=True)
class FullRankPCAEmissionPrediction:
    probabilities: FloatArray
    log_predictive_score: float
    restart_agreement: float
    state_profiles: FloatArray
    labels: IntArray
    leading_cluster_centers: FloatArray
    rotation: FloatArray
    emission_means_pc: FloatArray
    emission_variances_pc: FloatArray
    raw_covariances: FloatArray
    mixture_weights: FloatArray
    restart_records: tuple[KMeansRestartRecord, ...]
    retained_cluster_components: int
    likelihood_dimensions_observed: int
    model_definition: str = "LEADING_PC_CLUSTER_FULL_RANK_PC_EMISSION"


def _validate_inputs(
    train: FloatArray,
    current: FloatArray,
    n_states: int,
    components: int,
    restarts: int,
    variance_floor: float,
) -> tuple[FloatArray, FloatArray]:
    historical = np.asarray(train, dtype=np.float64)
    observation = np.asarray(current, dtype=np.float64)
    if historical.ndim != 2 or historical.shape[0] < max(4, n_states * 2):
        raise PCAEmissionError("PCA emissions require a two-dimensional historical matrix.")
    if historical.shape[1] < 3 or observation.shape != (historical.shape[1],):
        raise PCAEmissionError("The current PCA observation has an invalid feature shape.")
    if np.any(np.isinf(historical)) or np.any(np.isinf(observation)):
        raise PCAEmissionError("PCA-emission inputs cannot contain infinities.")
    if np.any(np.sum(np.isfinite(historical), axis=0) < 2):
        raise PCAEmissionError("Every PCA feature requires two historical observations.")
    if not np.any(np.isfinite(observation)):
        raise PCAEmissionError("The current PCA observation cannot be entirely missing.")
    if n_states < 2 or n_states > historical.shape[0]:
        raise PCAEmissionError("The PCA state count is invalid.")
    if components < 1 or components > historical.shape[1]:
        raise PCAEmissionError("The retained PCA component count is invalid.")
    if restarts < 2 or not np.isfinite(variance_floor) or variance_floor <= 0:
        raise PCAEmissionError("PCA restarts and variance floor must be positive.")
    return historical, observation


def _log_multivariate_normal(
    observation: FloatArray, mean: FloatArray, covariance: FloatArray
) -> float:
    sign, log_determinant = np.linalg.slogdet(covariance)
    if sign <= 0 or not np.isfinite(log_determinant):
        raise PCAEmissionError("A PCA emission covariance is not positive definite.")
    difference = observation - mean
    quadratic = float(difference @ np.linalg.solve(covariance, difference))
    return float(-0.5 * (observation.size * np.log(2.0 * np.pi) + log_determinant + quadratic))


def _state_profiles(train: FloatArray, labels: IntArray, n_states: int) -> FloatArray:
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


def predict_full_rank_pca_emission(
    train: FloatArray,
    current: FloatArray,
    n_states: int,
    components: int,
    restarts: int,
    variance_floor: float,
    seed: int,
) -> FullRankPCAEmissionPrediction:
    """Cluster in leading-PC space and score in the full raw-feature dimension.

    Inputs must already be standardized with moments from the admissible historical
    estimation window. Missing historical entries are therefore replaced by zero,
    the estimation-window standardized mean. The likelihood is marginalized to the
    raw feature dimensions observed at the current origin.
    """
    historical, observation = _validate_inputs(
        train, current, n_states, components, restarts, variance_floor
    )
    filled = np.where(np.isfinite(historical), historical, 0.0)
    _, _, rotation = np.linalg.svd(filled, full_matrices=False)
    if rotation.shape != (historical.shape[1], historical.shape[1]):
        raise PCAEmissionError("Full-rank PCA emissions require at least as many rows as features.")
    all_scores = filled @ rotation.T
    kmeans = fit_kmeans_restarts(all_scores[:, :components], n_states, restarts, seed)

    global_variances = np.maximum(np.var(all_scores, axis=0), variance_floor)
    emission_means = np.empty((n_states, historical.shape[1]), dtype=np.float64)
    emission_variances = np.empty_like(emission_means)
    raw_covariances = np.empty(
        (n_states, historical.shape[1], historical.shape[1]), dtype=np.float64
    )
    weights = np.empty(n_states, dtype=np.float64)
    for state in range(n_states):
        selected = all_scores[kmeans.labels == state]
        if selected.shape[0] == 0:
            raise PCAEmissionError("PCA clustering produced an empty state.")
        weights[state] = selected.shape[0] + 0.5
        emission_means[state] = np.mean(selected, axis=0)
        emission_variances[state] = (
            np.maximum(np.var(selected, axis=0), variance_floor)
            if selected.shape[0] >= 2
            else global_variances
        )
        raw_covariances[state] = rotation.T @ np.diag(emission_variances[state]) @ rotation
    weights /= np.sum(weights)

    observed = np.isfinite(observation)
    log_components = np.log(weights)
    for state in range(n_states):
        raw_mean = emission_means[state] @ rotation
        observed_covariance = raw_covariances[state][np.ix_(observed, observed)]
        log_components[state] += _log_multivariate_normal(
            observation[observed], raw_mean[observed], observed_covariance
        )
    maximum = float(np.max(log_components))
    log_score = maximum + float(np.log(np.sum(np.exp(log_components - maximum))))
    probabilities = np.exp(log_components - log_score)

    profiles = _state_profiles(historical, kmeans.labels, n_states)
    order = np.asarray(semantic_order(profiles), dtype=np.int64)
    inverse = np.empty(n_states, dtype=np.int64)
    inverse[order] = np.arange(n_states, dtype=np.int64)
    semantic_restart_records = tuple(
        KMeansRestartRecord(
            seed=record.seed,
            inertia=record.inertia,
            objective_gap_from_best=record.objective_gap_from_best,
            aligned_hard_assignments=tuple(
                int(inverse[value]) for value in record.aligned_hard_assignments
            ),
            agreement_with_best=record.agreement_with_best,
        )
        for record in kmeans.restart_records
    )
    return FullRankPCAEmissionPrediction(
        probabilities=probabilities[order],
        log_predictive_score=log_score,
        restart_agreement=kmeans.restart_agreement,
        state_profiles=profiles[order],
        labels=inverse[kmeans.labels],
        leading_cluster_centers=kmeans.centers[order],
        rotation=rotation,
        emission_means_pc=emission_means[order],
        emission_variances_pc=emission_variances[order],
        raw_covariances=raw_covariances[order],
        mixture_weights=weights[order],
        restart_records=semantic_restart_records,
        retained_cluster_components=components,
        likelihood_dimensions_observed=int(np.sum(observed)),
    )
