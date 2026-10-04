"""Outcome-blind orchestration for the frozen Run 008 subspace redesign."""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from shockbridge_state_risk.data.download import sha256_file
from shockbridge_state_risk.state.benchmarks import expanding_standardize
from shockbridge_state_risk.state.comparison import load_monthly_matrix
from shockbridge_state_risk.state.hmm import FloatArray, diagonal_gaussian_log_score
from shockbridge_state_risk.state.subspace import (
    AnchoredSubspaceEstimate,
    AnchoredTwoFactorEstimate,
    FixedLoadingFactorEstimate,
    compare_subspaces,
    economic_anchor_matrix,
    estimate_anchored_subspace,
    estimate_anchored_two_factor,
    estimate_fixed_loading_factor,
)


class Run008Error(ValueError):
    """Raised when the Run 008 contract or output integrity fails."""


@dataclass(frozen=True)
class SubspaceThresholds:
    minimum_second_principal_cosine: float
    minimum_tenth_percentile_second_principal_cosine: float
    maximum_median_projector_distance: float
    maximum_ninetieth_percentile_projector_distance: float
    minimum_tenth_percentile_anchor_capture_each_target: float
    weak_anchor_capture_cutoff: float
    maximum_weak_anchor_capture_rate_each_target: float
    minimum_median_anchored_loading_cosine_each_factor: float
    minimum_tenth_percentile_anchored_loading_cosine_each_factor: float


@dataclass(frozen=True)
class FactorThresholds:
    minimum_pearson_correlation: float
    minimum_spearman_correlation: float
    maximum_sign_disagreement_rate: float
    maximum_standardized_mean_absolute_difference: float


@dataclass(frozen=True)
class Run008Config:
    config_sha256: str
    experiment_id: str
    evidence_status: str
    approved_design_path: Path
    approved_design_sha256: str
    panel_path: Path
    panel_sha256: str
    features: tuple[str, ...]
    history_windows: tuple[str, ...]
    minimum_training_months: int
    rolling_months: int
    development_months: int
    development_start: str
    development_end: str
    evaluation_start: str
    evaluation_end: str
    factor_dimension: int
    variance_floor: float
    transition_ridge: float
    maximum_transition_spectral_radius: float
    subspace_thresholds: SubspaceThresholds
    fixed_scalar_thresholds: FactorThresholds
    require_positive_mean_log_score_gain_each_history: bool
    two_factor_thresholds: FactorThresholds
    outcomes_accessed: bool
    state_model_execution_authorized: bool
    transmission_outcome_execution_authorized: bool


@dataclass(frozen=True)
class SubspaceEstimateRow:
    month_id: str
    cutoff_timestamp: str
    history_window: str
    training_months: int
    explained_variance_ratio_1: float
    explained_variance_ratio_2: float
    anchor_capture_slack: float
    anchor_capture_policy_minus_inflation: float
    anchor_alignment_slack: float
    anchor_alignment_policy_minus_inflation: float
    projector_json: str
    anchored_basis_json: str
    feature_means_json: str
    feature_scales_json: str


@dataclass(frozen=True)
class FixedFactorRow:
    month_id: str
    cutoff_timestamp: str
    history_window: str
    training_months: int
    filtered_factor_mean: float
    filtered_factor_variance: float
    standardized_factor_mean: float
    standardized_factor_variance: float
    feature_log_predictive_score: float
    gaussian_log_predictive_score: float
    log_score_gain: float
    ar_coefficient: float
    factor_innovation_variance: float
    loading_json: str
    feature_means_json: str
    feature_scales_json: str
    idiosyncratic_variances_json: str


@dataclass(frozen=True)
class TwoFactorRow:
    month_id: str
    cutoff_timestamp: str
    history_window: str
    training_months: int
    standardized_factor_1_mean: float
    standardized_factor_2_mean: float
    standardized_factor_1_variance: float
    standardized_factor_2_variance: float
    standardized_factor_covariance: float
    feature_log_predictive_score: float
    gaussian_log_predictive_score: float
    log_score_gain: float
    anchor_capture_slack: float
    anchor_capture_policy_minus_inflation: float
    loadings_json: str
    transition_json: str
    innovation_covariance_json: str
    filtered_covariance_json: str
    feature_means_json: str
    feature_scales_json: str
    idiosyncratic_variances_json: str


