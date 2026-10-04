"""Outcome-blind orchestration for the prospective Run 007 state-model redesign."""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
import yaml

from shockbridge_state_risk.data.download import sha256_file
from shockbridge_state_risk.state.benchmarks import (
    expanding_standardize,
    semantic_order,
)
from shockbridge_state_risk.state.comparison import load_monthly_matrix
from shockbridge_state_risk.state.hmm import (
    FloatArray,
    audit_hmm_restarts,
    diagonal_gaussian_log_score,
    filter_next,
    fit_hmm_restarts,
    hmm_restart_gap_sensitivity,
    reorder_fit,
)
from shockbridge_state_risk.state.pca_emission import predict_full_rank_pca_emission
from shockbridge_state_risk.state.redesign import (
    ContinuousFactorEstimate,
    estimate_continuous_factor,
    estimate_exact_factor_states,
)
from shockbridge_state_risk.state.stability import (
    StabilityThresholds,
    evaluate_factor_stability,
)


class Run007Error(ValueError):
    """Raised when the Run 007 contract or output integrity fails."""


@dataclass(frozen=True)
class Run007Config:
    config_sha256: str
    experiment_id: str
    evidence_status: str
    panel_path: Path
    panel_sha256: str
    features: tuple[str, ...]
    history_windows: tuple[str, ...]
    minimum_training_months: int
    rolling_months: int
    variance_floor: float
    random_seed: int
    state_counts: tuple[int, ...]
    pca_components: int
    pca_restarts: int
    hmm_restarts: int
    hmm_max_iterations: int
    hmm_tolerance: float
    transition_prior: float
    hmm_objective_gap_grid: tuple[float, ...]
    thresholds: StabilityThresholds
    outcomes_accessed: bool
    execution_authorized: bool


@dataclass(frozen=True)
class FactorEstimateRow:
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
    sign_anchor_value: float
    ar_coefficient: float
    factor_innovation_variance: float
    loadings_json: str
    feature_means_json: str
    feature_scales_json: str
    idiosyncratic_variances_json: str


@dataclass(frozen=True)
class ChallengerEstimateRow:
    candidate: str
    n_states: int
    month_id: str
    cutoff_timestamp: str
    history_window: str
    training_months: int
    probability_state_0: float
    probability_state_1: float
    probability_state_2: Optional[float]
    hard_state: int
    entropy: float
    log_predictive_score: float
    restart_agreement: Optional[float]
    converged: bool


@dataclass(frozen=True)
class Run007Result:
    factor_rows: tuple[FactorEstimateRow, ...]
    challenger_rows: tuple[ChallengerEstimateRow, ...]
    restart_records: tuple[Mapping[str, Any], ...]
    audit: Mapping[str, Any]


