"""Expanding, outcome-blind historical replay for the event-indexed HMM benchmark."""

from __future__ import annotations

import csv
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Optional

import numpy as np
import yaml
from numpy.typing import NDArray

from shockbridge_state_risk.data.download import sha256_file
from shockbridge_state_risk.state.hmm import (
    FloatArray,
    HMMFit,
    alignment_order,
    diagonal_gaussian_log_score,
    filter_next,
    fit_hmm_restarts,
    reorder_fit,
)


class StateReplayError(ValueError):
    """Raised when replay inputs or outputs violate the frozen state contract."""


@dataclass(frozen=True)
class StateReplayConfig:
    panel_path: Path
    panel_sha256: str
    shock_path: Path
    shock_sha256: str
    features: tuple[str, ...]
    n_states: int
    minimum_training_events: int
    restarts: int
    max_iterations: int
    tolerance: float
    variance_floor: float
    transition_prior: float
    random_seed: int
    minimum_hard_count: int
    minimum_weighted_ess: float
    maximum_mean_entropy: float
    minimum_restart_agreement: float


@dataclass(frozen=True)
class StateMatrix:
    event_ids: tuple[str, ...]
    event_dates: tuple[date, ...]
    values: FloatArray


@dataclass(frozen=True)
class ReplayRow:
    event_id: str
    event_date: str
    training_events: int
    probability_state_0: Optional[float]
    probability_state_1: Optional[float]
    hard_state: Optional[int]
    entropy: Optional[float]
    hmm_log_predictive: Optional[float]
    gaussian_log_predictive: Optional[float]
    restart_hard_agreement: Optional[float]
    fit_converged: Optional[bool]
    fit_iterations: Optional[int]
    fit_seed: Optional[int]


@dataclass(frozen=True)
class StateReplayResult:
    rows: tuple[ReplayRow, ...]
    audit: Mapping[str, Any]


