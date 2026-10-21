"""Deterministic Stage-A calibration transaction for Run 031.

This module consumes origin-level geometry records produced by the frozen
scenario engine.  It does not read panel files, evaluation labels, evaluation
metrics, or transmission outcomes.  Keeping the selection transaction
separate from scenario fitting makes the information firewall testable.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from shockbridge_state_risk.state.calibration_orchestration import (
    CalibrationOrchestrationError,
    expected_calibration_months,
)
from shockbridge_state_risk.state.reliability_execution_harness import (
    ThresholdCandidate,
    match_calibration_participation,
    select_calibration_threshold,
)

BoolArray = NDArray[np.bool_]

SCORE_CUTOFFS = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30)
CHANNEL_CUTOFFS = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30)
ORIENTATION_FLOORS = (0.50, 0.60, 0.70, 0.80)
B3_LAMBDA_MULTIPLIERS = (0.5, 1.0, 2.0)


class StageACalibrationError(CalibrationOrchestrationError):
    """Raised when the one-time calibration transaction is not executable."""


@dataclass(frozen=True)
class GeometryRecord:
    """Threshold-free geometry for one origin and one registered method."""

    origin_month: str
    score_distance: float
    channel_distance: float
    orientation_capture: float
    analytic_scenario_count: int
    nondegenerate: bool


@dataclass(frozen=True)
class CalibrationCandidate:
    """A frozen threshold candidate and its complete 60-origin decisions."""

    candidate: ThresholdCandidate
    authorization: BoolArray
    authorization_sha256: str
    authorized_failure_rate: float


@dataclass(frozen=True)
class MethodCalibration:
    """Selected and calibration-participation-matched rules for one method."""

    method_id: str
    selected: CalibrationCandidate
    matched: CalibrationCandidate
    candidates: tuple[CalibrationCandidate, ...]
    lambda_multiplier: float | None = None


@dataclass(frozen=True)
class ControlGate:
    """Stage-A negative-control result under calibration-only analogues."""

    passed: bool
    nc1_degraded: bool
    nc2_degraded: bool
    nc3_jointly_reproduced: bool
    failures: tuple[str, ...]


@dataclass(frozen=True)
class StageATransaction:
    """Complete deterministic selections produced from sixty calibration origins."""

    primary: MethodCalibration
    B1: MethodCalibration
    B2: MethodCalibration
    B3: MethodCalibration
    NC1: MethodCalibration
    NC2: MethodCalibration
    NC3: MethodCalibration
    primary_success: bool
    primary_success_failures: tuple[str, ...]
    control_gate: ControlGate


def _canonical_json(payload: object) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def threshold_grid() -> tuple[tuple[float, float, float], ...]:
    """Return the exact lexical three-dimensional grid of 144 candidates."""
    return tuple(
        (score, channel, orientation)
        for score in SCORE_CUTOFFS
        for channel in CHANNEL_CUTOFFS
        for orientation in ORIENTATION_FLOORS
    )


def _validate_geometry(
    records: Sequence[GeometryRecord], method_id: str
) -> tuple[GeometryRecord, ...]:
    values = tuple(records)
    months = tuple(record.origin_month for record in values)
    if months != expected_calibration_months():
        raise StageACalibrationError(f"{method_id} must contain the exact 60 calibration origins")
    for record in values:
        if (
            not np.isfinite(record.score_distance)
            or not np.isfinite(record.channel_distance)
            or not np.isfinite(record.orientation_capture)
            or record.score_distance < 0.0
            or record.channel_distance < 0.0
            or not 0.0 <= record.orientation_capture <= 1.0
            or type(record.analytic_scenario_count) is not int
            or record.analytic_scenario_count < 0
            or type(record.nondegenerate) is not bool
        ):
            raise StageACalibrationError(f"{method_id} contains invalid geometry")
    return values


def _validate_labels(labels: object) -> BoolArray:
    array = np.asarray(labels)
    if array.dtype != np.bool_ or array.shape != (60,):
        raise StageACalibrationError("Stage A requires exactly 60 Boolean matured labels")
    return np.asarray(array, dtype=np.bool_)


def authorization_vector(
    records: Sequence[GeometryRecord],
    *,
    score_cutoff: float,
    channel_cutoff: float,
    orientation_floor: float,
    minimum_scenarios: int,
) -> BoolArray:
    """Apply one frozen threshold triple without consulting labels."""
    values = _validate_geometry(records, "authorization input")
    if (
        score_cutoff not in SCORE_CUTOFFS
        or channel_cutoff not in CHANNEL_CUTOFFS
        or orientation_floor not in ORIENTATION_FLOORS
        or type(minimum_scenarios) is not int
        or minimum_scenarios < 1
    ):
        raise StageACalibrationError("Authorization thresholds are outside the frozen grid")
    return np.asarray(
        [
            record.nondegenerate
            and record.analytic_scenario_count >= minimum_scenarios
            and record.score_distance <= score_cutoff
            and record.channel_distance <= channel_cutoff
            and record.orientation_capture >= orientation_floor
            for record in values
        ],
        dtype=np.bool_,
    )


def _decision_metrics(authorization: BoolArray, labels: BoolArray) -> tuple[float, float, float]:
    participation = float(np.mean(authorization))
    loss = float(np.mean((authorization & labels).astype(float) + 0.25 * (~authorization)))
    failure_rate = float(np.mean(labels[authorization])) if np.any(authorization) else 1.0
    return participation, loss, failure_rate


def _vector_hash(values: BoolArray) -> str:
    payload = {
        "dtype": "bool",
        "length": int(values.size),
        "values": values.astype(int).tolist(),
    }
    return _sha256(_canonical_json(payload))


def build_candidates(
    method_id: str,
    records: Sequence[GeometryRecord],
    labels: object,
    *,
    minimum_scenarios: int,
    candidate_prefix: str | None = None,
) -> tuple[CalibrationCandidate, ...]:
    """Materialize all 144 calibration-only candidate decisions."""
    values = _validate_geometry(records, method_id)
    outcome = _validate_labels(labels)
    prefix = candidate_prefix or method_id
    candidates: list[CalibrationCandidate] = []
    for score, channel, orientation in threshold_grid():
        actions = authorization_vector(
            values,
            score_cutoff=score,
            channel_cutoff=channel,
            orientation_floor=orientation,
            minimum_scenarios=minimum_scenarios,
        )
        participation, loss, failure_rate = _decision_metrics(actions, outcome)
        identifier = f"{prefix}__s{score:.2f}__c{channel:.2f}__o{orientation:.2f}"
        candidates.append(
            CalibrationCandidate(
                ThresholdCandidate(
                    identifier,
                    loss,
                    participation,
                    score,
                    channel,
                    orientation,
                ),
                actions,
                _vector_hash(actions),
                failure_rate,
            )
        )
    if len(candidates) != 144 or len({item.candidate.candidate_id for item in candidates}) != 144:
        raise StageACalibrationError("Candidate grid is incomplete or nonunique")
    return tuple(candidates)


def _lookup_candidate(
    candidates: Sequence[CalibrationCandidate], selected: ThresholdCandidate
) -> CalibrationCandidate:
    matches = [item for item in candidates if item.candidate.candidate_id == selected.candidate_id]
    if len(matches) != 1:
        raise StageACalibrationError("Selected candidate is absent or duplicated")
    return matches[0]


def calibrate_method(
    method_id: str,
    records: Sequence[GeometryRecord],
    labels: object,
    *,
    minimum_scenarios: int,
    participation_target: float | None = None,
    candidate_prefix: str | None = None,
    lambda_multiplier: float | None = None,
) -> MethodCalibration:
    """Select and participation-match one registered method on calibration only."""
    candidates = build_candidates(
        method_id,
        records,
        labels,
        minimum_scenarios=minimum_scenarios,
        candidate_prefix=candidate_prefix,
    )
    threshold_candidates = tuple(item.candidate for item in candidates)
    selected = _lookup_candidate(candidates, select_calibration_threshold(threshold_candidates))
    target = (
        selected.candidate.participation if participation_target is None else participation_target
    )
    matched = _lookup_candidate(
        candidates, match_calibration_participation(threshold_candidates, target)
    )
    return MethodCalibration(
        method_id,
        selected,
        matched,
        candidates,
        lambda_multiplier,
    )


def calibrate_b3(
    records_by_lambda: Mapping[float, Sequence[GeometryRecord]],
    labels: object,
    *,
    participation_target: float,
) -> MethodCalibration:
    """Select B3 lambda and thresholds jointly with lower-lambda final tie-break."""
    if set(records_by_lambda) != set(B3_LAMBDA_MULTIPLIERS):
        raise StageACalibrationError("B3 must contain all three frozen lambda multipliers")
    all_candidates: list[tuple[float, CalibrationCandidate]] = []
    per_lambda: dict[float, tuple[CalibrationCandidate, ...]] = {}
    for multiplier in B3_LAMBDA_MULTIPLIERS:
        candidates = build_candidates(
            "B3",
            records_by_lambda[multiplier],
            labels,
            minimum_scenarios=1,
            candidate_prefix=f"B3__lambda{multiplier:.1f}",
        )
        per_lambda[multiplier] = candidates
        all_candidates.extend((multiplier, item) for item in candidates)
    multiplier, selected = min(
        all_candidates,
        key=lambda item: (
            item[1].candidate.loss,
            -item[1].candidate.participation,
            item[1].candidate.score_cutoff,
            item[1].candidate.channel_cutoff,
            -item[1].candidate.orientation_floor,
            item[0],
            item[1].candidate.candidate_id,
        ),
    )
    selected_lambda_candidates = per_lambda[multiplier]
    matched_threshold = match_calibration_participation(
        tuple(item.candidate for item in selected_lambda_candidates), participation_target
    )
    matched = _lookup_candidate(selected_lambda_candidates, matched_threshold)
    return MethodCalibration(
        "B3",
        selected,
        matched,
        tuple(item for _, item in all_candidates),
        multiplier,
    )


def _same_threshold_and_loss(left: CalibrationCandidate, right: CalibrationCandidate) -> bool:
    a, b = left.candidate, right.candidate
    return (
        a.score_cutoff == b.score_cutoff
        and a.channel_cutoff == b.channel_cutoff
        and a.orientation_floor == b.orientation_floor
        and a.loss == b.loss
    )


def _calibration_analogue_failures(
    method: MethodCalibration,
    records: Sequence[GeometryRecord],
    B1: MethodCalibration,
) -> tuple[str, ...]:
    failures: list[str] = []
    selected = method.selected
    if selected.candidate.participation < 0.10:
        failures.append("participation_below_0_10")
    counts = np.asarray(
        [record.analytic_scenario_count for record in _validate_geometry(records, method.method_id)]
    )
    if np.any(selected.authorization & (counts < 2)) or not np.any(
        selected.authorization & (counts >= 2)
    ):
        failures.append("authorized_origin_has_fewer_than_two_scenarios")
    if selected.candidate.loss >= B1.selected.candidate.loss:
        failures.append("decision_loss_not_strictly_lower_than_B1")
    if selected.authorized_failure_rate > B1.matched.authorized_failure_rate:
        failures.append("failure_rate_higher_than_B1_at_matched_participation")
    return tuple(failures)


def run_stage_a_transaction(
    *,
    labels: object,
    primary: Sequence[GeometryRecord],
    B1: Sequence[GeometryRecord],
    B2: Sequence[GeometryRecord],
    B3: Mapping[float, Sequence[GeometryRecord]],
    NC1: Sequence[GeometryRecord],
    NC2: Sequence[GeometryRecord],
    NC3_labels: object,
) -> StageATransaction:
    """Execute the frozen calibration transaction without evaluation access."""
    outcome = _validate_labels(labels)
    permuted = _validate_labels(NC3_labels)
    primary_fit = calibrate_method("primary", primary, outcome, minimum_scenarios=2)
    target = primary_fit.selected.candidate.participation
    b1_fit = calibrate_method("B1", B1, outcome, minimum_scenarios=1, participation_target=target)
    b2_fit = calibrate_method("B2", B2, outcome, minimum_scenarios=2, participation_target=target)
    b3_fit = calibrate_b3(B3, outcome, participation_target=target)
    nc1_fit = calibrate_method("NC1", NC1, outcome, minimum_scenarios=2)
    nc2_fit = calibrate_method("NC2", NC2, outcome, minimum_scenarios=2)
    nc3_fit = calibrate_method("NC3", primary, permuted, minimum_scenarios=2)

    selected = primary_fit.selected
    primary_failures = _calibration_analogue_failures(primary_fit, primary, b1_fit)
    primary_success = not primary_failures
    nc1_failures = _calibration_analogue_failures(nc1_fit, NC1, b1_fit)
    nc2_failures = _calibration_analogue_failures(nc2_fit, NC2, b1_fit)
    nc1_degraded = nc1_fit.selected.candidate.loss >= selected.candidate.loss and bool(nc1_failures)
    nc2_degraded = nc2_fit.selected.candidate.loss >= selected.candidate.loss and bool(nc2_failures)
    nc3_reproduced = _same_threshold_and_loss(selected, nc3_fit.selected)
    control_failures: list[str] = []
    if not (nc1_degraded or nc2_degraded):
        control_failures.append("neither_NC1_nor_NC2_degraded")
    if nc3_reproduced:
        control_failures.append("NC3_reproduced_threshold_and_loss")
    control_gate = ControlGate(
        not control_failures,
        nc1_degraded,
        nc2_degraded,
        nc3_reproduced,
        tuple(control_failures),
    )
    return StageATransaction(
        primary_fit,
        b1_fit,
        b2_fit,
        b3_fit,
        nc1_fit,
        nc2_fit,
        nc3_fit,
        primary_success,
        primary_failures,
        control_gate,
    )


def transaction_summary(transaction: StageATransaction) -> Mapping[str, Any]:
    """Return the lock-ready calibration summary without origin values or labels."""
    methods = {
        name: getattr(transaction, name)
        for name in ("primary", "B1", "B2", "B3", "NC1", "NC2", "NC3")
    }
    return {
        "candidate_grid_count": 144,
        "methods": {
            name: {
                "selected_candidate_id": value.selected.candidate.candidate_id,
                "selected_authorization_sha256": value.selected.authorization_sha256,
                "selected_loss": value.selected.candidate.loss,
                "selected_participation": value.selected.candidate.participation,
                "selected_authorized_failure_rate": value.selected.authorized_failure_rate,
                "matched_candidate_id": value.matched.candidate.candidate_id,
                "matched_authorization_sha256": value.matched.authorization_sha256,
                "lambda_multiplier": value.lambda_multiplier,
            }
            for name, value in methods.items()
        },
        "primary_success": transaction.primary_success,
        "primary_success_failures": list(transaction.primary_success_failures),
        "control_gate_passed": transaction.control_gate.passed,
        "control_gate_failures": list(transaction.control_gate.failures),
    }
