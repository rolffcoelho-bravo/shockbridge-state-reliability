"""Rotation-aware factor-subspace components for the prospective Run 008 redesign."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from shockbridge_state_risk.state.hmm import FloatArray


class SubspaceError(ValueError):
    """Raised when a factor-subspace estimate violates its numerical contract."""


@dataclass(frozen=True)
class AnchoredSubspaceEstimate:
    basis: FloatArray
    anchored_basis: FloatArray
    projector: FloatArray
    feature_means: FloatArray
    feature_scales: FloatArray
    singular_values: FloatArray
    explained_variance_ratio: FloatArray
    anchor_capture: FloatArray
    anchor_alignment: FloatArray


@dataclass(frozen=True)
class SubspaceComparison:
    principal_cosines: FloatArray
    root_mean_square_projector_distance: float
    anchored_loading_cosines: FloatArray


@dataclass(frozen=True)
class FixedLoadingFactorEstimate:
    filtered_factor_mean: float
    filtered_factor_variance: float
    standardized_factor_mean: float
    standardized_factor_variance: float
    historical_standardized_factors: FloatArray
    loading: FloatArray
    feature_means: FloatArray
    feature_scales: FloatArray
    ar_coefficient: float
    factor_innovation_variance: float
    idiosyncratic_variances: FloatArray
    feature_log_predictive_score: float


@dataclass(frozen=True)
class AnchoredTwoFactorEstimate:
    filtered_factor_mean: FloatArray
    filtered_factor_covariance: FloatArray
    standardized_factor_mean: FloatArray
    standardized_factor_variances: FloatArray
    historical_standardized_factors: FloatArray
    loadings: FloatArray
    feature_means: FloatArray
    feature_scales: FloatArray
    transition: FloatArray
    innovation_covariance: FloatArray
    idiosyncratic_variances: FloatArray
    feature_log_predictive_score: float
    anchor_capture: FloatArray
    anchor_alignment: FloatArray
    explained_variance_ratio: FloatArray


def economic_anchor_matrix(
    feature_count: int = 4,
    inflation_index: int = 0,
    industrial_production_index: int = 1,
    unemployment_index: int = 2,
    policy_rate_index: int = 3,
) -> FloatArray:
    """Return orthonormal slack and ex-post-real-rate orientation targets."""
    indices = (
        inflation_index,
        industrial_production_index,
        unemployment_index,
        policy_rate_index,
    )
    if (
        feature_count < 4
        or len(set(indices)) != 4
        or any(index < 0 or index >= feature_count for index in indices)
    ):
        raise SubspaceError("Economic anchors require four distinct valid feature indices.")
    anchors = np.zeros((feature_count, 2), dtype=np.float64)
    anchors[industrial_production_index, 0] = -1.0 / np.sqrt(2.0)
    anchors[unemployment_index, 0] = 1.0 / np.sqrt(2.0)
    anchors[inflation_index, 1] = -1.0 / np.sqrt(2.0)
    anchors[policy_rate_index, 1] = 1.0 / np.sqrt(2.0)
    return anchors


def _validate_orthonormal(matrix: FloatArray, context: str) -> None:
    if matrix.ndim != 2 or np.any(~np.isfinite(matrix)):
        raise SubspaceError(f"{context} must be a finite matrix.")
    identity = np.eye(matrix.shape[1], dtype=np.float64)
    if matrix.shape[0] < matrix.shape[1] or not np.allclose(
        matrix.T @ matrix, identity, rtol=0.0, atol=1e-10
    ):
        raise SubspaceError(f"{context} columns must be orthonormal.")


def align_basis_to_anchors(
    basis: FloatArray, anchors: FloatArray
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Resolve within-subspace rotation through prespecified economic targets."""
    candidate = np.asarray(basis, dtype=np.float64)
    targets = np.asarray(anchors, dtype=np.float64)
    _validate_orthonormal(candidate, "Factor basis")
    _validate_orthonormal(targets, "Economic anchors")
    if candidate.shape != targets.shape:
        raise SubspaceError("Factor basis and economic anchors must have equal shape.")
    left, _, right_transpose = np.linalg.svd(candidate.T @ targets)
    aligned = candidate @ (left @ right_transpose)
    for column in range(aligned.shape[1]):
        if float(aligned[:, column] @ targets[:, column]) < 0.0:
            aligned[:, column] *= -1.0
    capture = np.linalg.norm(candidate.T @ targets, axis=0)
    alignment = np.diag(aligned.T @ targets)
    return aligned, capture, alignment