def load_state_replay_config(path: Path) -> StateReplayConfig:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise StateReplayError("State replay config must be a mapping.")
    required = {
        "panel_path",
        "panel_sha256",
        "shock_path",
        "shock_sha256",
        "features",
        "n_states",
        "minimum_training_events",
        "restarts",
        "max_iterations",
        "tolerance",
        "variance_floor",
        "transition_prior",
        "random_seed",
        "minimum_hard_count",
        "minimum_weighted_ess",
        "maximum_mean_entropy",
        "minimum_restart_agreement",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise StateReplayError(f"State replay config is missing: {missing}")
    features = payload["features"]
    if not isinstance(features, list) or not all(isinstance(item, str) for item in features):
        raise StateReplayError("features must be a list of strings.")
    if not features or len(features) != len(set(features)):
        raise StateReplayError("features must be nonempty and unique.")
    config = StateReplayConfig(
        panel_path=Path(str(payload["panel_path"])),
        panel_sha256=str(payload["panel_sha256"]),
        shock_path=Path(str(payload["shock_path"])),
        shock_sha256=str(payload["shock_sha256"]),
        features=tuple(features),
        n_states=int(payload["n_states"]),
        minimum_training_events=int(payload["minimum_training_events"]),
        restarts=int(payload["restarts"]),
        max_iterations=int(payload["max_iterations"]),
        tolerance=float(payload["tolerance"]),
        variance_floor=float(payload["variance_floor"]),
        transition_prior=float(payload["transition_prior"]),
        random_seed=int(payload["random_seed"]),
        minimum_hard_count=int(payload["minimum_hard_count"]),
        minimum_weighted_ess=float(payload["minimum_weighted_ess"]),
        maximum_mean_entropy=float(payload["maximum_mean_entropy"]),
        minimum_restart_agreement=float(payload["minimum_restart_agreement"]),
    )
    if config.n_states != 2:
        raise StateReplayError("Replay v1 is deliberately restricted to two states.")
    if config.minimum_training_events < 20 or config.restarts < 2:
        raise StateReplayError("Replay requires at least 20 training events and two restarts.")
    if (
        config.max_iterations < 1
        or config.tolerance <= 0
        or config.variance_floor <= 0
        or config.transition_prior <= 0
    ):
        raise StateReplayError("Replay optimization settings must be positive.")
    if (
        config.minimum_hard_count < 0
        or config.minimum_weighted_ess < 0
        or config.maximum_mean_entropy < 0.0
        or not 0.0 <= config.minimum_restart_agreement <= 1.0
    ):
        raise StateReplayError("Replay screening thresholds are invalid.")
    for source_path, expected_hash in (
        (config.panel_path, config.panel_sha256),
        (config.shock_path, config.shock_sha256),
    ):
        if not source_path.is_file():
            raise StateReplayError(f"Replay source is missing: {source_path}")
        observed_hash = sha256_file(source_path)
        if observed_hash != expected_hash:
            raise StateReplayError(
                f"Replay source hash mismatch for {source_path}: {observed_hash}"
            )
    return config


def load_state_matrix(path: Path, features: tuple[str, ...]) -> StateMatrix:
    values_by_event: dict[str, dict[str, float]] = {}
    dates: dict[str, date] = {}
    seen_keys: set[tuple[str, str]] = set()
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            feature = row["feature_id"]
            if feature not in features:
                continue
            if row["admission_status"] != "ADMITTED":
                raise StateReplayError(f"Non-admitted feature requested: {feature}")
            event_id = row["event_id"]
            key = (event_id, feature)
            if key in seen_keys:
                raise StateReplayError(f"Duplicate event feature row: {event_id}, {feature}")
            seen_keys.add(key)
            event_date = date.fromisoformat(event_id.removeprefix("ecb-pr-"))
            dates[event_id] = event_date
            values_by_event.setdefault(event_id, {})
            missing = row["missing"]
            if missing not in {"True", "False"}:
                raise StateReplayError(f"Invalid missingness flag: {event_id}, {feature}")
            if missing == "False":
                if not row["value"]:
                    raise StateReplayError(
                        f"Observed event feature lacks value: {event_id}, {feature}"
                    )
                value = float(row["value"])
                if not np.isfinite(value):
                    raise StateReplayError(f"Non-finite event feature: {event_id}, {feature}")
                values_by_event[event_id][feature] = value
            elif row["value"]:
                raise StateReplayError(
                    f"Missing event feature carries value: {event_id}, {feature}"
                )
    event_ids = tuple(sorted(values_by_event, key=lambda item: dates[item]))
    missing_keys = {
        (event_id, feature)
        for event_id in event_ids
        for feature in features
        if (event_id, feature) not in seen_keys
    }
    if missing_keys:
        event_id, feature = sorted(missing_keys)[0]
        raise StateReplayError(f"Missing event feature row: {event_id}, {feature}")
    matrix = np.full((len(event_ids), len(features)), np.nan, dtype=np.float64)
    for row_index, event_id in enumerate(event_ids):
        for column, feature in enumerate(features):
            if feature in values_by_event[event_id]:
                matrix[row_index, column] = values_by_event[event_id][feature]
    if np.any(np.sum(np.isfinite(matrix), axis=0) < 2):
        raise StateReplayError("Each replay feature needs at least two observations.")
    return StateMatrix(event_ids, tuple(dates[item] for item in event_ids), matrix)


def _expanding_scale(train: FloatArray) -> tuple[FloatArray, FloatArray, FloatArray]:
    means = np.nanmean(train, axis=0)
    standard_deviations = np.nanstd(train, axis=0)
    standard_deviations = np.where(standard_deviations < 1e-8, 1.0, standard_deviations)
    return (train - means) / standard_deviations, means, standard_deviations


def _initial_slack_order(raw_means: FloatArray, features: tuple[str, ...]) -> tuple[int, ...]:
    unemployment = features.index("unemployment_rate")
    production = features.index("industrial_production_yoy")
    scores = raw_means[:, unemployment] - raw_means[:, production]
    return tuple(int(value) for value in np.argsort(scores))


def _restart_agreement(best: HMMFit, fits: tuple[HMMFit, ...]) -> float:
    best_labels = np.argmax(best.filtered_probabilities, axis=1)
    agreements: list[float] = []
    for fit in fits:
        order = alignment_order(best.parameters.means, fit.parameters.means)
        aligned = reorder_fit(fit, order)
        agreements.append(
            float(np.mean(best_labels == np.argmax(aligned.filtered_probabilities, axis=1)))
        )
    return min(agreements)


def _entropy(probabilities: FloatArray) -> float:
    clipped = np.clip(probabilities, 1e-15, 1.0)
    return float(-np.sum(clipped * np.log(clipped)))


def _effective_sample_size(weights: FloatArray) -> float:
    denominator = float(np.sum(weights**2))
    return float(np.sum(weights) ** 2 / denominator) if denominator > 0 else 0.0


def _require_float(value: Optional[float], field: str) -> float:
    if value is None:
        raise StateReplayError(f"Eligible replay row is missing {field}.")
    return value


def _chronological_blocks(count: int) -> NDArray[np.int64]:
    return np.asarray([min(2, index * 3 // count) for index in range(count)], dtype=np.int64)


def _load_shocks(path: Path) -> Mapping[str, float]:
    shocks: dict[str, float] = {}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            event_id = f"ecb-pr-{date.fromisoformat(row['date']).isoformat()}"
            shocks[event_id] = float(row["target"])
    return shocks


def _state_support(
    rows: tuple[ReplayRow, ...],
    matrix: StateMatrix,
    features: tuple[str, ...],
    shocks: Mapping[str, float],
) -> Mapping[str, Any]:
    retained = [row for row in rows if row.probability_state_0 is not None]
    probabilities = np.asarray(
        [[row.probability_state_0, row.probability_state_1] for row in retained],
        dtype=np.float64,
    )
    hard = np.argmax(probabilities, axis=1)
    entropies = np.asarray([row.entropy for row in retained], dtype=np.float64)
    event_lookup = {event_id: index for index, event_id in enumerate(matrix.event_ids)}
    raw = np.asarray([matrix.values[event_lookup[row.event_id]] for row in retained])
    blocks = _chronological_blocks(len(retained))
    shock_values = np.asarray([shocks[row.event_id] for row in retained], dtype=np.float64)
    state_records: dict[str, Any] = {}
    for state in range(probabilities.shape[1]):
        weights = probabilities[:, state]
        descriptors: dict[str, Optional[float]] = {}
        for column, feature in enumerate(features):
            observed = np.isfinite(raw[:, column])
            denominator = float(np.sum(weights[observed]))
            descriptors[feature] = (
                float(np.sum(weights[observed] * raw[observed, column]) / denominator)
                if denominator > 0
                else None
            )
        block_records: dict[str, Any] = {}
        for block in range(3):
            selection = blocks == block
            block_weights = weights[selection]
            block_records[str(block + 1)] = {
                "events": int(np.sum(selection)),
                "hard_count": int(np.sum(hard[selection] == state)),
                "weighted_count": float(np.sum(block_weights)),
                "weighted_ess": _effective_sample_size(block_weights),
            }
        state_records[str(state)] = {
            "hard_count": int(np.sum(hard == state)),
            "weighted_count": float(np.sum(weights)),
            "weighted_ess": _effective_sample_size(weights),
            "mean_probability": float(np.mean(weights)),
            "feature_weighted_means": descriptors,
            "shock_positive_weighted_count": float(np.sum(weights[shock_values > 0])),
            "shock_negative_weighted_count": float(np.sum(weights[shock_values < 0])),
            "shock_zero_weighted_count": float(np.sum(weights[shock_values == 0])),
            "shock_weighted_mean_absolute_dose": float(
                np.sum(weights * np.abs(shock_values)) / np.sum(weights)
            ),
            "blocks": block_records,
        }
    centered = probabilities[:, 1] - np.mean(probabilities[:, 1])
    contrast_information = float(np.sum(centered**2))
    leverage = (
        centered**2 / contrast_information if contrast_information > 0 else np.zeros_like(centered)
    )
    top_indices = np.argsort(leverage)[-10:][::-1]
    return {
        "eligible_replay_events": len(retained),
        "warmup_events": len(rows) - len(retained),
        "mean_entropy": float(np.mean(entropies)),
        "median_entropy": float(np.median(entropies)),
        "maximum_entropy": float(np.max(entropies)),
        "centered_probability_contrast_information": contrast_information,
        "states": state_records,
        "top_state_contrast_leverage_events": [
            {
                "event_id": retained[int(index)].event_id,
                "leverage": float(leverage[index]),
                "probability_state_1": float(probabilities[index, 1]),
            }
            for index in top_indices
        ],
    }


def run_state_replay(config: StateReplayConfig) -> StateReplayResult:
    matrix = load_state_matrix(config.panel_path, config.features)
    shocks = _load_shocks(config.shock_path)
    if any(event_id not in shocks for event_id in matrix.event_ids):
        raise StateReplayError("Shock support file does not cover every state-panel event.")
    rows: list[ReplayRow] = []
    previous_raw_means: Optional[FloatArray] = None
    transitions: list[FloatArray] = []
    for index, (event_id, event_date) in enumerate(zip(matrix.event_ids, matrix.event_dates)):
        if index < config.minimum_training_events:
            rows.append(
                ReplayRow(
                    event_id,
                    event_date.isoformat(),
                    index,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                )
            )
            continue
        train_scaled, means, standard_deviations = _expanding_scale(matrix.values[:index])
        current = (matrix.values[index] - means) / standard_deviations
        best, fits = fit_hmm_restarts(
            values=train_scaled,
            n_states=config.n_states,
            restarts=config.restarts,
            max_iterations=config.max_iterations,
            tolerance=config.tolerance,
            variance_floor=config.variance_floor,
            transition_prior=config.transition_prior,
            seed=config.random_seed + index * 100_003,
        )
        raw_means = best.parameters.means * standard_deviations + means
        if previous_raw_means is None:
            order = _initial_slack_order(raw_means, config.features)
        else:
            order = alignment_order(
                previous_raw_means / standard_deviations,
                raw_means / standard_deviations,
            )
        best = reorder_fit(best, order)
        raw_means = raw_means[np.asarray(order)]
        agreement = _restart_agreement(best, fits)
        posterior, hmm_score = filter_next(
            best.parameters, best.filtered_probabilities[-1], current
        )
        gaussian_score = diagonal_gaussian_log_score(train_scaled, current)
        entropy = _entropy(posterior)
        rows.append(
            ReplayRow(
                event_id=event_id,
                event_date=event_date.isoformat(),
                training_events=index,
                probability_state_0=float(posterior[0]),
                probability_state_1=float(posterior[1]),
                hard_state=int(np.argmax(posterior)),
                entropy=entropy,
                hmm_log_predictive=hmm_score,
                gaussian_log_predictive=gaussian_score,
                restart_hard_agreement=agreement,
                fit_converged=best.converged,
                fit_iterations=best.iterations,
                fit_seed=best.seed,
            )
        )
        previous_raw_means = raw_means
        transitions.append(best.parameters.transition)

    materialized = tuple(rows)
    assert_probability_integrity(materialized)
    eligible = [row for row in materialized if row.probability_state_0 is not None]
    if not eligible:
        raise StateReplayError("Replay produced no eligible event probabilities.")
    support = _state_support(materialized, matrix, config.features, shocks)
    hard_counts = [support["states"][str(state)]["hard_count"] for state in range(2)]
    weighted_ess = [support["states"][str(state)]["weighted_ess"] for state in range(2)]
    score_gain = float(
        sum(
            _require_float(row.hmm_log_predictive, "hmm_log_predictive")
            - _require_float(row.gaussian_log_predictive, "gaussian_log_predictive")
            for row in eligible
        )
    )
    restart_agreements = [
        _require_float(row.restart_hard_agreement, "restart_hard_agreement") for row in eligible
    ]
    mean_agreement = float(np.mean(restart_agreements))
    minimum_agreement = min(restart_agreements)
    gates = {
        "hmm_beats_state_independent_gaussian_prequentially": score_gain > 0,
        "minimum_hard_count": min(hard_counts) >= config.minimum_hard_count,
        "minimum_weighted_ess": min(weighted_ess) >= config.minimum_weighted_ess,
        "maximum_mean_entropy": support["mean_entropy"] <= config.maximum_mean_entropy,
        "minimum_restart_agreement": minimum_agreement >= config.minimum_restart_agreement,
        "all_selected_fits_converged": all(bool(row.fit_converged) for row in eligible),
    }
    audit: dict[str, Any] = {
        "evidence_status": "REAL_DATA_OUTCOME_BLIND_STATE_BENCHMARK",
        "estimator_status": "BENCHMARK_NOT_FINAL_PRIMARY",
        "events": len(materialized),
        "features": list(config.features),
        "minimum_training_events": config.minimum_training_events,
        "prequential_log_score_gain_vs_single_gaussian": score_gain,
        "mean_restart_hard_agreement": mean_agreement,
        "minimum_restart_hard_agreement": minimum_agreement,
        "restart_agreement_threshold": config.minimum_restart_agreement,
        "events_below_restart_agreement_threshold": [
            row.event_id
            for row, agreement in zip(eligible, restart_agreements)
            if agreement < config.minimum_restart_agreement
        ],
        "mean_transition_matrix": np.mean(np.stack(transitions), axis=0).tolist(),
        "support": support,
        "screening_gates": gates,
        "screening_pass": all(gates.values()),
        "outcomes_accessed": False,
        "shock_used_for_model_selection": False,
        "known_limitation": (
            "Event-indexed replay treats irregular meeting intervals as one transition; "
            "monthly-calendar challengers remain required by Blueprint V2."
        ),
    }
    return StateReplayResult(materialized, audit)


def write_replay_csv(rows: tuple[ReplayRow, ...], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(ReplayRow.__dataclass_fields__))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)
    temporary.replace(path)


def assert_probability_integrity(rows: tuple[ReplayRow, ...]) -> None:
    for row in rows:
        if row.probability_state_0 is None:
            if row.probability_state_1 is not None or row.hard_state is not None:
                raise StateReplayError("Warm-up rows must have fully missing state outputs.")
            continue
        if row.probability_state_1 is None:
            raise StateReplayError("State probability pair is incomplete.")
        total = row.probability_state_0 + row.probability_state_1
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-10):
            raise StateReplayError(f"State probabilities do not sum to one: {row.event_id}")