@dataclass(frozen=True)
class PairedFactorMetrics:
    pearson_correlation: float
    spearman_correlation: float
    sign_disagreement_rate: float
    standardized_mean_absolute_difference: float


@dataclass(frozen=True)
class Run008Result:
    subspace_rows: tuple[SubspaceEstimateRow, ...]
    fixed_factor_rows: tuple[FixedFactorRow, ...]
    two_factor_rows: tuple[TwoFactorRow, ...]
    audit: Mapping[str, Any]


def _mapping(value: object, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise Run008Error(f"{context} must be a mapping.")
    return value


def _sequence(value: object, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise Run008Error(f"{context} must be a list.")
    return value


def _boolean(value: object, context: str) -> bool:
    if not isinstance(value, bool):
        raise Run008Error(f"{context} must be a boolean.")
    return value


def _exact_fields(payload: Mapping[str, Any], expected: set[str], context: str) -> None:
    if set(payload) != expected:
        missing = sorted(expected - payload.keys())
        unexpected = sorted(payload.keys() - expected)
        raise Run008Error(
            f"{context} fields differ from the frozen contract: {missing=}, {unexpected=}."
        )


def _factor_thresholds(payload: Mapping[str, Any], context: str) -> FactorThresholds:
    fields = set(FactorThresholds.__dataclass_fields__)
    _exact_fields(payload, fields, context)
    return FactorThresholds(**{field: float(payload[field]) for field in fields})


def _validate_execution_config(config: Run008Config) -> None:
    if (
        config.outcomes_accessed
        or not config.state_model_execution_authorized
        or config.transmission_outcome_execution_authorized
    ):
        raise Run008Error(
            "Run 008 execution must remain authorized, state only, and outcome blind."
        )
    if config.evidence_status != "REAL_DATA_OUTCOME_BLIND":
        return
    expected_features = (
        "hicp_yoy",
        "industrial_production_yoy",
        "unemployment_rate",
        "deposit_facility_rate",
    )
    expected_subspace = SubspaceThresholds(0.75, 0.90, 0.20, 0.35, 0.50, 0.35, 0.10, 0.90, 0.75)
    expected_fixed = FactorThresholds(0.80, 0.80, 0.10, 0.35)
    expected_two = FactorThresholds(0.75, 0.75, 0.15, 0.50)
    exact_contract = (
        config.experiment_id == "state-model-run008-v1",
        config.features == expected_features,
        config.history_windows == ("expanding", "rolling_120"),
        config.minimum_training_months == 60,
        config.rolling_months == 120,
        config.development_months == 120,
        config.development_start == "month-2002-01",
        config.development_end == "month-2011-12",
        config.evaluation_start == "month-2012-01",
        config.evaluation_end == "month-2025-10",
        config.factor_dimension == 2,
        config.variance_floor == 0.05,
        config.transition_ridge == 0.000001,
        config.maximum_transition_spectral_radius == 0.98,
        config.subspace_thresholds == expected_subspace,
        config.fixed_scalar_thresholds == expected_fixed,
        config.require_positive_mean_log_score_gain_each_history,
        config.two_factor_thresholds == expected_two,
    )
    if not all(exact_contract):
        raise Run008Error("Run 008 settings differ from the approved frozen contract.")


def load_run008_config(path: Path) -> Run008Config:
    """Load and fail closed on any departure from the approved Run 008 contract."""
    payload = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "Run 008 config")
    top_fields = {
        "schema_version",
        "experiment_id",
        "evidence_status",
        "approved_design_path",
        "approved_design_sha256",
        "panel_path",
        "panel_sha256",
        "features",
        "history_windows",
        "minimum_training_months",
        "rolling_months",
        "development_months",
        "development_start",
        "development_end",
        "evaluation_start",
        "evaluation_end",
        "factor_dimension",
        "variance_floor",
        "transition_ridge",
        "maximum_transition_spectral_radius",
        "subspace_gates",
        "fixed_scalar_gates",
        "two_factor_diagnostic_gates",
        "outcomes_accessed",
        "state_model_execution_authorized",
        "transmission_outcome_execution_authorized",
    }
    _exact_fields(payload, top_fields, "Run 008 config")
    subspace_payload = _mapping(payload["subspace_gates"], "subspace_gates")
    subspace_fields = set(SubspaceThresholds.__dataclass_fields__)
    _exact_fields(subspace_payload, subspace_fields, "subspace_gates")
    fixed_payload = _mapping(payload["fixed_scalar_gates"], "fixed_scalar_gates")
    fixed_fields = set(FactorThresholds.__dataclass_fields__) | {
        "require_positive_mean_log_score_gain_each_history"
    }
    _exact_fields(fixed_payload, fixed_fields, "fixed_scalar_gates")
    two_factor_payload = _mapping(
        payload["two_factor_diagnostic_gates"], "two_factor_diagnostic_gates"
    )

    approved_design_path = Path(str(payload["approved_design_path"]))
    panel_path = Path(str(payload["panel_path"]))
    if not approved_design_path.is_file() or sha256_file(approved_design_path) != str(
        payload["approved_design_sha256"]
    ):
        raise Run008Error("The approved Run 008 design is missing or has a hash mismatch.")
    if not panel_path.is_file() or sha256_file(panel_path) != str(payload["panel_sha256"]):
        raise Run008Error("The Run 008 panel is missing or has a hash mismatch.")
    approved = _mapping(
        yaml.safe_load(approved_design_path.read_text(encoding="utf-8")), "approved Run 008 design"
    )
    if (
        approved.get("status") != "APPROVED_AND_FROZEN_FOR_STATE_ONLY_EXECUTION"
        or approved.get("outcomes_accessed") is not False
        or approved.get("state_model_execution_authorized") is not True
        or approved.get("transmission_outcome_execution_authorized") is not False
    ):
        raise Run008Error("The referenced Run 008 design is not authorized and outcome blind.")

    try:
        fixed_threshold_values = {
            field: float(fixed_payload[field]) for field in FactorThresholds.__dataclass_fields__
        }
        config = Run008Config(
            config_sha256=sha256_file(path),
            experiment_id=str(payload["experiment_id"]),
            evidence_status=str(payload["evidence_status"]),
            approved_design_path=approved_design_path,
            approved_design_sha256=str(payload["approved_design_sha256"]),
            panel_path=panel_path,
            panel_sha256=str(payload["panel_sha256"]),
            features=tuple(str(value) for value in _sequence(payload["features"], "features")),
            history_windows=tuple(
                str(value) for value in _sequence(payload["history_windows"], "history_windows")
            ),
            minimum_training_months=int(payload["minimum_training_months"]),
            rolling_months=int(payload["rolling_months"]),
            development_months=int(payload["development_months"]),
            development_start=str(payload["development_start"]),
            development_end=str(payload["development_end"]),
            evaluation_start=str(payload["evaluation_start"]),
            evaluation_end=str(payload["evaluation_end"]),
            factor_dimension=int(payload["factor_dimension"]),
            variance_floor=float(payload["variance_floor"]),
            transition_ridge=float(payload["transition_ridge"]),
            maximum_transition_spectral_radius=float(payload["maximum_transition_spectral_radius"]),
            subspace_thresholds=SubspaceThresholds(
                **{field: float(subspace_payload[field]) for field in subspace_fields}
            ),
            fixed_scalar_thresholds=FactorThresholds(**fixed_threshold_values),
            require_positive_mean_log_score_gain_each_history=_boolean(
                fixed_payload["require_positive_mean_log_score_gain_each_history"],
                "require_positive_mean_log_score_gain_each_history",
            ),
            two_factor_thresholds=_factor_thresholds(
                two_factor_payload, "two_factor_diagnostic_gates"
            ),
            outcomes_accessed=_boolean(payload["outcomes_accessed"], "outcomes_accessed"),
            state_model_execution_authorized=_boolean(
                payload["state_model_execution_authorized"],
                "state_model_execution_authorized",
            ),
            transmission_outcome_execution_authorized=_boolean(
                payload["transmission_outcome_execution_authorized"],
                "transmission_outcome_execution_authorized",
            ),
        )
    except (TypeError, ValueError) as error:
        if isinstance(error, Run008Error):
            raise
        raise Run008Error(f"Run 008 config contains an invalid value: {error}") from error

    if payload["schema_version"] != 1:
        raise Run008Error("Run 008 schema version differs from the approved frozen contract.")
    _validate_execution_config(config)
    numerical_values = (
        config.variance_floor,
        config.transition_ridge,
        config.maximum_transition_spectral_radius,
        *config.subspace_thresholds.__dict__.values(),
        *config.fixed_scalar_thresholds.__dict__.values(),
        *config.two_factor_thresholds.__dict__.values(),
    )
    if any(not np.isfinite(value) for value in numerical_values):
        raise Run008Error("Run 008 numerical settings must be finite.")
    return config


def _json_array(values: FloatArray) -> str:
    array = np.asarray(values, dtype=np.float64)
    if np.any(~np.isfinite(array)):
        raise Run008Error("Run 008 cannot serialize a non-finite array.")
    canonical = np.asarray([_canonical_float(value) for value in array.ravel()]).reshape(
        array.shape
    )
    return json.dumps(canonical.tolist(), separators=(",", ":"))


def _canonical_float(value: float) -> float:
    scalar = float(value)
    if not np.isfinite(scalar):
        raise Run008Error("Run 008 cannot serialize a non-finite value.")
    if abs(scalar) < 1e-12:
        return 0.0
    return float(f"{scalar:.12g}")


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
        raise Run008Error("Run 008 factor correlations require variation in both histories.")
    return float(np.sum(left_centered * right_centered) / denominator)


def _paired_factor_metrics(left: FloatArray, right: FloatArray) -> PairedFactorMetrics:
    expanding = np.asarray(left, dtype=np.float64)
    rolling = np.asarray(right, dtype=np.float64)
    if expanding.ndim != 1 or rolling.shape != expanding.shape or expanding.size < 3:
        raise Run008Error("Run 008 factor metrics require paired one-dimensional histories.")
    if np.any(~np.isfinite(expanding)) or np.any(~np.isfinite(rolling)):
        raise Run008Error("Run 008 factor metrics cannot contain non-finite values.")
    pooled_scale = float(np.sqrt((np.var(expanding) + np.var(rolling)) / 2.0))
    if pooled_scale <= 1e-14:
        raise Run008Error("Run 008 factor differences require pooled variation.")
    return PairedFactorMetrics(
        pearson_correlation=_correlation(expanding, rolling),
        spearman_correlation=_correlation(_average_ranks(expanding), _average_ranks(rolling)),
        sign_disagreement_rate=float(np.mean(np.sign(expanding) != np.sign(rolling))),
        standardized_mean_absolute_difference=float(
            np.mean(np.abs(expanding - rolling)) / pooled_scale
        ),
    )


def _factor_gates(
    metrics: PairedFactorMetrics, thresholds: FactorThresholds
) -> tuple[tuple[str, bool], ...]:
    return (
        (
            "pearson_correlation",
            metrics.pearson_correlation >= thresholds.minimum_pearson_correlation,
        ),
        (
            "spearman_correlation",
            metrics.spearman_correlation >= thresholds.minimum_spearman_correlation,
        ),
        (
            "sign_disagreement_rate",
            metrics.sign_disagreement_rate <= thresholds.maximum_sign_disagreement_rate,
        ),
        (
            "standardized_mean_absolute_difference",
            metrics.standardized_mean_absolute_difference
            <= thresholds.maximum_standardized_mean_absolute_difference,
        ),
    )


def _factor_metrics_payload(metrics: PairedFactorMetrics) -> dict[str, float]:
    return {key: _canonical_float(value) for key, value in asdict(metrics).items()}


def _subspace_row(
    month_id: str,
    cutoff: str,
    history_window: str,
    training_months: int,
    estimate: AnchoredSubspaceEstimate,
) -> SubspaceEstimateRow:
    return SubspaceEstimateRow(
        month_id=month_id,
        cutoff_timestamp=cutoff,
        history_window=history_window,
        training_months=training_months,
        explained_variance_ratio_1=_canonical_float(estimate.explained_variance_ratio[0]),
        explained_variance_ratio_2=_canonical_float(estimate.explained_variance_ratio[1]),
        anchor_capture_slack=_canonical_float(estimate.anchor_capture[0]),
        anchor_capture_policy_minus_inflation=_canonical_float(estimate.anchor_capture[1]),
        anchor_alignment_slack=_canonical_float(estimate.anchor_alignment[0]),
        anchor_alignment_policy_minus_inflation=_canonical_float(estimate.anchor_alignment[1]),
        projector_json=_json_array(estimate.projector),
        anchored_basis_json=_json_array(estimate.anchored_basis),
        feature_means_json=_json_array(estimate.feature_means),
        feature_scales_json=_json_array(estimate.feature_scales),
    )


def _fixed_row(
    month_id: str,
    cutoff: str,
    history_window: str,
    training_months: int,
    estimate: FixedLoadingFactorEstimate,
    gaussian_score: float,
) -> FixedFactorRow:
    return FixedFactorRow(
        month_id=month_id,
        cutoff_timestamp=cutoff,
        history_window=history_window,
        training_months=training_months,
        filtered_factor_mean=_canonical_float(estimate.filtered_factor_mean),
        filtered_factor_variance=_canonical_float(estimate.filtered_factor_variance),
        standardized_factor_mean=_canonical_float(estimate.standardized_factor_mean),
        standardized_factor_variance=_canonical_float(estimate.standardized_factor_variance),
        feature_log_predictive_score=_canonical_float(estimate.feature_log_predictive_score),
        gaussian_log_predictive_score=_canonical_float(gaussian_score),
        log_score_gain=_canonical_float(estimate.feature_log_predictive_score - gaussian_score),
        ar_coefficient=_canonical_float(estimate.ar_coefficient),
        factor_innovation_variance=_canonical_float(estimate.factor_innovation_variance),
        loading_json=_json_array(estimate.loading),
        feature_means_json=_json_array(estimate.feature_means),
        feature_scales_json=_json_array(estimate.feature_scales),
        idiosyncratic_variances_json=_json_array(estimate.idiosyncratic_variances),
    )


def _two_factor_row(
    month_id: str,
    cutoff: str,
    history_window: str,
    training_months: int,
    estimate: AnchoredTwoFactorEstimate,
    gaussian_score: float,
) -> TwoFactorRow:
    factor_scales = np.sqrt(
        estimate.standardized_factor_variances / np.diag(estimate.filtered_factor_covariance)
    )
    standardized_covariance = float(
        estimate.filtered_factor_covariance[0, 1] * factor_scales[0] * factor_scales[1]
    )
    return TwoFactorRow(
        month_id=month_id,
        cutoff_timestamp=cutoff,
        history_window=history_window,
        training_months=training_months,
        standardized_factor_1_mean=_canonical_float(estimate.standardized_factor_mean[0]),
        standardized_factor_2_mean=_canonical_float(estimate.standardized_factor_mean[1]),
        standardized_factor_1_variance=_canonical_float(estimate.standardized_factor_variances[0]),
        standardized_factor_2_variance=_canonical_float(estimate.standardized_factor_variances[1]),
        standardized_factor_covariance=_canonical_float(standardized_covariance),
        feature_log_predictive_score=_canonical_float(estimate.feature_log_predictive_score),
        gaussian_log_predictive_score=_canonical_float(gaussian_score),
        log_score_gain=_canonical_float(estimate.feature_log_predictive_score - gaussian_score),
        anchor_capture_slack=_canonical_float(estimate.anchor_capture[0]),
        anchor_capture_policy_minus_inflation=_canonical_float(estimate.anchor_capture[1]),
        loadings_json=_json_array(estimate.loadings),
        transition_json=_json_array(estimate.transition),
        innovation_covariance_json=_json_array(estimate.innovation_covariance),
        filtered_covariance_json=_json_array(estimate.filtered_factor_covariance),
        feature_means_json=_json_array(estimate.feature_means),
        feature_scales_json=_json_array(estimate.feature_scales),
        idiosyncratic_variances_json=_json_array(estimate.idiosyncratic_variances),
    )


def run_run008(config: Run008Config) -> Run008Result:
    """Execute the frozen state-only Run 008 without loading any outcome data."""
    _validate_execution_config(config)
    if sha256_file(config.approved_design_path) != config.approved_design_sha256:
        raise Run008Error("The approved Run 008 design changed after configuration validation.")
    if sha256_file(config.panel_path) != config.panel_sha256:
        raise Run008Error("The Run 008 panel changed after configuration validation.")
    matrix = load_monthly_matrix(config.panel_path, config.features)
    expected_boundaries = (
        matrix.month_ids[0] == config.development_start,
        matrix.month_ids[config.development_months - 1] == config.development_end,
        matrix.month_ids[config.development_months] == config.evaluation_start,
        matrix.month_ids[-1] == config.evaluation_end,
    )
    if not all(expected_boundaries):
        raise Run008Error("Run 008 panel boundaries differ from the frozen development split.")
    anchors = economic_anchor_matrix(
        len(config.features),
        config.features.index("hicp_yoy"),
        config.features.index("industrial_production_yoy"),
        config.features.index("unemployment_rate"),
        config.features.index("deposit_facility_rate"),
    )
    development_subspace = estimate_anchored_subspace(
        matrix.values[: config.development_months], anchors, config.factor_dimension
    )
    fixed_loading = development_subspace.anchored_basis[:, 0].copy()

    subspace_rows: list[SubspaceEstimateRow] = []
    fixed_rows: list[FixedFactorRow] = []
    two_rows: list[TwoFactorRow] = []
    subspace_objects: dict[tuple[str, str], AnchoredSubspaceEstimate] = {}
    fixed_objects: dict[tuple[str, str], FixedLoadingFactorEstimate] = {}
    two_objects: dict[tuple[str, str], AnchoredTwoFactorEstimate] = {}

    for history_window in config.history_windows:
        for index in range(config.minimum_training_months, len(matrix.month_ids)):
            start = max(0, index - config.rolling_months) if history_window == "rolling_120" else 0
            train = matrix.values[start:index]
            current = matrix.values[index]
            month_id = matrix.month_ids[index]
            cutoff = matrix.cutoff_timestamps[index]
            subspace = estimate_anchored_subspace(train, anchors, config.factor_dimension)
            subspace_objects[(history_window, month_id)] = subspace
            subspace_rows.append(
                _subspace_row(month_id, cutoff, history_window, len(train), subspace)
            )
            standardized_train, standardized_current, _, _ = expanding_standardize(train, current)
            gaussian_score = diagonal_gaussian_log_score(standardized_train, standardized_current)
            two_factor = estimate_anchored_two_factor(
                train,
                current,
                anchors,
                config.variance_floor,
                config.transition_ridge,
                config.maximum_transition_spectral_radius,
            )
            two_objects[(history_window, month_id)] = two_factor
            two_rows.append(
                _two_factor_row(
                    month_id, cutoff, history_window, len(train), two_factor, gaussian_score
                )
            )
            if index >= config.development_months:
                fixed = estimate_fixed_loading_factor(
                    train, current, fixed_loading, config.variance_floor
                )
                fixed_objects[(history_window, month_id)] = fixed
                fixed_rows.append(
                    _fixed_row(month_id, cutoff, history_window, len(train), fixed, gaussian_score)
                )

    paired_months = tuple(
        month_id for index, month_id in enumerate(matrix.month_ids) if index > config.rolling_months
    )
    if not paired_months:
        raise Run008Error("Run 008 has no origins with genuinely different history windows.")
    comparisons = [
        compare_subspaces(
            subspace_objects[("expanding", month_id)],
            subspace_objects[("rolling_120", month_id)],
        )
        for month_id in paired_months
    ]
    second_cosines = np.asarray([comparison.principal_cosines[1] for comparison in comparisons])
    projector_distances = np.asarray(
        [comparison.root_mean_square_projector_distance for comparison in comparisons]
    )
    anchored_cosines = np.stack([comparison.anchored_loading_cosines for comparison in comparisons])
    captures = {
        history_window: np.stack(
            [
                subspace_objects[(history_window, month_id)].anchor_capture
                for month_id in paired_months
            ]
        )
        for history_window in config.history_windows
    }
    anchor_tenth_percentiles = np.minimum(
        np.percentile(captures["expanding"], 10.0, axis=0),
        np.percentile(captures["rolling_120"], 10.0, axis=0),
    )
    weak_anchor_rates = np.maximum(
        np.mean(
            captures["expanding"] < config.subspace_thresholds.weak_anchor_capture_cutoff,
            axis=0,
        ),
        np.mean(
            captures["rolling_120"] < config.subspace_thresholds.weak_anchor_capture_cutoff,
            axis=0,
        ),
    )
    subspace_metrics: dict[str, Any] = {
        "minimum_second_principal_cosine": _canonical_float(np.min(second_cosines)),
        "tenth_percentile_second_principal_cosine": _canonical_float(
            np.percentile(second_cosines, 10.0)
        ),
        "median_projector_distance": _canonical_float(np.median(projector_distances)),
        "ninetieth_percentile_projector_distance": _canonical_float(
            np.percentile(projector_distances, 90.0)
        ),
        "anchor_capture_tenth_percentile": [
            _canonical_float(value) for value in anchor_tenth_percentiles
        ],
        "weak_anchor_capture_rate": [_canonical_float(value) for value in weak_anchor_rates],
        "anchored_loading_cosine_median": [
            _canonical_float(value) for value in np.median(anchored_cosines, axis=0)
        ],
        "anchored_loading_cosine_tenth_percentile": [
            _canonical_float(value) for value in np.percentile(anchored_cosines, 10.0, axis=0)
        ],
    }
    thresholds = config.subspace_thresholds
    subspace_gates = (
        (
            "minimum_second_principal_cosine",
            float(subspace_metrics["minimum_second_principal_cosine"])
            >= thresholds.minimum_second_principal_cosine,
        ),
        (
            "tenth_percentile_second_principal_cosine",
            float(subspace_metrics["tenth_percentile_second_principal_cosine"])
            >= thresholds.minimum_tenth_percentile_second_principal_cosine,
        ),
        (
            "median_projector_distance",
            float(subspace_metrics["median_projector_distance"])
            <= thresholds.maximum_median_projector_distance,
        ),
        (
            "ninetieth_percentile_projector_distance",
            float(subspace_metrics["ninetieth_percentile_projector_distance"])
            <= thresholds.maximum_ninetieth_percentile_projector_distance,
        ),
        *tuple(
            (
                f"anchor_capture_tenth_percentile_factor_{factor + 1}",
                float(anchor_tenth_percentiles[factor])
                >= thresholds.minimum_tenth_percentile_anchor_capture_each_target,
            )
            for factor in range(config.factor_dimension)
        ),
        *tuple(
            (
                f"weak_anchor_capture_rate_factor_{factor + 1}",
                float(weak_anchor_rates[factor])
                <= thresholds.maximum_weak_anchor_capture_rate_each_target,
            )
            for factor in range(config.factor_dimension)
        ),
        *tuple(
            (
                f"anchored_loading_cosine_median_factor_{factor + 1}",
                float(np.median(anchored_cosines[:, factor]))
                >= thresholds.minimum_median_anchored_loading_cosine_each_factor,
            )
            for factor in range(config.factor_dimension)
        ),
        *tuple(
            (
                f"anchored_loading_cosine_tenth_percentile_factor_{factor + 1}",
                float(np.percentile(anchored_cosines[:, factor], 10.0))
                >= thresholds.minimum_tenth_percentile_anchored_loading_cosine_each_factor,
            )
            for factor in range(config.factor_dimension)
        ),
    )

    fixed_expanding = np.asarray(
        [fixed_objects[("expanding", month)].standardized_factor_mean for month in paired_months]
    )
    fixed_rolling = np.asarray(
        [fixed_objects[("rolling_120", month)].standardized_factor_mean for month in paired_months]
    )
    fixed_metrics = _paired_factor_metrics(fixed_expanding, fixed_rolling)
    fixed_gates = list(_factor_gates(fixed_metrics, config.fixed_scalar_thresholds))
    fixed_score_summary: dict[str, Any] = {}
    for history_window in config.history_windows:
        selected_fixed_rows = [row for row in fixed_rows if row.history_window == history_window]
        mean_gain = _canonical_float(
            float(np.mean([row.log_score_gain for row in selected_fixed_rows]))
        )
        fixed_score_summary[history_window] = {
            "origins": len(selected_fixed_rows),
            "mean_log_score_gain_vs_diagonal_gaussian": mean_gain,
            "cumulative_log_score_gain_vs_diagonal_gaussian": _canonical_float(
                sum(row.log_score_gain for row in selected_fixed_rows)
            ),
        }
        fixed_gates.append((f"positive_mean_log_score_gain__{history_window}", mean_gain > 0.0))

    two_factor_metrics: dict[str, Any] = {}
    two_factor_gates: list[tuple[str, bool]] = []
    for factor in range(config.factor_dimension):
        expanding_values = np.asarray(
            [
                two_objects[("expanding", month)].standardized_factor_mean[factor]
                for month in paired_months
            ]
        )
        rolling_values = np.asarray(
            [
                two_objects[("rolling_120", month)].standardized_factor_mean[factor]
                for month in paired_months
            ]
        )
        metrics = _paired_factor_metrics(expanding_values, rolling_values)
        factor_name = f"factor_{factor + 1}"
        two_factor_metrics[factor_name] = _factor_metrics_payload(metrics)
        two_factor_gates.extend(
            (f"{name}__{factor_name}", passed)
            for name, passed in _factor_gates(metrics, config.two_factor_thresholds)
        )
    two_factor_score_summary: dict[str, Any] = {}
    for history_window in config.history_windows:
        selected_two_factor_rows = [row for row in two_rows if row.history_window == history_window]
        two_factor_score_summary[history_window] = {
            "origins": len(selected_two_factor_rows),
            "mean_log_score_gain_vs_diagonal_gaussian": _canonical_float(
                float(np.mean([row.log_score_gain for row in selected_two_factor_rows]))
            ),
            "cumulative_log_score_gain_vs_diagonal_gaussian": _canonical_float(
                sum(row.log_score_gain for row in selected_two_factor_rows)
            ),
        }

    subspace_passed = all(passed for _, passed in subspace_gates)
    fixed_passed = all(passed for _, passed in fixed_gates)
    two_factor_diagnostic_passed = all(passed for _, passed in two_factor_gates)
    selected_representation = "fixed_loading_scalar" if subspace_passed and fixed_passed else None
    audit = {
        "experiment_id": config.experiment_id,
        "evidence_status": "REAL_DATA_OUTCOME_BLIND_RUN_008_STATE_EVALUATION",
        "config_sha256": config.config_sha256,
        "approved_design_sha256": config.approved_design_sha256,
        "panel_sha256": config.panel_sha256,
        "features": list(config.features),
        "history_windows": list(config.history_windows),
        "months": len(matrix.month_ids),
        "development_months": config.development_months,
        "development_period": [config.development_start, config.development_end],
        "evaluation_period": [config.evaluation_start, config.evaluation_end],
        "cross_window_distinct_origins": len(paired_months),
        "cross_window_shared_origins_excluded": config.rolling_months
        - config.minimum_training_months
        + 1,
        "subspace_rows": len(subspace_rows),
        "fixed_factor_rows": len(fixed_rows),
        "two_factor_rows": len(two_rows),
        "output_serialization": {
            "significant_digits": 12,
            "absolute_zero_cutoff": 1e-12,
            "raw_unidentified_pca_basis_persisted": False,
            "rotation_invariant_projector_persisted": True,
        },
        "development_fixed_loading": [_canonical_float(value) for value in fixed_loading],
        "subspace": {
            "metrics": subspace_metrics,
            "gates": dict(subspace_gates),
            "passed": subspace_passed,
        },
        "fixed_loading_scalar": {
            "metrics": _factor_metrics_payload(fixed_metrics),
            "score_summary": fixed_score_summary,
            "gates": dict(fixed_gates),
            "passed": fixed_passed,
        },
        "anchored_two_factor_diagnostic": {
            "factorwise_metrics": two_factor_metrics,
            "score_summary": two_factor_score_summary,
            "gates": dict(two_factor_gates),
            "passed": two_factor_diagnostic_passed,
            "transmission_eligible": False,
        },
        "selected_primary_state_representation": selected_representation,
        "selection_status": (
            "STATE_GATE_PASS_FIXED_LOADING_SCALAR"
            if selected_representation is not None
            else "KILL_GATE_RUN_008_REQUIRED_GATES_FAILED"
        ),
        "outcomes_accessed": False,
        "synthetic_observations_used": False,
        "transmission_estimation_authorized": False,
    }
    return Run008Result(tuple(subspace_rows), tuple(fixed_rows), tuple(two_rows), audit)


def _write_csv(rows: tuple[Any, ...], path: Path) -> None:
    if not rows:
        raise Run008Error("Run 008 cannot write an empty CSV artifact.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].__dataclass_fields__))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)
    temporary.replace(path)


def write_run008_outputs(
    result: Run008Result,
    subspace_path: Path,
    fixed_factor_path: Path,
    two_factor_path: Path,
    audit_path: Path,
) -> None:
    """Atomically write every Run 008 state-only artifact."""
    if (
        not result.subspace_rows
        or not result.fixed_factor_rows
        or not result.two_factor_rows
        or not result.audit
    ):
        raise Run008Error("Run 008 cannot write an incomplete artifact bundle.")
    paths = (subspace_path, fixed_factor_path, two_factor_path, audit_path)
    if len(set(paths)) != len(paths):
        raise Run008Error("Run 008 output paths must be distinct.")
    _write_csv(result.subspace_rows, subspace_path)
    _write_csv(result.fixed_factor_rows, fixed_factor_path)
    _write_csv(result.two_factor_rows, two_factor_path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = audit_path.with_suffix(audit_path.suffix + ".part")
    temporary.write_text(
        json.dumps(result.audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(audit_path)