def estimate_anchored_subspace(
    train: FloatArray, anchors: FloatArray, n_factors: int = 2
) -> AnchoredSubspaceEstimate:
    """Estimate a PCA subspace and identify its basis without outcome information."""
    historical = np.asarray(train, dtype=np.float64)
    targets = np.asarray(anchors, dtype=np.float64)
    if historical.ndim != 2 or historical.shape[0] < 8:
        raise SubspaceError("Subspace estimation requires a two-dimensional history.")
    if np.any(np.isinf(historical)):
        raise SubspaceError("Subspace history cannot contain infinities.")
    if n_factors < 1 or n_factors >= historical.shape[1]:
        raise SubspaceError("The factor-subspace dimension is invalid.")
    if targets.shape != (historical.shape[1], n_factors):
        raise SubspaceError("Economic-anchor dimensions do not match the factor subspace.")
    _validate_orthonormal(targets, "Economic anchors")
    if np.any(np.sum(np.isfinite(historical), axis=0) < 2):
        raise SubspaceError("Every feature requires two historical observations.")
    means = np.nanmean(historical, axis=0)
    scales = np.nanstd(historical, axis=0)
    scales = np.where(scales < 1e-8, 1.0, scales)
    standardized = (historical - means) / scales
    filled = np.where(np.isfinite(standardized), standardized, 0.0)
    _, singular_values, right = np.linalg.svd(filled, full_matrices=False)
    total_variation = float(np.sum(singular_values**2))
    if total_variation <= 1e-12 or singular_values[n_factors - 1] <= 1e-10:
        raise SubspaceError("The requested factor subspace is not identified by the history.")
    basis = right[:n_factors].T
    anchored, capture, alignment = align_basis_to_anchors(basis, targets)
    squared = singular_values**2
    explained = squared[:n_factors] / total_variation
    return AnchoredSubspaceEstimate(
        basis=basis,
        anchored_basis=anchored,
        projector=basis @ basis.T,
        feature_means=means,
        feature_scales=scales,
        singular_values=singular_values[:n_factors],
        explained_variance_ratio=explained,
        anchor_capture=capture,
        anchor_alignment=alignment,
    )


def compare_subspaces(
    left: AnchoredSubspaceEstimate, right: AnchoredSubspaceEstimate
) -> SubspaceComparison:
    """Compare factor spaces separately from their prespecified economic rotation."""
    if left.basis.shape != right.basis.shape:
        raise SubspaceError("Compared factor subspaces must have equal shape.")
    _validate_orthonormal(left.basis, "Left factor basis")
    _validate_orthonormal(right.basis, "Right factor basis")
    _validate_orthonormal(left.anchored_basis, "Left anchored basis")
    _validate_orthonormal(right.anchored_basis, "Right anchored basis")
    if (
        left.anchored_basis.shape != left.basis.shape
        or right.anchored_basis.shape != right.basis.shape
    ):
        raise SubspaceError("Anchored bases must match their factor-subspace shape.")
    principal_cosines = np.clip(
        np.linalg.svd(left.basis.T @ right.basis, compute_uv=False), 0.0, 1.0
    )
    dimension = left.basis.shape[1]
    left_projector = left.basis @ left.basis.T
    right_projector = right.basis @ right.basis.T
    projector_distance = float(
        np.linalg.norm(left_projector - right_projector, ord="fro") / np.sqrt(2.0 * dimension)
    )
    anchored_cosines = np.clip(np.diag(left.anchored_basis.T @ right.anchored_basis), -1.0, 1.0)
    return SubspaceComparison(
        principal_cosines=principal_cosines,
        root_mean_square_projector_distance=projector_distance,
        anchored_loading_cosines=anchored_cosines,
    )


def _regularize_covariance(covariance: FloatArray, variance_floor: float) -> FloatArray:
    symmetric = 0.5 * (covariance + covariance.T)
    eigenvalues, eigenvectors = np.linalg.eigh(symmetric)
    regularized = (eigenvectors * np.maximum(eigenvalues, variance_floor)) @ eigenvectors.T
    return np.asarray(regularized, dtype=np.float64)


