"""Historical comparison of required state-model benchmarks."""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np
import yaml

from shockbridge_state_risk.data.download import sha256_file
from shockbridge_state_risk.state.benchmarks import (
    BenchmarkPrediction,
    expanding_standardize,
    predict_change_point,
    predict_dynamic_factor,
    predict_hidden_markov,
    predict_pca_cluster,
)
from shockbridge_state_risk.state.hmm import FloatArray, diagonal_gaussian_log_score


class ComparisonError(ValueError):
    """Raised when the comparison contract or result integrity fails."""


@dataclass(frozen=True)
class ComparisonConfig:
    panel_path: Path
    panel_sha256: str
    features: tuple[str, ...]
    models: tuple[str, ...]
    state_counts: tuple[int, ...]
    history_windows: tuple[str, ...]
    minimum_training_months: int
    random_seed: int
    kmeans_restarts: int
    hmm_restarts: int
    hmm_max_iterations: int
    hmm_tolerance: float
    variance_floor: float
    transition_prior: float
    pca_components: int
    change_point_threshold: float
    change_point_minimum_segment: int
    minimum_global_hard_count: int
    minimum_global_weighted_ess: float
    minimum_block_hard_count: int
    minimum_block_weighted_ess: float
    minimum_restart_agreement: float
    require_score_gain: bool
    primary_state_count: int
    primary_history_window: str


@dataclass(frozen=True)
class MonthlyMatrix:
    month_ids: tuple[str, ...]
    cutoff_timestamps: tuple[str, ...]
    values: FloatArray


@dataclass(frozen=True)
class ComparisonRow:
    model: str
    n_states: int
    history_window: str
    month_id: str
    cutoff_timestamp: str
    training_months: int
    probability_state_0: float
    probability_state_1: float
    probability_state_2: Optional[float]
    hard_state: int
    entropy: float
    log_predictive_score: float
    gaussian_log_predictive_score: float
    restart_agreement: Optional[float]
    converged: bool


@dataclass(frozen=True)
class ComparisonResult:
    rows: tuple[ComparisonRow, ...]
    audit: Mapping[str, Any]


