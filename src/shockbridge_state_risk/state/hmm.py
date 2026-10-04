"""Small, auditable diagonal-Gaussian HMM with native missing-data likelihoods."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Optional

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


class HMMError(ValueError):
    """Raised when a latent-state fit violates numerical or shape requirements."""


@dataclass(frozen=True)
class HMMParameters:
    initial: FloatArray
    transition: FloatArray
    means: FloatArray
    variances: FloatArray


@dataclass(frozen=True)
class HMMFit:
    parameters: HMMParameters
    log_likelihood: float
    regularized_objective: float
    iterations: int
    converged: bool
    seed: int
    filtered_probabilities: FloatArray


@dataclass(frozen=True)
class HMMRestartRecord:
    seed: int
    converged: bool
    iterations: int
    log_likelihood: float
    regularized_objective: float
    objective_gap_from_best: float
    aligned_hard_assignments: tuple[int, ...]
    agreement_with_best: float
    objective_weight: float


@dataclass(frozen=True)
class HMMRestartAudit:
    best_seed: int
    records: tuple[HMMRestartRecord, ...]
    objective_weighted_agreement: float
    effective_restart_count: float
    minimum_all_start_agreement: float
    diagnostic_weight_interpretation: str = "NUMERICAL_DIAGNOSTIC_NOT_POSTERIOR_PROBABILITY"


@dataclass(frozen=True)
class HMMGapSensitivityRecord:
    maximum_objective_gap: float
    included_restarts: int
    objective_weighted_agreement: float
    effective_restart_count: float
    minimum_agreement: float


def _logsumexp(values: FloatArray, axis: Optional[int] = None) -> FloatArray:
    maximum = np.max(values, axis=axis, keepdims=True)
    stable = maximum + np.log(np.sum(np.exp(values - maximum), axis=axis, keepdims=True))
    if axis is None:
        return np.asarray(stable.squeeze(), dtype=np.float64)
    return np.asarray(np.squeeze(stable, axis=axis), dtype=np.float64)


def _validate_matrix(values: FloatArray, n_states: int) -> None:
    if values.ndim != 2 or values.shape[0] < max(4, n_states * 2):
        raise HMMError("HMM input must be a two-dimensional matrix with enough rows.")
    if n_states < 1:
        raise HMMError("n_states must be positive.")
    if np.any(np.isinf(values)):
        raise HMMError("HMM input cannot contain infinite values.")
    if np.any(np.sum(np.isfinite(values), axis=0) < 2):
        raise HMMError("Every feature needs at least two observed training values.")


def emission_log_probabilities(values: FloatArray, parameters: HMMParameters) -> FloatArray:
    """Return log p(x_t | state), integrating out missing feature dimensions."""
    n_rows = values.shape[0]
    n_states = parameters.means.shape[0]
    result = np.zeros((n_rows, n_states), dtype=np.float64)
    observed = np.isfinite(values)
    for state in range(n_states):
        differences = values - parameters.means[state]
        terms = np.log(2.0 * np.pi * parameters.variances[state]) + (
            differences**2 / parameters.variances[state]
        )
        result[:, state] = -0.5 * np.sum(np.where(observed, terms, 0.0), axis=1)
    return result


def _forward(emission_log: FloatArray, parameters: HMMParameters) -> tuple[FloatArray, float]:
    n_rows, n_states = emission_log.shape
    log_initial = np.log(np.clip(parameters.initial, 1e-300, None))
    log_transition = np.log(np.clip(parameters.transition, 1e-300, None))
    alpha = np.empty((n_rows, n_states), dtype=np.float64)
    alpha[0] = log_initial + emission_log[0]
    for row in range(1, n_rows):
        alpha[row] = emission_log[row] + _logsumexp(
            alpha[row - 1][:, None] + log_transition, axis=0
        )
    log_likelihood = float(_logsumexp(alpha[-1]))
    filtered = np.exp(alpha - _logsumexp(alpha, axis=1)[:, None])
    return filtered, log_likelihood


def _forward_backward(
    emission_log: FloatArray, parameters: HMMParameters
) -> tuple[FloatArray, FloatArray, float]:
    n_rows, n_states = emission_log.shape
    log_initial = np.log(np.clip(parameters.initial, 1e-300, None))
    log_transition = np.log(np.clip(parameters.transition, 1e-300, None))
    alpha = np.empty((n_rows, n_states), dtype=np.float64)
    alpha[0] = log_initial + emission_log[0]
    for row in range(1, n_rows):
        alpha[row] = emission_log[row] + _logsumexp(
            alpha[row - 1][:, None] + log_transition, axis=0
        )
    log_likelihood = float(_logsumexp(alpha[-1]))

    beta = np.zeros((n_rows, n_states), dtype=np.float64)
    for row in range(n_rows - 2, -1, -1):
        beta[row] = _logsumexp(
            log_transition + emission_log[row + 1][None, :] + beta[row + 1][None, :],
            axis=1,
        )
    gamma = np.exp(alpha + beta - log_likelihood)
    gamma /= np.sum(gamma, axis=1, keepdims=True)

    xi_sum = np.zeros((n_states, n_states), dtype=np.float64)
    for row in range(n_rows - 1):
        log_xi = (
            alpha[row][:, None]
            + log_transition
            + emission_log[row + 1][None, :]
            + beta[row + 1][None, :]
            - log_likelihood
        )
        xi_sum += np.exp(log_xi)
    return gamma, xi_sum, log_likelihood


def _initial_parameters(
    values: FloatArray,
    n_states: int,
    variance_floor: float,
    transition_prior: float,
    seed: int,
) -> HMMParameters:
    generator = np.random.default_rng(seed)
    filled = np.where(np.isfinite(values), values, 0.0)
    _, _, right = np.linalg.svd(filled, full_matrices=False)
    factor = filled @ right[0]
    factor = factor + generator.normal(0.0, 0.05, size=factor.shape)
    boundaries = np.quantile(factor, np.linspace(0.0, 1.0, n_states + 1)[1:-1])
    assignments = np.digitize(factor, boundaries)
    n_features = values.shape[1]
    means = np.zeros((n_states, n_features), dtype=np.float64)
    variances = np.ones((n_states, n_features), dtype=np.float64)
    global_means = np.nanmean(values, axis=0)
    global_variances = np.maximum(np.nanvar(values, axis=0), variance_floor)
    for state in range(n_states):
        state_rows = values[assignments == state]
        if state_rows.shape[0] == 0:
            state_rows = values
        for feature in range(n_features):
            observed = state_rows[np.isfinite(state_rows[:, feature]), feature]
            if observed.size == 0:
                means[state, feature] = global_means[feature]
                variances[state, feature] = global_variances[feature]
            else:
                means[state, feature] = float(np.mean(observed))
                variances[state, feature] = max(float(np.var(observed)), variance_floor)
    transition = np.full((n_states, n_states), transition_prior, dtype=np.float64)
    for left, right_state in zip(assignments[:-1], assignments[1:]):
        transition[left, right_state] += 1.0
    transition /= np.sum(transition, axis=1, keepdims=True)
    initial = np.full(n_states, transition_prior, dtype=np.float64)
    initial[assignments[0]] += 1.0
    initial /= np.sum(initial)
    return HMMParameters(initial, transition, means, variances)


def _regularized_objective(
    log_likelihood: float, parameters: HMMParameters, pseudo_count: float
) -> float:
    """Log posterior induced by the transition and initial pseudo-counts."""
    log_initial = np.log(np.clip(parameters.initial, 1e-300, None))
    log_transition = np.log(np.clip(parameters.transition, 1e-300, None))
    return float(log_likelihood + pseudo_count * (np.sum(log_initial) + np.sum(log_transition)))


def fit_diagonal_gaussian_hmm(
    values: FloatArray,
    n_states: int = 2,
    max_iterations: int = 100,
    tolerance: float = 1e-6,
    variance_floor: float = 0.05,
    transition_prior: float = 0.5,
    seed: int = 0,
) -> HMMFit:
    """Fit by EM; missing dimensions make no contribution to their row likelihood."""
    _validate_matrix(values, n_states)
    if max_iterations < 1 or tolerance <= 0 or variance_floor <= 0 or transition_prior <= 0:
        raise HMMError("Invalid HMM optimization setting.")
    parameters = _initial_parameters(values, n_states, variance_floor, transition_prior, seed)
    previous_objective = -np.inf
    converged = False
    iterations = 0
    for iteration in range(1, max_iterations + 1):
        iterations = iteration
        emission_log = emission_log_probabilities(values, parameters)
        gamma, xi_sum, log_likelihood = _forward_backward(emission_log, parameters)
        objective = _regularized_objective(log_likelihood, parameters, transition_prior)
        initial = np.clip(gamma[0] + transition_prior, 1e-12, None)
        initial /= np.sum(initial)
        transition = xi_sum + transition_prior
        transition /= np.sum(transition, axis=1, keepdims=True)

        means = parameters.means.copy()
        variances = parameters.variances.copy()
        observed = np.isfinite(values)
        for state in range(n_states):
            for feature in range(values.shape[1]):
                weights = gamma[:, state] * observed[:, feature]
                denominator = float(np.sum(weights))
                if denominator <= 1e-10:
                    continue
                feature_values = np.where(observed[:, feature], values[:, feature], 0.0)
                mean = float(np.sum(weights * feature_values) / denominator)
                variance = float(np.sum(weights * (feature_values - mean) ** 2) / denominator)
                means[state, feature] = mean
                variances[state, feature] = max(variance, variance_floor)
        parameters = HMMParameters(initial, transition, means, variances)
        numerical_tolerance = 1e-8 * (1.0 + abs(previous_objective))
        if objective + numerical_tolerance < previous_objective:
            raise HMMError(
                "HMM regularized objective decreased during EM: "
                f"{previous_objective:.12g} -> {objective:.12g}."
            )
        if np.isfinite(previous_objective) and abs(objective - previous_objective) <= tolerance * (
            1.0 + abs(previous_objective)
        ):
            converged = True
            break
        previous_objective = objective
    emission_log = emission_log_probabilities(values, parameters)
    filtered, log_likelihood = _forward(emission_log, parameters)
    regularized_objective = _regularized_objective(log_likelihood, parameters, transition_prior)
    return HMMFit(
        parameters=parameters,
        log_likelihood=log_likelihood,
        regularized_objective=regularized_objective,
        iterations=iterations,
        converged=converged,
        seed=seed,
        filtered_probabilities=filtered,
    )


def fit_hmm_restarts(
    values: FloatArray,
    n_states: int,
    restarts: int,
    max_iterations: int,
    tolerance: float,
    variance_floor: float,
    transition_prior: float,
    seed: int,
) -> tuple[HMMFit, tuple[HMMFit, ...]]:
    if restarts < 1:
        raise HMMError("At least one restart is required.")
    fits = tuple(
        fit_diagonal_gaussian_hmm(
            values=values,
            n_states=n_states,
            max_iterations=max_iterations,
            tolerance=tolerance,
            variance_floor=variance_floor,
            transition_prior=transition_prior,
            seed=seed + restart * 1009,
        )
        for restart in range(restarts)
    )
    return max(fits, key=lambda fit: fit.regularized_objective), fits


def reorder_fit(fit: HMMFit, order: tuple[int, ...]) -> HMMFit:
    parameters = fit.parameters
    index = np.asarray(order)
    reordered = HMMParameters(
        initial=parameters.initial[index],
        transition=parameters.transition[np.ix_(index, index)],
        means=parameters.means[index],
        variances=parameters.variances[index],
    )
    return HMMFit(
        parameters=reordered,
        log_likelihood=fit.log_likelihood,
        regularized_objective=fit.regularized_objective,
        iterations=fit.iterations,
        converged=fit.converged,
        seed=fit.seed,
        filtered_probabilities=fit.filtered_probabilities[:, index],
    )


def alignment_order(reference_means: FloatArray, candidate_means: FloatArray) -> tuple[int, ...]:
    if reference_means.shape != candidate_means.shape:
        raise HMMError("State-mean shapes must match for label alignment.")
    n_states = reference_means.shape[0]
    candidates = tuple(permutations(range(n_states)))
    return min(
        candidates,
        key=lambda order: float(
            np.sum((reference_means - candidate_means[np.asarray(order)]) ** 2)
        ),
    )


def audit_hmm_restarts(fits: tuple[HMMFit, ...]) -> HMMRestartAudit:
    """Retain restart provenance and summarize aligned numerical consensus."""
    if not fits:
        raise HMMError("Restart provenance requires at least one HMM fit.")
    objectives = np.asarray([fit.regularized_objective for fit in fits], dtype=np.float64)
    if np.any(~np.isfinite(objectives)):
        raise HMMError("Restart objectives must be finite.")
    best_index = int(np.argmax(objectives))
    best = fits[best_index]
    expected_shape = best.filtered_probabilities.shape
    if (
        len(expected_shape) != 2
        or expected_shape[0] == 0
        or expected_shape[1] != best.parameters.means.shape[0]
    ):
        raise HMMError("Restart filtered probabilities have an invalid shape.")
    best_labels = np.argmax(best.filtered_probabilities, axis=1)
    gaps = float(objectives[best_index]) - objectives
    unnormalized = np.exp(-gaps)
    weights = unnormalized / np.sum(unnormalized)
    agreements = np.empty(len(fits), dtype=np.float64)
    aligned_assignments: list[tuple[int, ...]] = []
    for index, fit in enumerate(fits):
        if fit.filtered_probabilities.shape != expected_shape:
            raise HMMError("All restarts must share the same filtered-probability shape.")
        if np.any(~np.isfinite(fit.filtered_probabilities)):
            raise HMMError("Restart filtered probabilities must be finite.")
        if fit.parameters.means.shape != best.parameters.means.shape:
            raise HMMError("All restarts must share the same state-mean shape.")
        order = alignment_order(best.parameters.means, fit.parameters.means)
        aligned = reorder_fit(fit, order)
        labels = np.argmax(aligned.filtered_probabilities, axis=1)
        aligned_assignments.append(tuple(int(value) for value in labels))
        agreements[index] = float(np.mean(best_labels == labels))
    records = tuple(
        HMMRestartRecord(
            seed=fit.seed,
            converged=fit.converged,
            iterations=fit.iterations,
            log_likelihood=fit.log_likelihood,
            regularized_objective=fit.regularized_objective,
            objective_gap_from_best=float(gaps[index]),
            aligned_hard_assignments=aligned_assignments[index],
            agreement_with_best=float(agreements[index]),
            objective_weight=float(weights[index]),
        )
        for index, fit in enumerate(fits)
    )
    return HMMRestartAudit(
        best_seed=best.seed,
        records=records,
        objective_weighted_agreement=float(np.sum(weights * agreements)),
        effective_restart_count=float(1.0 / np.sum(weights**2)),
        minimum_all_start_agreement=float(np.min(agreements)),
    )


def hmm_restart_gap_sensitivity(
    audit: HMMRestartAudit, maximum_gaps: tuple[float, ...]
) -> tuple[HMMGapSensitivityRecord, ...]:
    """Summarize restart consensus over prospectively supplied objective-gap cutoffs."""
    if not maximum_gaps or any(not np.isfinite(gap) or gap < 0 for gap in maximum_gaps):
        raise HMMError("Objective-gap cutoffs must be finite and nonnegative.")
    if any(right <= left for left, right in zip(maximum_gaps, maximum_gaps[1:])):
        raise HMMError("Objective-gap cutoffs must be strictly increasing.")
    gaps = np.asarray([record.objective_gap_from_best for record in audit.records])
    agreements = np.asarray([record.agreement_with_best for record in audit.records])
    if gaps.size == 0 or np.any(~np.isfinite(gaps)) or np.any(gaps < 0):
        raise HMMError("Restart audit objective gaps are invalid.")
    output: list[HMMGapSensitivityRecord] = []
    for maximum_gap in maximum_gaps:
        included = gaps <= maximum_gap
        if not np.any(included):
            raise HMMError("Every gap cutoff must include the best restart.")
        unnormalized = np.exp(-gaps[included])
        weights = unnormalized / np.sum(unnormalized)
        output.append(
            HMMGapSensitivityRecord(
                maximum_objective_gap=maximum_gap,
                included_restarts=int(np.sum(included)),
                objective_weighted_agreement=float(np.sum(weights * agreements[included])),
                effective_restart_count=float(1.0 / np.sum(weights**2)),
                minimum_agreement=float(np.min(agreements[included])),
            )
        )
    return tuple(output)


def filter_next(
    parameters: HMMParameters,
    previous_filtered: FloatArray,
    observation: FloatArray,
) -> tuple[FloatArray, float]:
    if observation.ndim != 1 or observation.shape[0] != parameters.means.shape[1]:
        raise HMMError("Current observation has the wrong feature shape.")
    prior = previous_filtered @ parameters.transition
    emission = emission_log_probabilities(observation[None, :], parameters)[0]
    log_weights = np.log(np.clip(prior, 1e-300, None)) + emission
    log_predictive = float(_logsumexp(log_weights))
    posterior = np.exp(log_weights - log_predictive)
    return posterior, log_predictive


def diagonal_gaussian_log_score(train: FloatArray, observation: FloatArray) -> float:
    means = np.nanmean(train, axis=0)
    variances = np.maximum(np.nanvar(train, axis=0), 0.05)
    observed = np.isfinite(observation)
    if not np.any(observed):
        return 0.0
    terms = np.log(2.0 * np.pi * variances[observed]) + (
        (observation[observed] - means[observed]) ** 2 / variances[observed]
    )
    return float(-0.5 * np.sum(terms))