def _mapping(value: object, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise Run007Error(f"{context} must be a mapping.")
    return value


def _sequence(value: object, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise Run007Error(f"{context} must be a list.")
    return value


def _boolean(value: object, context: str) -> bool:
    if not isinstance(value, bool):
        raise Run007Error(f"{context} must be a boolean.")
    return value


def load_run007_config(path: Path) -> Run007Config:
    payload = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "Run 007 config")
    pca = _mapping(payload.get("pca_challenger"), "pca_challenger")
    hmm = _mapping(payload.get("hmm_diagnostic"), "hmm_diagnostic")
    gates = _mapping(payload.get("stability_gates"), "stability_gates")
    required = {
        "schema_version",
        "experiment_id",
        "evidence_status",
        "panel_path",
        "panel_sha256",
        "features",
        "history_windows",
        "minimum_training_months",
        "rolling_months",
        "variance_floor",
        "random_seed",
        "state_counts",
        "outcomes_accessed",
        "execution_authorized",
    }
    if missing := sorted(required - payload.keys()):
        raise Run007Error(f"Run 007 config is missing: {missing}")
    panel_path = Path(str(payload["panel_path"]))
    if not panel_path.is_file() or sha256_file(panel_path) != str(payload["panel_sha256"]):
        raise Run007Error("Run 007 panel is missing or has a hash mismatch.")
    threshold_fields = set(StabilityThresholds.__dataclass_fields__)
    if set(gates) != threshold_fields:
        raise Run007Error("Run 007 stability-gate fields do not match the frozen contract.")
    pca_required = {"components", "restarts"}
    hmm_required = {
        "restarts",
        "max_iterations",
        "tolerance",
        "transition_prior",
        "objective_gap_grid",
    }
    if missing := sorted(pca_required - pca.keys()):
        raise Run007Error(f"pca_challenger is missing: {missing}")
    if missing := sorted(hmm_required - hmm.keys()):
        raise Run007Error(f"hmm_diagnostic is missing: {missing}")
    try:
        thresholds = StabilityThresholds(**{key: float(gates[key]) for key in threshold_fields})
        config = Run007Config(
            config_sha256=sha256_file(path),
            experiment_id=str(payload["experiment_id"]),
            evidence_status=str(payload["evidence_status"]),
            panel_path=panel_path,
            panel_sha256=str(payload["panel_sha256"]),
            features=tuple(str(value) for value in _sequence(payload["features"], "features")),
            history_windows=tuple(
                str(value) for value in _sequence(payload["history_windows"], "history_windows")
            ),
            minimum_training_months=int(payload["minimum_training_months"]),
            rolling_months=int(payload["rolling_months"]),
            variance_floor=float(payload["variance_floor"]),
            random_seed=int(payload["random_seed"]),
            state_counts=tuple(
                int(value) for value in _sequence(payload["state_counts"], "state_counts")
            ),
            pca_components=int(pca["components"]),
            pca_restarts=int(pca["restarts"]),
            hmm_restarts=int(hmm["restarts"]),
            hmm_max_iterations=int(hmm["max_iterations"]),
            hmm_tolerance=float(hmm["tolerance"]),
            transition_prior=float(hmm["transition_prior"]),
            hmm_objective_gap_grid=tuple(
                float(value) for value in _sequence(hmm["objective_gap_grid"], "objective_gap_grid")
            ),
            thresholds=thresholds,
            outcomes_accessed=_boolean(payload["outcomes_accessed"], "outcomes_accessed"),
            execution_authorized=_boolean(payload["execution_authorized"], "execution_authorized"),
        )
    except (TypeError, ValueError) as error:
        if isinstance(error, Run007Error):
            raise
        raise Run007Error(f"Run 007 config contains an invalid value: {error}") from error
    if (
        payload["schema_version"] != 1
        or config.experiment_id != "state-model-run007-v1"
        or config.evidence_status != "REAL_DATA_OUTCOME_BLIND"
        or config.outcomes_accessed
        or not config.execution_authorized
    ):
        raise Run007Error("Run 007 must be authorized and outcome blind.")
    if len(config.features) != 4 or len(set(config.features)) != 4:
        raise Run007Error("Run 007 requires four unique frozen features.")
    if (
        "industrial_production_yoy" not in config.features
        or "unemployment_rate" not in config.features
    ):
        raise Run007Error("Run 007 sign-anchor features are missing.")
    if config.history_windows != ("expanding", "rolling_120"):
        raise Run007Error("Run 007 history windows are not frozen correctly.")
    if config.state_counts != (2, 3):
        raise Run007Error("Run 007 requires two- and three-state challengers.")
    if (
        config.minimum_training_months < 36
        or config.rolling_months <= config.minimum_training_months
        or config.variance_floor <= 0
        or config.pca_components < 1
        or config.pca_components > len(config.features)
        or config.pca_restarts < 2
        or config.hmm_restarts < 2
        or config.hmm_max_iterations < 1
        or config.hmm_tolerance <= 0
        or config.transition_prior <= 0
    ):
        raise Run007Error("Run 007 numerical settings are invalid.")
    continuous_values = (
        config.variance_floor,
        config.hmm_tolerance,
        config.transition_prior,
        *config.hmm_objective_gap_grid,
    )
    if any(not np.isfinite(value) for value in continuous_values):
        raise Run007Error("Run 007 numerical settings must be finite.")
    if config.hmm_objective_gap_grid != (0.0, 2.0, 5.0, 10.0):
        raise Run007Error("Run 007 HMM objective-gap grid differs from the frozen grid.")
    frozen_thresholds = StabilityThresholds(
        minimum_pearson_correlation=0.80,
        minimum_spearman_correlation=0.80,
        maximum_sign_disagreement_rate=0.10,
        maximum_standardized_mean_absolute_difference=0.35,
        minimum_median_loading_cosine=0.90,
        minimum_loading_cosine=0.75,
        minimum_anchor_tenth_percentile=0.20,
        weak_anchor_cutoff=0.10,
        maximum_weak_anchor_rate=0.05,
    )
    if config.thresholds != frozen_thresholds:
        raise Run007Error("Run 007 stability gates differ from the frozen execution contract.")
    frozen_numerical_settings = (
        config.minimum_training_months == 60,
        config.rolling_months == 120,
        config.variance_floor == 0.05,
        config.random_seed == 73107,
        config.pca_components == 2,
        config.pca_restarts == 20,
        config.hmm_restarts == 6,
        config.hmm_max_iterations == 150,
        config.hmm_tolerance == 0.000001,
        config.transition_prior == 0.5,
    )
    if not all(frozen_numerical_settings):
        raise Run007Error("Run 007 numerical settings differ from the frozen execution contract.")
    return config


def _json_vector(values: FloatArray) -> str:
    return json.dumps([float(value) for value in values], separators=(",", ":"))


def _entropy(probabilities: FloatArray) -> float:
    clipped = np.clip(probabilities, 1e-15, 1.0)
    return float(-np.sum(clipped * np.log(clipped)))


def _challenger_row(
    candidate: str,
    n_states: int,
    month_id: str,
    cutoff_timestamp: str,
    history_window: str,
    training_months: int,
    probabilities: FloatArray,
    score: float,
    agreement: Optional[float],
    converged: bool,
) -> ChallengerEstimateRow:
    if probabilities.shape != (n_states,) or np.any(~np.isfinite(probabilities)):
        raise Run007Error(f"{candidate} returned invalid probabilities.")
    if not math.isclose(float(np.sum(probabilities)), 1.0, rel_tol=0.0, abs_tol=1e-10):
        raise Run007Error(f"{candidate} probabilities do not sum to one.")
    if not np.isfinite(score):
        raise Run007Error(f"{candidate} returned a non-finite predictive score.")
    return ChallengerEstimateRow(
        candidate=candidate,
        n_states=n_states,
        month_id=month_id,
        cutoff_timestamp=cutoff_timestamp,
        history_window=history_window,
        training_months=training_months,
        probability_state_0=float(probabilities[0]),
        probability_state_1=float(probabilities[1]),
        probability_state_2=float(probabilities[2]) if n_states == 3 else None,
        hard_state=int(np.argmax(probabilities)),
        entropy=_entropy(probabilities),
        log_predictive_score=score,
        restart_agreement=agreement,
        converged=converged,
    )


def run_run007(config: Run007Config) -> Run007Result:
    if sha256_file(config.panel_path) != config.panel_sha256:
        raise Run007Error("Run 007 panel changed after configuration validation.")
    matrix = load_monthly_matrix(config.panel_path, config.features)
    ip_index = config.features.index("industrial_production_yoy")
    unemployment_index = config.features.index("unemployment_rate")
    factor_rows: list[FactorEstimateRow] = []
    challenger_rows: list[ChallengerEstimateRow] = []
    restart_records: list[Mapping[str, Any]] = []
    factor_objects: dict[tuple[str, str], ContinuousFactorEstimate] = {}

    for window_index, history_window in enumerate(config.history_windows):
        for index in range(config.minimum_training_months, len(matrix.month_ids)):
            start = max(0, index - config.rolling_months) if history_window == "rolling_120" else 0
            train = matrix.values[start:index]
            current = matrix.values[index]
            month_id = matrix.month_ids[index]
            cutoff = matrix.cutoff_timestamps[index]
            factor = estimate_continuous_factor(
                train,
                current,
                config.variance_floor,
                ip_index,
                unemployment_index,
            )
            standardized_train, standardized_current, _, _ = expanding_standardize(train, current)
            factor_rows.append(
                FactorEstimateRow(
                    month_id=month_id,
                    cutoff_timestamp=cutoff,
                    history_window=history_window,
                    training_months=len(train),
                    filtered_factor_mean=factor.filtered_factor_mean,
                    filtered_factor_variance=factor.filtered_factor_variance,
                    standardized_factor_mean=factor.standardized_factor_mean,
                    standardized_factor_variance=factor.standardized_factor_variance,
                    feature_log_predictive_score=factor.feature_log_predictive_score,
                    gaussian_log_predictive_score=diagonal_gaussian_log_score(
                        standardized_train, standardized_current
                    ),
                    sign_anchor_value=factor.sign_anchor_value,
                    ar_coefficient=factor.ar_coefficient,
                    factor_innovation_variance=factor.factor_innovation_variance,
                    loadings_json=_json_vector(factor.loadings),
                    feature_means_json=_json_vector(factor.feature_means),
                    feature_scales_json=_json_vector(factor.feature_scales),
                    idiosyncratic_variances_json=_json_vector(factor.idiosyncratic_variances),
                )
            )
            factor_objects[(history_window, month_id)] = factor

            for n_states in config.state_counts:
                exact = estimate_exact_factor_states(
                    train,
                    current,
                    n_states,
                    config.variance_floor,
                    ip_index,
                    unemployment_index,
                )
                challenger_rows.append(
                    _challenger_row(
                        "exact_factor",
                        n_states,
                        month_id,
                        cutoff,
                        history_window,
                        len(train),
                        exact.probabilities,
                        exact.factor_mixture_log_score,
                        None,
                        True,
                    )
                )

                seed = (
                    config.random_seed
                    + window_index * 1_000_003
                    + n_states * 100_003
                    + index * 1009
                )
                pca = predict_full_rank_pca_emission(
                    standardized_train,
                    standardized_current,
                    n_states,
                    config.pca_components,
                    config.pca_restarts,
                    config.variance_floor,
                    seed,
                )
                challenger_rows.append(
                    _challenger_row(
                        "pca_full_rank",
                        n_states,
                        month_id,
                        cutoff,
                        history_window,
                        len(train),
                        pca.probabilities,
                        pca.log_predictive_score,
                        pca.restart_agreement,
                        True,
                    )
                )
                for pca_record in pca.restart_records:
                    restart_records.append(
                        {
                            "record_type": "pca_restart",
                            "candidate": "pca_full_rank",
                            "n_states": n_states,
                            "month_id": month_id,
                            "history_window": history_window,
                            **asdict(pca_record),
                        }
                    )

                best, fits = fit_hmm_restarts(
                    standardized_train,
                    n_states,
                    config.hmm_restarts,
                    config.hmm_max_iterations,
                    config.hmm_tolerance,
                    config.variance_floor,
                    config.transition_prior,
                    seed + 10_000_019,
                )
                hmm_audit = audit_hmm_restarts(fits)
                order = semantic_order(best.parameters.means)
                inverse = np.empty(n_states, dtype=np.int64)
                inverse[np.asarray(order)] = np.arange(n_states, dtype=np.int64)
                ordered_best = reorder_fit(best, order)
                probabilities, score = filter_next(
                    ordered_best.parameters,
                    ordered_best.filtered_probabilities[-1],
                    standardized_current,
                )
                challenger_rows.append(
                    _challenger_row(
                        "hidden_markov_diagnostic",
                        n_states,
                        month_id,
                        cutoff,
                        history_window,
                        len(train),
                        probabilities,
                        score,
                        hmm_audit.objective_weighted_agreement,
                        ordered_best.converged,
                    )
                )
                for hmm_record in hmm_audit.records:
                    payload = asdict(hmm_record)
                    payload["aligned_hard_assignments"] = [
                        int(inverse[value]) for value in hmm_record.aligned_hard_assignments
                    ]
                    restart_records.append(
                        {
                            "record_type": "hmm_restart",
                            "candidate": "hidden_markov_diagnostic",
                            "n_states": n_states,
                            "month_id": month_id,
                            "history_window": history_window,
                            **payload,
                        }
                    )
                for sensitivity in hmm_restart_gap_sensitivity(
                    hmm_audit, config.hmm_objective_gap_grid
                ):
                    restart_records.append(
                        {
                            "record_type": "hmm_gap_sensitivity",
                            "candidate": "hidden_markov_diagnostic",
                            "n_states": n_states,
                            "month_id": month_id,
                            "history_window": history_window,
                            **asdict(sensitivity),
                        }
                    )

    paired_months = [
        month_id
        for month_id in matrix.month_ids[config.minimum_training_months :]
        if next(
            row.training_months
            for row in factor_rows
            if row.month_id == month_id and row.history_window == "expanding"
        )
        > config.rolling_months
    ]
    expanding = [factor_objects[("expanding", month)] for month in paired_months]
    rolling = [factor_objects[("rolling_120", month)] for month in paired_months]
    stability = evaluate_factor_stability(
        np.asarray([item.standardized_factor_mean for item in expanding]),
        np.asarray([item.standardized_factor_mean for item in rolling]),
        np.stack([item.loadings for item in expanding]),
        np.stack([item.loadings for item in rolling]),
        np.asarray([item.sign_anchor_value for item in expanding]),
        np.asarray([item.sign_anchor_value for item in rolling]),
        config.thresholds,
    )
    factor_summary: dict[str, Any] = {}
    for history_window in config.history_windows:
        selected_factor_rows = [row for row in factor_rows if row.history_window == history_window]
        factor_summary[history_window] = {
            "origins": len(selected_factor_rows),
            "cumulative_log_predictive_score": float(
                sum(row.feature_log_predictive_score for row in selected_factor_rows)
            ),
            "cumulative_gaussian_log_predictive_score": float(
                sum(row.gaussian_log_predictive_score for row in selected_factor_rows)
            ),
            "score_gain_vs_diagonal_gaussian": float(
                sum(
                    row.feature_log_predictive_score - row.gaussian_log_predictive_score
                    for row in selected_factor_rows
                )
            ),
        }
    challenger_summary: dict[str, Any] = {}
    for candidate in ("exact_factor", "pca_full_rank", "hidden_markov_diagnostic"):
        for n_states in config.state_counts:
            for history_window in config.history_windows:
                selected_challenger_rows = [
                    row
                    for row in challenger_rows
                    if row.candidate == candidate
                    and row.n_states == n_states
                    and row.history_window == history_window
                ]
                key = f"{candidate}__k{n_states}__{history_window}"
                agreements = [
                    row.restart_agreement
                    for row in selected_challenger_rows
                    if row.restart_agreement is not None
                ]
                challenger_summary[key] = {
                    "origins": len(selected_challenger_rows),
                    "score_domain": (
                        "standardized_scalar_factor_not_cross_candidate_comparable"
                        if candidate == "exact_factor"
                        else "observed_standardized_feature_dimensions"
                    ),
                    "cumulative_log_predictive_score": float(
                        sum(row.log_predictive_score for row in selected_challenger_rows)
                    ),
                    "minimum_restart_agreement": min(agreements) if agreements else None,
                    "all_converged": all(row.converged for row in selected_challenger_rows),
                }
    audit = {
        "experiment_id": config.experiment_id,
        "evidence_status": "REAL_DATA_OUTCOME_BLIND_RUN_007_STATE_EVALUATION",
        "config_sha256": config.config_sha256,
        "panel_sha256": config.panel_sha256,
        "features": list(config.features),
        "history_windows": list(config.history_windows),
        "state_counts": list(config.state_counts),
        "months": len(matrix.month_ids),
        "warmup_months": config.minimum_training_months,
        "rolling_months": config.rolling_months,
        "factor_rows": len(factor_rows),
        "challenger_rows": len(challenger_rows),
        "restart_records": len(restart_records),
        "cross_window_distinct_origins": len(paired_months),
        "cross_window_shared_origins_excluded": (
            len(matrix.month_ids) - config.minimum_training_months - len(paired_months)
        ),
        "numerical_contract": {
            "variance_floor": config.variance_floor,
            "random_seed": config.random_seed,
            "pca_components": config.pca_components,
            "pca_restarts": config.pca_restarts,
            "hmm_restarts": config.hmm_restarts,
            "hmm_max_iterations": config.hmm_max_iterations,
            "hmm_tolerance": config.hmm_tolerance,
            "transition_prior": config.transition_prior,
            "hmm_objective_gap_grid": list(config.hmm_objective_gap_grid),
            "stability_thresholds": asdict(config.thresholds),
        },
        "continuous_factor": factor_summary,
        "stability": {
            **asdict(stability),
            "gates": dict(stability.gates),
        },
        "challengers": challenger_summary,
        "selected_primary_state_representation": (
            "continuous_factor" if stability.passed else None
        ),
        "selection_status": (
            "STATE_GATE_PASS_CONTINUOUS_FACTOR"
            if stability.passed
            else "KILL_GATE_CONTINUOUS_FACTOR_UNSTABLE"
        ),
        "outcomes_accessed": False,
        "synthetic_observations_used": False,
        "transmission_estimation_authorized": False,
    }
    return Run007Result(
        factor_rows=tuple(factor_rows),
        challenger_rows=tuple(challenger_rows),
        restart_records=tuple(restart_records),
        audit=audit,
    )


def _write_csv(rows: tuple[Any, ...], path: Path) -> None:
    if not rows:
        raise Run007Error("Run 007 cannot write an empty CSV artifact.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].__dataclass_fields__))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)
    temporary.replace(path)


def write_run007_outputs(
    result: Run007Result,
    factor_path: Path,
    challenger_path: Path,
    restart_path: Path,
    audit_path: Path,
) -> None:
    """Atomically write every Run 007 empirical and audit artifact."""
    _write_csv(result.factor_rows, factor_path)
    _write_csv(result.challenger_rows, challenger_path)
    restart_path.parent.mkdir(parents=True, exist_ok=True)
    restart_temporary = restart_path.with_suffix(restart_path.suffix + ".part")
    restart_temporary.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in result.restart_records),
        encoding="utf-8",
    )
    restart_temporary.replace(restart_path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_temporary = audit_path.with_suffix(audit_path.suffix + ".part")
    audit_temporary.write_text(
        json.dumps(result.audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    audit_temporary.replace(audit_path)