def _gaussian_log_score(observation: FloatArray, mean: FloatArray, covariance: FloatArray) -> float:
    sign, log_determinant = np.linalg.slogdet(covariance)
    if sign <= 0 or not np.isfinite(log_determinant):
        raise SubspaceError("Predictive covariance must be positive definite.")
    difference = observation - mean
    quadratic = float(difference @ np.linalg.solve(covariance, difference))
    return float(-0.5 * (observation.size * np.log(2.0 * np.pi) + log_determinant + quadratic))


def _standardize_inputs(
    train: FloatArray, current: FloatArray
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    historical = np.asarray(train, dtype=np.float64)
    observation = np.asarray(current, dtype=np.float64)
    if historical.ndim != 2 or historical.shape[0] < 8:
        raise SubspaceError("Factor filtering requires a two-dimensional history.")
    if observation.shape != (historical.shape[1],):
        raise SubspaceError("Current factor observation has an invalid shape.")
    if np.any(np.isinf(historical)) or np.any(np.isinf(observation)):
        raise SubspaceError("Factor-filtering inputs cannot contain infinities.")
    if np.any(np.sum(np.isfinite(historical), axis=0) < 2):
        raise SubspaceError("Every feature requires two historical observations.")
    if not np.any(np.isfinite(observation)):
        raise SubspaceError("Current factor observation cannot be entirely missing.")
    means = np.nanmean(historical, axis=0)
    scales = np.nanstd(historical, axis=0)
    scales = np.where(scales < 1e-8, 1.0, scales)
    standardized_train = (historical - means) / scales
    standardized_current = (observation - means) / scales
    return standardized_train, standardized_current, means, scales


def estimate_fixed_loading_factor(
    train: FloatArray,
    current: FloatArray,
    loading: FloatArray,
    variance_floor: float = 0.05,
) -> FixedLoadingFactorEstimate:
    """Filter a scalar factor whose loading was frozen in an earlier development block."""
    historical, observation, means, scales = _standardize_inputs(train, current)
    fixed = np.asarray(loading, dtype=np.float64)
    if (
        fixed.shape != (historical.shape[1],)
        or np.any(~np.isfinite(fixed))
        or not np.isclose(np.linalg.norm(fixed), 1.0, rtol=0.0, atol=1e-10)
        or not np.isfinite(variance_floor)
        or variance_floor <= 0
    ):
        raise SubspaceError("The fixed scalar loading or variance floor is invalid.")
    filled = np.where(np.isfinite(historical), historical, 0.0)
    factors = filled @ fixed
    factor_location = float(np.mean(factors))
    factor_scale = float(np.std(factors))
    if factor_scale < 1e-8:
        raise SubspaceError("The fixed-loading factor has no usable variation.")
    denominator = float(np.sum(factors[:-1] ** 2))
    coefficient = (
        float(np.sum(factors[1:] * factors[:-1]) / denominator) if denominator > 1e-10 else 0.0
    )
    coefficient = float(np.clip(coefficient, -0.98, 0.98))
    innovation_variance = max(
        float(np.var(factors[1:] - coefficient * factors[:-1])), variance_floor
    )
    residuals = filled - factors[:, None] * fixed[None, :]
    idiosyncratic = np.maximum(np.var(residuals, axis=0), variance_floor)
    prior_mean = coefficient * float(factors[-1])
    observed = np.isfinite(observation)
    predictive_covariance = np.diag(idiosyncratic[observed]) + innovation_variance * np.outer(
        fixed[observed], fixed[observed]
    )
    score = _gaussian_log_score(
        observation[observed], fixed[observed] * prior_mean, predictive_covariance
    )
    precision = 1.0 / innovation_variance + float(
        np.sum(fixed[observed] ** 2 / idiosyncratic[observed])
    )
    information = prior_mean / innovation_variance + float(
        np.sum(fixed[observed] * observation[observed] / idiosyncratic[observed])
    )
    filtered_variance = 1.0 / precision
    filtered_mean = filtered_variance * information
    return FixedLoadingFactorEstimate(
        filtered_factor_mean=float(filtered_mean),
        filtered_factor_variance=float(filtered_variance),
        standardized_factor_mean=float((filtered_mean - factor_location) / factor_scale),
        standardized_factor_variance=float(filtered_variance / factor_scale**2),
        historical_standardized_factors=(factors - factor_location) / factor_scale,
        loading=fixed.copy(),
        feature_means=means,
        feature_scales=scales,
        ar_coefficient=coefficient,
        factor_innovation_variance=innovation_variance,
        idiosyncratic_variances=idiosyncratic,
        feature_log_predictive_score=score,
    )


def estimate_anchored_two_factor(
    train: FloatArray,
    current: FloatArray,
    anchors: FloatArray,
    variance_floor: float = 0.05,
    transition_ridge: float = 1e-6,
    maximum_transition_radius: float = 0.98,
) -> AnchoredTwoFactorEstimate:
    """Filter a two-factor VAR(1) after rotation-invariant economic alignment."""
    historical, observation, means, scales = _standardize_inputs(train, current)
    if (
        not np.isfinite(variance_floor)
        or variance_floor <= 0
        or not np.isfinite(transition_ridge)
        or transition_ridge <= 0
        or not np.isfinite(maximum_transition_radius)
        or not 0 < maximum_transition_radius < 1
    ):
        raise SubspaceError("Two-factor numerical controls are invalid.")
    subspace = estimate_anchored_subspace(train, anchors, n_factors=2)
    filled = np.where(np.isfinite(historical), historical, 0.0)
    factors = filled @ subspace.anchored_basis
    predictors = factors[:-1]
    responses = factors[1:]
    coefficient = np.linalg.solve(
        predictors.T @ predictors + transition_ridge * np.eye(2),
        predictors.T @ responses,
    )
    transition = coefficient.T
    radius = float(np.max(np.abs(np.linalg.eigvals(transition))))
    if radius > maximum_transition_radius:
        transition *= maximum_transition_radius / radius
    innovations = responses - predictors @ transition.T
    innovation_covariance = _regularize_covariance(
        np.cov(innovations, rowvar=False, bias=True), variance_floor
    )
    residuals = filled - factors @ subspace.anchored_basis.T
    idiosyncratic = np.maximum(np.var(residuals, axis=0), variance_floor)
    prior_mean = transition @ factors[-1]
    prior_covariance = innovation_covariance
    observed = np.isfinite(observation)
    observed_loadings = subspace.anchored_basis[observed]
    predictive_covariance = observed_loadings @ prior_covariance @ observed_loadings.T + np.diag(
        idiosyncratic[observed]
    )
    score = _gaussian_log_score(
        observation[observed], observed_loadings @ prior_mean, predictive_covariance
    )
    prior_precision = np.linalg.inv(prior_covariance)
    residual_precision = np.diag(1.0 / idiosyncratic[observed])
    posterior_precision = (
        prior_precision + observed_loadings.T @ residual_precision @ observed_loadings
    )
    posterior_covariance = np.linalg.inv(posterior_precision)
    posterior_mean = posterior_covariance @ (
        prior_precision @ prior_mean
        + observed_loadings.T @ residual_precision @ observation[observed]
    )
    factor_locations = np.mean(factors, axis=0)
    factor_scales = np.std(factors, axis=0)
    if np.any(factor_scales < 1e-8):
        raise SubspaceError("An anchored factor has no usable variation.")
    return AnchoredTwoFactorEstimate(
        filtered_factor_mean=posterior_mean,
        filtered_factor_covariance=posterior_covariance,
        standardized_factor_mean=(posterior_mean - factor_locations) / factor_scales,
        standardized_factor_variances=np.diag(posterior_covariance) / factor_scales**2,
        historical_standardized_factors=(factors - factor_locations) / factor_scales,
        loadings=subspace.anchored_basis,
        feature_means=means,
        feature_scales=scales,
        transition=transition,
        innovation_covariance=innovation_covariance,
        idiosyncratic_variances=idiosyncratic,
        feature_log_predictive_score=score,
        anchor_capture=subspace.anchor_capture,
        anchor_alignment=subspace.anchor_alignment,
        explained_variance_ratio=subspace.explained_variance_ratio,
    )