def _require_mapping(value: object, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ComparisonError(f"{context} must be a mapping.")
    return value


def load_comparison_config(path: Path) -> ComparisonConfig:
    payload = _require_mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "config")
    screening = _require_mapping(payload.get("screening"), "screening")
    selection = _require_mapping(payload.get("selection"), "selection")
    required = {
        "panel_path",
        "panel_sha256",
        "features",
        "models",
        "state_counts",
        "history_windows",
        "minimum_training_months",
        "random_seed",
        "kmeans_restarts",
        "hmm_restarts",
        "hmm_max_iterations",
        "hmm_tolerance",
        "variance_floor",
        "transition_prior",
        "pca_components",
        "change_point_threshold",
        "change_point_minimum_segment",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ComparisonError(f"Comparison config is missing: {missing}")
    screening_required = {
        "minimum_global_hard_count",
        "minimum_global_weighted_ess",
        "minimum_block_hard_count",
        "minimum_block_weighted_ess",
        "minimum_restart_agreement",
        "require_score_gain_vs_single_gaussian",
    }
    selection_required = {"primary_state_count", "primary_history_window"}
    if missing_screening := sorted(screening_required - screening.keys()):
        raise ComparisonError(f"Screening config is missing: {missing_screening}")
    if missing_selection := sorted(selection_required - selection.keys()):
        raise ComparisonError(f"Selection config is missing: {missing_selection}")
    for field in ("features", "models", "state_counts", "history_windows"):
        if not isinstance(payload[field], list):
            raise ComparisonError(f"{field} must be a list.")
    if not isinstance(screening["require_score_gain_vs_single_gaussian"], bool):
        raise ComparisonError("require_score_gain_vs_single_gaussian must be Boolean.")
    panel_path = Path(str(payload["panel_path"]))
    if not panel_path.is_file():
        raise ComparisonError(f"Comparison panel is missing: {panel_path}")
    panel_sha256 = str(payload["panel_sha256"])
    if sha256_file(panel_path) != panel_sha256:
        raise ComparisonError("Comparison panel hash mismatch.")
    config = ComparisonConfig(
        panel_path=panel_path,
        panel_sha256=panel_sha256,
        features=tuple(str(item) for item in payload["features"]),
        models=tuple(str(item) for item in payload["models"]),
        state_counts=tuple(int(item) for item in payload["state_counts"]),
        history_windows=tuple(str(item) for item in payload["history_windows"]),
        minimum_training_months=int(payload["minimum_training_months"]),
        random_seed=int(payload["random_seed"]),
        kmeans_restarts=int(payload["kmeans_restarts"]),
        hmm_restarts=int(payload["hmm_restarts"]),
        hmm_max_iterations=int(payload["hmm_max_iterations"]),
        hmm_tolerance=float(payload["hmm_tolerance"]),
        variance_floor=float(payload["variance_floor"]),
        transition_prior=float(payload["transition_prior"]),
        pca_components=int(payload["pca_components"]),
        change_point_threshold=float(payload["change_point_threshold"]),
        change_point_minimum_segment=int(payload["change_point_minimum_segment"]),
        minimum_global_hard_count=int(screening["minimum_global_hard_count"]),
        minimum_global_weighted_ess=float(screening["minimum_global_weighted_ess"]),
        minimum_block_hard_count=int(screening["minimum_block_hard_count"]),
        minimum_block_weighted_ess=float(screening["minimum_block_weighted_ess"]),
        minimum_restart_agreement=float(screening["minimum_restart_agreement"]),
        require_score_gain=bool(screening["require_score_gain_vs_single_gaussian"]),
        primary_state_count=int(selection["primary_state_count"]),
        primary_history_window=str(selection["primary_history_window"]),
    )
    expected_models = {
        "pca_cluster",
        "dynamic_factor",
        "hidden_markov",
        "change_point",
    }
    if len(config.features) != len(set(config.features)) or not config.features:
        raise ComparisonError("Comparison features must be nonempty and unique.")
    if len(config.models) != len(expected_models) or set(config.models) != expected_models:
        raise ComparisonError("All four Blueprint V2 benchmark models are required.")
    if config.state_counts != (2, 3):
        raise ComparisonError("The frozen sensitivity requires two and three states.")
    if len(config.history_windows) != 2 or set(config.history_windows) != {
        "expanding",
        "rolling_120",
    }:
        raise ComparisonError("The frozen history-window sensitivity is incomplete.")
    if config.minimum_training_months < 36:
        raise ComparisonError("At least 36 training months are required.")
    if config.kmeans_restarts < 2 or config.hmm_restarts < 2:
        raise ComparisonError("Stability audits require at least two restarts.")
    if (
        config.hmm_max_iterations < 1
        or config.hmm_tolerance <= 0
        or config.variance_floor <= 0
        or config.transition_prior <= 0
        or config.pca_components < 1
        or config.change_point_threshold <= 0
        or config.change_point_minimum_segment < 2
    ):
        raise ComparisonError("Comparison optimization settings must be positive.")
    if (
        config.minimum_global_hard_count < 0
        or config.minimum_global_weighted_ess < 0
        or config.minimum_block_hard_count < 0
        or config.minimum_block_weighted_ess < 0
        or not 0.0 <= config.minimum_restart_agreement <= 1.0
    ):
        raise ComparisonError("Comparison screening thresholds are invalid.")
    if config.primary_state_count not in config.state_counts:
        raise ComparisonError("Primary state count is outside the frozen grid.")
    if config.primary_history_window not in config.history_windows:
        raise ComparisonError("Primary history window is outside the frozen grid.")
    return config


def load_monthly_matrix(path: Path, features: tuple[str, ...]) -> MonthlyMatrix:
    values: dict[str, dict[str, float]] = {}
    cutoffs: dict[str, str] = {}
    seen_keys: set[tuple[str, str]] = set()
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            feature = row["feature_id"]
            if feature not in features:
                continue
            if row["admission_status"] != "ADMITTED":
                raise ComparisonError(f"Non-admitted monthly feature: {feature}")
            month_id = row["event_id"]
            key = (month_id, feature)
            if key in seen_keys:
                raise ComparisonError(f"Duplicate monthly feature row: {month_id}, {feature}")
            seen_keys.add(key)
            cutoff = row["state_cutoff_timestamp"]
            try:
                parsed_cutoff = datetime.fromisoformat(cutoff)
            except ValueError as exc:
                raise ComparisonError(f"Invalid monthly cutoff: {cutoff}") from exc
            if parsed_cutoff.utcoffset() is None:
                raise ComparisonError(f"Monthly cutoff lacks a timezone offset: {cutoff}")
            if month_id in cutoffs and cutoffs[month_id] != cutoff:
                raise ComparisonError(f"Inconsistent monthly cutoff: {month_id}")
            cutoffs[month_id] = cutoff
            values.setdefault(month_id, {})
            missing = row["missing"]
            if missing not in {"True", "False"}:
                raise ComparisonError(f"Invalid missingness flag: {month_id}, {feature}")
            if missing == "False":
                if not row["value"]:
                    raise ComparisonError(
                        f"Observed monthly feature lacks value: {month_id}, {feature}"
                    )
                value = float(row["value"])
                if not math.isfinite(value):
                    raise ComparisonError(f"Non-finite monthly feature: {month_id}, {feature}")
                values[month_id][feature] = value
            elif row["value"]:
                raise ComparisonError(
                    f"Missing monthly feature carries value: {month_id}, {feature}"
                )
    month_ids = tuple(sorted(values, key=lambda item: datetime.fromisoformat(cutoffs[item])))
    missing_keys = {
        (month_id, feature)
        for month_id in month_ids
        for feature in features
        if (month_id, feature) not in seen_keys
    }
    if missing_keys:
        month_id, feature = sorted(missing_keys)[0]
        raise ComparisonError(f"Missing monthly feature row: {month_id}, {feature}")
    matrix = np.full((len(month_ids), len(features)), np.nan, dtype=np.float64)
    for row_index, month_id in enumerate(month_ids):
        for column, feature in enumerate(features):
            if feature in values[month_id]:
                matrix[row_index, column] = values[month_id][feature]
    if np.any(np.sum(np.isfinite(matrix), axis=0) < 36):
        raise ComparisonError("Every monthly feature needs at least 36 observations.")
    return MonthlyMatrix(month_ids, tuple(cutoffs[item] for item in month_ids), matrix)


def _prediction(
    model: str,
    train: FloatArray,
    current: FloatArray,
    n_states: int,
    config: ComparisonConfig,
    seed: int,
) -> BenchmarkPrediction:
    if model == "pca_cluster":
        return predict_pca_cluster(
            train,
            current,
            n_states,
            config.pca_components,
            config.kmeans_restarts,
            config.variance_floor,
            seed,
        )
    if model == "dynamic_factor":
        return predict_dynamic_factor(
            train,
            current,
            n_states,
            config.kmeans_restarts,
            config.variance_floor,
            seed,
        )
    if model == "hidden_markov":
        return predict_hidden_markov(
            train,
            current,
            n_states,
            config.hmm_restarts,
            config.hmm_max_iterations,
            config.hmm_tolerance,
            config.variance_floor,
            config.transition_prior,
            seed,
        )
    if model == "change_point":
        return predict_change_point(
            train,
            current,
            n_states,
            config.kmeans_restarts,
            config.variance_floor,
            config.change_point_threshold,
            config.change_point_minimum_segment,
            seed,
        )
    raise ComparisonError(f"Unknown benchmark model: {model}")


def _entropy(probabilities: FloatArray) -> float:
    clipped = np.clip(probabilities, 1e-15, 1.0)
    return float(-np.sum(clipped * np.log(clipped)))


def _effective_sample_size(weights: FloatArray) -> float:
    denominator = float(np.sum(weights**2))
    return float(np.sum(weights) ** 2 / denominator) if denominator > 0 else 0.0


def _variant_audit(rows: list[ComparisonRow], config: ComparisonConfig) -> dict[str, Any]:
    n_states = rows[0].n_states
    probabilities = np.asarray(
        [
            [
                row.probability_state_0,
                row.probability_state_1,
                *([row.probability_state_2] if n_states == 3 else []),
            ]
            for row in rows
        ],
        dtype=np.float64,
    )
    hard = np.argmax(probabilities, axis=1)
    blocks = np.asarray(
        [min(2, index * 3 // len(rows)) for index in range(len(rows))],
        dtype=np.int64,
    )
    states: dict[str, Any] = {}
    minimum_block_hard = math.inf
    minimum_block_ess = math.inf
    for state in range(n_states):
        weights = probabilities[:, state]
        block_records: dict[str, Any] = {}
        for block in range(3):
            selection = blocks == block
            block_weights = weights[selection]
            hard_count = int(np.sum(hard[selection] == state))
            ess = _effective_sample_size(block_weights)
            minimum_block_hard = min(minimum_block_hard, hard_count)
            minimum_block_ess = min(minimum_block_ess, ess)
            block_records[str(block + 1)] = {
                "hard_count": hard_count,
                "weighted_ess": ess,
                "weighted_count": float(np.sum(block_weights)),
            }
        states[str(state)] = {
            "hard_count": int(np.sum(hard == state)),
            "weighted_count": float(np.sum(weights)),
            "weighted_ess": _effective_sample_size(weights),
            "blocks": block_records,
        }
    score_gain = float(
        sum(row.log_predictive_score - row.gaussian_log_predictive_score for row in rows)
    )
    agreements = [float(row.restart_agreement) for row in rows if row.restart_agreement is not None]
    minimum_agreement = min(agreements) if agreements else 1.0
    gates = {
        "score_gain_vs_single_gaussian": score_gain > 0 if config.require_score_gain else True,
        "global_hard_count": min(int(states[str(state)]["hard_count"]) for state in range(n_states))
        >= config.minimum_global_hard_count,
        "global_weighted_ess": min(
            float(states[str(state)]["weighted_ess"]) for state in range(n_states)
        )
        >= config.minimum_global_weighted_ess,
        "block_hard_count": minimum_block_hard >= config.minimum_block_hard_count,
        "block_weighted_ess": minimum_block_ess >= config.minimum_block_weighted_ess,
        "restart_agreement": minimum_agreement >= config.minimum_restart_agreement,
        "all_fits_converged": all(row.converged for row in rows),
    }
    return {
        "eligible_months": len(rows),
        "cumulative_log_predictive_score": float(sum(row.log_predictive_score for row in rows)),
        "cumulative_gaussian_log_predictive_score": float(
            sum(row.gaussian_log_predictive_score for row in rows)
        ),
        "score_gain_vs_single_gaussian": score_gain,
        "mean_entropy": float(np.mean([row.entropy for row in rows])),
        "minimum_restart_agreement": minimum_agreement,
        "states": states,
        "screening_gates": gates,
        "screening_pass": all(gates.values()),
    }


def run_comparison(config: ComparisonConfig) -> ComparisonResult:
    matrix = load_monthly_matrix(config.panel_path, config.features)
    rows: list[ComparisonRow] = []
    profiles: dict[str, list[FloatArray]] = {}
    for model_index, model in enumerate(config.models):
        for n_states in config.state_counts:
            for window_index, history_window in enumerate(config.history_windows):
                variant = f"{model}__k{n_states}__{history_window}"
                profiles[variant] = []
                for index in range(config.minimum_training_months, len(matrix.month_ids)):
                    start = max(0, index - 120) if history_window == "rolling_120" else 0
                    raw_train = matrix.values[start:index]
                    raw_current = matrix.values[index]
                    train, current, means, scales = expanding_standardize(raw_train, raw_current)
                    seed = (
                        config.random_seed
                        + model_index * 10_000_019
                        + n_states * 100_003
                        + window_index * 1_000_003
                        + index * 1009
                    )
                    prediction = _prediction(model, train, current, n_states, config, seed)
                    if not math.isclose(
                        float(np.sum(prediction.probabilities)),
                        1.0,
                        rel_tol=0.0,
                        abs_tol=1e-10,
                    ):
                        raise ComparisonError(f"Probabilities do not sum to one: {variant}")
                    raw_profiles = prediction.state_profiles * scales + means
                    profiles[variant].append(raw_profiles)
                    probabilities = prediction.probabilities
                    rows.append(
                        ComparisonRow(
                            model=model,
                            n_states=n_states,
                            history_window=history_window,
                            month_id=matrix.month_ids[index],
                            cutoff_timestamp=matrix.cutoff_timestamps[index],
                            training_months=len(raw_train),
                            probability_state_0=float(probabilities[0]),
                            probability_state_1=float(probabilities[1]),
                            probability_state_2=(
                                float(probabilities[2]) if n_states == 3 else None
                            ),
                            hard_state=int(np.argmax(probabilities)),
                            entropy=_entropy(probabilities),
                            log_predictive_score=prediction.log_predictive_score,
                            gaussian_log_predictive_score=diagonal_gaussian_log_score(
                                train, current
                            ),
                            restart_agreement=prediction.restart_agreement,
                            converged=prediction.converged,
                        )
                    )
    variants: dict[str, Any] = {}
    for variant, variant_profiles in profiles.items():
        model, state_text, history_window = variant.split("__")
        n_states = int(state_text.removeprefix("k"))
        variant_rows = [
            row
            for row in rows
            if row.model == model
            and row.n_states == n_states
            and row.history_window == history_window
        ]
        audit = _variant_audit(variant_rows, config)
        audit["mean_state_profiles"] = np.mean(np.stack(variant_profiles), axis=0).tolist()
        variants[variant] = audit

    primary_variants = {
        model: variants[f"{model}__k{config.primary_state_count}__{config.primary_history_window}"]
        for model in config.models
    }
    eligible = [model for model, audit in primary_variants.items() if audit["screening_pass"]]
    selected = (
        max(
            eligible,
            key=lambda model: float(primary_variants[model]["cumulative_log_predictive_score"]),
        )
        if eligible
        else None
    )
    audit = {
        "evidence_status": "REAL_DATA_OUTCOME_BLIND_MODEL_COMPARISON",
        "panel_sha256": config.panel_sha256,
        "months": len(matrix.month_ids),
        "warmup_months": config.minimum_training_months,
        "variants": variants,
        "primary_candidates_passing_all_gates": eligible,
        "selected_primary_model": selected,
        "selection_status": "SELECTED" if selected else "KILL_GATE_NO_ELIGIBLE_MODEL",
        "outcomes_accessed": False,
        "synthetic_observations_used": False,
        "important_comparability_note": (
            "All density scores use the same expanding standardization and observed "
            "feature dimensions, but model likelihoods are approximations specific to "
            "each benchmark family; support and stability gates remain co-primary."
        ),
    }
    return ComparisonResult(tuple(rows), audit)


def write_comparison_csv(rows: tuple[ComparisonRow, ...], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(ComparisonRow.__dataclass_fields__))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)
    temporary.replace(path)


def write_comparison_audit(audit: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
