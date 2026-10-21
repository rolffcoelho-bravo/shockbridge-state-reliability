"""Prospectively frozen Stage-A orchestration primitives.

The functions in this module implement the nine Run 029 composition
resolutions.  They are deliberately independent of file retrieval and never
import evaluation, transmission, or outcome modules.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from numpy.typing import NDArray

from shockbridge_state_risk.state.hmm import FloatArray
from shockbridge_state_risk.state.reliability_engine import standardize_observed_matrix
from shockbridge_state_risk.state.reliability_execution_harness import (
    ReliabilityExecutionHarnessError,
    RobustPCAFit,
    SeriesRedundancyMetadata,
    resolve_near_duplicates,
)

BoolArray = NDArray[np.bool_]


class CalibrationOrchestrationError(ValueError):
    """Raised when the approved Stage-A orchestration cannot be applied exactly."""


PIPELINE_OPERATIONS = (
    "verify_exact_bound_panel_bytes_and_coordinates",
    "build_origin_by_manifest_series_path",
    "apply_registered_or_plus_one_month_timing_policy",
    "apply_full_panel_or_leave_one_available_channel_out_family_rule",
    "slice_expanding_and_exact_rolling_120_histories",
    "independently_apply_count_coverage_and_nonzero_scale_eligibility",
    "collapse_exact_equal_value_and_missingness_paths_within_channel",
    "standardize_using_observed_moments_within_each_history",
    "build_within_channel_absolute_correlation_graph",
    "select_one_representative_per_connected_component",
    "recompute_signed_equal_total_channel_weights",
    "fit_each_history_and_construct_common_space_geometry",
    "hash_and_deduplicate_complete_two_history_scenario_identity",
    "map_every_provenance_label_to_its_analytic_representative",
)

TIMING_STRENGTH = {"A_REPLAY_ELIGIBLE": 0, "B_RELEASE_LAG_ELIGIBLE": 1}
REVISION_EXPOSURE = {
    "archived_policy_concept_vintages": 0,
    "dated_effective_rate_with_history_timestamp": 1,
    "dated_curve_estimate_with_history_timestamp": 2,
    "nonrevisable_dated_reference_rate_assumption_to_be_audited": 3,
    "current_history_shifted_to_verified_release_calendar": 4,
}
EVALUATION_FORBIDDEN_TOKENS = (
    "metric",
    "label",
    "loss",
    "authorization",
    "estimator",
    "geometry",
    "comparator",
    "result",
)
LOCK_SELECTED_SETTINGS = {
    "primary_threshold",
    "B1_cutoff_and_matched_participation_cutoff",
    "B2_cutoff_and_matched_participation_cutoff",
    "B3_lambda_cutoff_and_matched_participation_cutoff",
    "NC1_NC2_NC3_frozen_settings",
}
LOCK_CALIBRATION_METRICS = {
    "candidate_grid_count",
    "participation",
    "decision_loss",
    "future_failure_prevalence",
    "authorized_future_failure_rate",
    "nondegenerate_scenario_count_distribution",
    "comparator_metrics",
    "negative_control_metrics",
}
LEDGER_FIELDS = {
    "origin_month",
    "matured_future_failure_label",
    "analytic_scenario_count",
    "provenance_to_analytic_mapping",
    "scenario_representatives_and_failure_reasons",
    "envelope_statistics",
    "candidate_authorization_vector_hash",
    "B1_B2_B3_candidate_authorization_vector_hashes",
    "negative_control_candidate_vector_hashes",
    "selected_primary_and_comparator_decisions",
}


@dataclass(frozen=True)
class SeriesDescriptor:
    series_id: str
    channel: str
    timing_class: str
    revision_exposure: str
    first_usable_month: str
    manifest_order: int
    sign: int


@dataclass(frozen=True)
class PreparedHistory:
    retained_series_ids: tuple[str, ...]
    eligibility_mask: BoolArray
    standardized: FloatArray
    observed: BoolArray
    series_channels: tuple[str, ...]
    signs: tuple[int, ...]
    exact_components: tuple[tuple[str, ...], ...]
    near_components: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class ScenarioIdentity:
    full_scenario_id: str
    payload: Mapping[str, Any]
    sha256: str


@dataclass(frozen=True)
class B2Member:
    analytic_class_id: str
    standardized_anchor_scalar: FloatArray
    channel_projector: FloatArray
    anchor_capture: float


@dataclass(frozen=True)
class B2HistoryCombination:
    analytic_class_ids: tuple[str, ...]
    standardized_anchor_scalar: FloatArray
    channel_operator: FloatArray
    mean_anchor_capture: float


@dataclass(frozen=True)
class CalibrationAnalogue:
    passed: bool
    participation: float
    decision_loss: float
    authorized_failure_rate: float
    nondegenerate_authorized_origins: int
    failures: tuple[str, ...]


def _canonical_json(payload: object) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _valid_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def validate_run029_approval(approval_path: Path, proposal_path: Path) -> str:
    """Verify exact owner approval of the unchanged nine-resolution amendment."""
    approval = yaml.safe_load(approval_path.read_text(encoding="utf-8"))
    if not isinstance(approval, dict) or approval.get("status") != (
        "APPROVED_EXACT_AMENDMENT_FOR_IMPLEMENTATION_HOSTILE_TESTS_AND_CONDITIONAL_STAGE_A"
    ):
        raise CalibrationOrchestrationError("Run 029 orchestration amendment is not approved")
    bound = approval.get("approved_amendment")
    scope = approval.get("approval_scope")
    prohibited = approval.get("still_prohibited")
    raw = proposal_path.read_bytes()
    digest = _sha256(raw)
    if not isinstance(bound, dict) or (
        bound.get("bytes") != len(raw)
        or bound.get("sha256") != digest
        or bound.get("incorporated_by_reference_without_modification") is not True
    ):
        raise CalibrationOrchestrationError("Approved Run 029 amendment byte identity changed")
    if not isinstance(scope, dict) or any(
        scope.get(key) is not True
        for key in (
            "implement_all_nine_orchestration_resolutions",
            "hostile_software_tests_with_fixture_values",
            "official_stage_A_calibration_after_all_acceptance_tests_pass",
        )
    ):
        raise CalibrationOrchestrationError("Run 030 implementation scope is incomplete")
    if (
        not isinstance(prohibited, dict)
        or not prohibited
        or any(value is not True for value in prohibited.values())
    ):
        raise CalibrationOrchestrationError("Run 030 empirical firewall is incomplete")
    return digest


def validate_pipeline_trace(trace: Sequence[str]) -> None:
    """Reject every omission, addition, or permutation of the frozen pipeline."""
    if tuple(trace) != PIPELINE_OPERATIONS:
        raise CalibrationOrchestrationError("Scenario operations violate the frozen order")


def encode_month(month: str) -> int:
    """Encode YYYY-MM as year * 12 + month - 1."""
    try:
        year_text, month_text = month.split("-")
        year, value = int(year_text), int(month_text)
    except (AttributeError, TypeError, ValueError) as error:
        raise CalibrationOrchestrationError("Month must be YYYY-MM") from error
    if len(year_text) != 4 or len(month_text) != 2 or year < 1 or not 1 <= value <= 12:
        raise CalibrationOrchestrationError("Month must be YYYY-MM")
    return year * 12 + value - 1


def _descriptor_priority(descriptor: SeriesDescriptor, missingness: float) -> tuple[Any, ...]:
    try:
        timing = TIMING_STRENGTH[descriptor.timing_class]
        revision = REVISION_EXPOSURE[descriptor.revision_exposure]
    except KeyError as error:
        raise CalibrationOrchestrationError("Unregistered categorical tie-break value") from error
    if descriptor.sign not in (-1, 1) or not np.isfinite(missingness):
        raise CalibrationOrchestrationError("Series sign or missingness is invalid")
    return (
        timing,
        revision,
        encode_month(descriptor.first_usable_month),
        missingness,
        descriptor.manifest_order,
        descriptor.series_id,
    )


def _exact_components(
    values: FloatArray, descriptors: Sequence[SeriesDescriptor]
) -> tuple[tuple[int, ...], ...]:
    groups: dict[tuple[str, str], list[int]] = {}
    for index, descriptor in enumerate(descriptors):
        observed = np.isfinite(values[:, index])
        payload = (
            observed.astype(np.uint8).tobytes()
            + np.asarray(values[observed, index], dtype="<f8").tobytes()
        )
        groups.setdefault((descriptor.channel, _sha256(payload)), []).append(index)
    return tuple(tuple(indices) for _, indices in sorted(groups.items()))


def prepare_history(
    values: object,
    descriptors: Sequence[SeriesDescriptor],
    *,
    minimum_coverage: float = 0.80,
    minimum_observations: int = 24,
) -> PreparedHistory:
    """Apply OG-03 eligibility, exact-duplicate, and near-duplicate rules."""
    matrix = np.asarray(values, dtype=np.float64)
    records = tuple(descriptors)
    if matrix.ndim != 2 or matrix.shape[0] < 2 or matrix.shape[1] != len(records):
        raise CalibrationOrchestrationError("History matrix and descriptors do not align")
    if len({item.series_id for item in records}) != len(records) or np.any(np.isinf(matrix)):
        raise CalibrationOrchestrationError("History series must be unique and finite-or-missing")
    observed = np.isfinite(matrix)
    counts = observed.sum(axis=0)
    coverage = counts / matrix.shape[0]
    eligible = (counts >= minimum_observations) & (coverage >= minimum_coverage)
    for index in np.flatnonzero(eligible):
        values_observed = matrix[observed[:, index], index]
        eligible[index] = bool(
            values_observed.size > 1 and np.std(values_observed, ddof=1) > np.finfo(np.float64).eps
        )
    if not np.any(eligible):
        raise CalibrationOrchestrationError("No history-specific series passes eligibility")
    eligible_indices = np.flatnonzero(eligible)
    eligible_matrix = matrix[:, eligible_indices]
    eligible_records = tuple(records[index] for index in eligible_indices)
    exact = _exact_components(eligible_matrix, eligible_records)
    exact_retained: list[int] = []
    for component in exact:
        representative = min(
            component,
            key=lambda index: _descriptor_priority(
                eligible_records[index],
                1.0 - float(np.mean(np.isfinite(eligible_matrix[:, index]))),
            ),
        )
        exact_retained.append(representative)
    collapsed = eligible_matrix[:, exact_retained]
    collapsed_records = tuple(eligible_records[index] for index in exact_retained)
    standardized = standardize_observed_matrix(
        collapsed,
        minimum_coverage=minimum_coverage,
        minimum_observations=minimum_observations,
    )
    old_style_metadata = tuple(
        SeriesRedundancyMetadata(
            item.series_id,
            item.channel,
            -TIMING_STRENGTH.get(item.timing_class, 10),
            REVISION_EXPOSURE.get(item.revision_exposure, 10),
            encode_month(item.first_usable_month),
            1.0 - float(np.mean(standardized.observed[:, index])),
            item.manifest_order,
        )
        for index, item in enumerate(collapsed_records)
    )
    if any(item.timing_class not in TIMING_STRENGTH for item in collapsed_records) or any(
        item.revision_exposure not in REVISION_EXPOSURE for item in collapsed_records
    ):
        raise CalibrationOrchestrationError("Unregistered categorical tie-break value")
    try:
        redundancy = resolve_near_duplicates(standardized.values, old_style_metadata)
    except ReliabilityExecutionHarnessError as error:
        raise CalibrationOrchestrationError(str(error)) from error
    retained = redundancy.retained_indices
    final_records = tuple(collapsed_records[index] for index in retained)
    return PreparedHistory(
        retained_series_ids=tuple(item.series_id for item in final_records),
        eligibility_mask=np.asarray(eligible, dtype=np.bool_),
        standardized=np.asarray(standardized.values[:, retained], dtype=np.float64),
        observed=np.asarray(standardized.observed[:, retained], dtype=np.bool_),
        series_channels=tuple(item.channel for item in final_records),
        signs=tuple(item.sign for item in final_records),
        exact_components=tuple(
            tuple(eligible_records[index].series_id for index in component) for component in exact
        ),
        near_components=redundancy.components,
    )


def canonical_matrix_hash(values: object) -> str:
    """Hash shape, ordered missingness, and observed little-endian float64 values."""
    matrix = np.asarray(values, dtype=np.float64)
    if matrix.ndim != 2 or np.any(np.isinf(matrix)):
        raise CalibrationOrchestrationError("Canonical matrix must be two-dimensional")
    observed = np.isfinite(matrix)
    payload = (
        _canonical_json({"shape": list(matrix.shape), "dtype": "float64"})
        + observed.astype(np.uint8).tobytes()
        + np.asarray(matrix[observed], dtype="<f8").tobytes()
    )
    return _sha256(payload)


def scenario_identity(
    full_scenario_id: str,
    expanding: PreparedHistory,
    rolling: PreparedHistory,
) -> ScenarioIdentity:
    """Hash the complete two-history identity while permitting unequal columns."""
    if (
        not full_scenario_id
        or expanding.standardized.shape[0] < 120
        or (rolling.standardized.shape[0] != 120)
    ):
        raise CalibrationOrchestrationError("Scenario identity histories are invalid")
    payload = {
        "scenario_id": full_scenario_id,
        "expanding_ordered_retained_series_ids": list(expanding.retained_series_ids),
        "expanding_eligibility_mask": expanding.eligibility_mask.astype(int).tolist(),
        "expanding_canonical_standardized_matrix_hash": canonical_matrix_hash(
            expanding.standardized
        ),
        "rolling_ordered_retained_series_ids": list(rolling.retained_series_ids),
        "rolling_eligibility_mask": rolling.eligibility_mask.astype(int).tolist(),
        "rolling_canonical_standardized_matrix_hash": canonical_matrix_hash(rolling.standardized),
    }
    return ScenarioIdentity(full_scenario_id, payload, _sha256(_canonical_json(payload)))


def deduplicate_scenario_identities(
    identities: Sequence[ScenarioIdentity],
) -> tuple[dict[str, ScenarioIdentity], dict[str, str]]:
    """Choose the lexical provenance representative for each analytic identity."""
    grouped: dict[str, list[ScenarioIdentity]] = {}
    for identity in identities:
        grouped.setdefault(identity.sha256, []).append(identity)
    representatives: dict[str, ScenarioIdentity] = {}
    mapping: dict[str, str] = {}
    for digest, members in sorted(grouped.items()):
        representative = min(members, key=lambda item: item.full_scenario_id)
        representatives[digest] = representative
        for member in members:
            mapping[member.full_scenario_id] = representative.full_scenario_id
    return representatives, mapping


def combine_b2_history(members: Sequence[B2Member]) -> B2HistoryCombination:
    """Average unique analytic classes with zero provenance-multiplicity weight."""
    unique: dict[str, B2Member] = {}
    for member in members:
        existing = unique.get(member.analytic_class_id)
        if existing is not None:
            if (
                canonical_matrix_hash(existing.standardized_anchor_scalar[:, None])
                != canonical_matrix_hash(member.standardized_anchor_scalar[:, None])
                or canonical_matrix_hash(existing.channel_projector)
                != canonical_matrix_hash(member.channel_projector)
                or existing.anchor_capture != member.anchor_capture
            ):
                raise CalibrationOrchestrationError("Analytic-class duplicate is inconsistent")
        else:
            unique[member.analytic_class_id] = member
    ordered = tuple(unique[key] for key in sorted(unique))
    if len(ordered) < 2:
        raise CalibrationOrchestrationError("B2 needs at least two unique analytic classes")
    scalar_shapes = {np.asarray(item.standardized_anchor_scalar).shape for item in ordered}
    operator_shapes = {np.asarray(item.channel_projector).shape for item in ordered}
    if len(scalar_shapes) != 1 or len(operator_shapes) != 1:
        raise CalibrationOrchestrationError("B2 members do not share common spaces")
    scalar = np.mean(np.stack([item.standardized_anchor_scalar for item in ordered]), axis=0)
    operator = np.mean(np.stack([item.channel_projector for item in ordered]), axis=0)
    capture = float(np.mean([item.anchor_capture for item in ordered]))
    if np.any(~np.isfinite(scalar)) or np.any(~np.isfinite(operator)) or not np.isfinite(capture):
        raise CalibrationOrchestrationError("B2 combination is nonfinite")
    return B2HistoryCombination(
        tuple(item.analytic_class_id for item in ordered),
        np.asarray(scalar, dtype=np.float64),
        np.asarray(operator, dtype=np.float64),
        capture,
    )


def fit_projected_observed_stable_pcp(
    values: object,
    *,
    lambda_multiplier: float = 1.0,
    tolerance: float = 1e-8,
    maximum_iterations: int = 2000,
) -> RobustPCAFit:
    """Fit OG-05 PCP without treating unobserved cells as observed zeros."""
    matrix = np.asarray(values, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] < 2 or matrix.shape[1] < 1:
        raise CalibrationOrchestrationError("Projected PCP input must be a matrix")
    observed = np.isfinite(matrix)
    data = np.where(observed, matrix, 0.0)
    if (
        np.any(np.isinf(matrix))
        or not np.any(observed)
        or lambda_multiplier not in (0.5, 1.0, 2.0)
        or not np.isfinite(tolerance)
        or tolerance <= 0.0
        or type(maximum_iterations) is not int
        or maximum_iterations < 1
    ):
        raise CalibrationOrchestrationError("Projected PCP controls are invalid")
    lam = lambda_multiplier / np.sqrt(max(matrix.shape))
    epsilon = float(np.finfo(np.float64).eps)
    spectral = float(np.linalg.norm(data, ord=2))
    scaled_max = float(np.max(np.abs(data))) / lam
    dual = data / max(spectral, scaled_max, epsilon)
    low_rank = np.zeros_like(data)
    sparse = np.zeros_like(data)
    mu = 1.25 / max(spectral, epsilon)
    observed_norm = max(float(np.linalg.norm(data[observed])), epsilon)
    error = float("inf")
    for iteration in range(1, maximum_iterations + 1):
        projected_update = np.where(observed, data - sparse + dual / mu, low_rank)
        left, singular, right = np.linalg.svd(projected_update, full_matrices=False)
        shrunk = np.maximum(singular - 1.0 / mu, 0.0)
        low_rank = (left * shrunk) @ right
        residual_for_sparse = data - low_rank + dual / mu
        sparse = np.where(
            observed,
            np.sign(residual_for_sparse) * np.maximum(np.abs(residual_for_sparse) - lam / mu, 0.0),
            0.0,
        )
        primal = np.where(observed, data - low_rank - sparse, 0.0)
        error = float(np.linalg.norm(primal[observed]) / observed_norm)
        if error <= tolerance:
            return RobustPCAFit(
                low_rank=np.asarray(low_rank, dtype=np.float64),
                sparse=np.asarray(sparse, dtype=np.float64),
                iterations=iteration,
                converged=True,
                relative_primal_error=error,
            )
        dual += mu * primal
        mu *= 1.5
    raise CalibrationOrchestrationError("Projected PCP did not converge")


def assess_calibration_analogue(
    authorization: object,
    labels: object,
    nondegenerate_scenario_counts: object,
    *,
    false_authorization_cost: float = 1.0,
    abstention_cost: float = 0.25,
) -> CalibrationAnalogue:
    """Compute the frozen Stage-A success analogues without evaluation values."""
    action = np.asarray(authorization, dtype=np.bool_)
    outcome = np.asarray(labels, dtype=np.bool_)
    counts = np.asarray(nondegenerate_scenario_counts, dtype=np.int64)
    if action.shape != (60,) or outcome.shape != (60,) or counts.shape != (60,):
        raise CalibrationOrchestrationError("Calibration analogue requires exactly 60 origins")
    participation = float(np.mean(action))
    false_authorization = action & outcome
    abstention = ~action
    loss = float(
        np.mean(false_authorization_cost * false_authorization + abstention_cost * abstention)
    )
    failure_rate = float(np.mean(outcome[action])) if np.any(action) else 1.0
    valid_authorized = int(np.sum(action & (counts >= 2)))
    failures: list[str] = []
    if participation < 0.10:
        failures.append("participation_below_0_10")
    if np.any(action & (counts < 2)) or not np.any(action & (counts >= 2)):
        failures.append("authorized_origin_has_fewer_than_two_scenarios")
    return CalibrationAnalogue(
        not failures, participation, loss, failure_rate, valid_authorized, tuple(failures)
    )


def evaluation_identity_payload(payload: Mapping[str, Any]) -> tuple[bytes, str]:
    """Validate and hash Stage-A evaluation input identity with no fitted field."""
    required = {
        "origin_month",
        "full_scenario_id",
        "analytic_representative_id",
        "provenance_member_ids",
        "expanding_ordered_retained_series_ids",
        "expanding_eligibility_mask_hash",
        "expanding_standardized_matrix_hash",
        "rolling_ordered_retained_series_ids",
        "rolling_eligibility_mask_hash",
        "rolling_standardized_matrix_hash",
    }
    keys = set(payload)
    if keys != required or any(
        token in key.lower() for key in keys for token in EVALUATION_FORBIDDEN_TOKENS
    ):
        raise CalibrationOrchestrationError(
            "Evaluation identity contains a fitted or unknown field"
        )
    for key in (
        "expanding_eligibility_mask_hash",
        "expanding_standardized_matrix_hash",
        "rolling_eligibility_mask_hash",
        "rolling_standardized_matrix_hash",
    ):
        if not _valid_sha256(payload[key]):
            raise CalibrationOrchestrationError("Evaluation identity hash is invalid")
    encoded = _canonical_json(dict(payload))
    return encoded, _sha256(encoded)


def expected_calibration_months() -> tuple[str, ...]:
    return tuple(f"{year:04d}-{month:02d}" for year in range(2013, 2018) for month in range(1, 13))


def validate_and_serialize_calibration_ledger(rows: Sequence[Mapping[str, Any]]) -> bytes:
    """Require the complete 60-origin immutable calibration ledger."""
    ordered = tuple(rows)
    if len(ordered) != 60:
        raise CalibrationOrchestrationError("Calibration ledger must have exactly 60 rows")
    months = tuple(str(row.get("origin_month", "")) for row in ordered)
    if months != expected_calibration_months() or len(set(months)) != 60:
        raise CalibrationOrchestrationError(
            "Calibration ledger origins are incomplete or unordered"
        )
    for row in ordered:
        if set(row) != LEDGER_FIELDS or not isinstance(row["matured_future_failure_label"], bool):
            raise CalibrationOrchestrationError("Calibration ledger row schema is incomplete")
        if (
            not isinstance(row["analytic_scenario_count"], int)
            or row["analytic_scenario_count"] < 0
        ):
            raise CalibrationOrchestrationError("Calibration scenario count is invalid")
        for key in (
            "candidate_authorization_vector_hash",
            "B1_B2_B3_candidate_authorization_vector_hashes",
            "negative_control_candidate_vector_hashes",
        ):
            value = row[key]
            if key.endswith("_hash"):
                valid = _valid_sha256(value)
            else:
                valid = (
                    isinstance(value, dict)
                    and bool(value)
                    and all(_valid_sha256(item) for item in value.values())
                )
            if not valid:
                raise CalibrationOrchestrationError("Calibration ledger contains an invalid hash")
    return b"".join(_canonical_json(dict(row)) for row in ordered)


def validate_calibration_lock_body(body: Mapping[str, Any]) -> None:
    """Validate the complete OG-08 lock schema before immutable creation."""
    required = {
        "stage",
        "approved_amendment_sha256",
        "implementation_identity",
        "required_counts",
        "selected_settings",
        "calibration_metrics",
        "calibration_origin_ledger_sha256",
        "evaluation_identity_map_sha256",
        "exact_input_hashes",
        "invariance_results",
    }
    if set(body) != required or body.get("stage") != "calibration_lock":
        raise CalibrationOrchestrationError("Calibration lock schema is incomplete")
    implementation = body["implementation_identity"]
    if not isinstance(implementation, dict) or set(implementation) != {
        "git_commit",
        "orchestrator_sha256",
        "harness_sha256",
        "protocol_sha256",
        "run027_amendment_sha256",
    }:
        raise CalibrationOrchestrationError("Calibration implementation identity is incomplete")
    commit = implementation["git_commit"]
    if (
        not isinstance(commit, str)
        or len(commit) != 40
        or not all(character in "0123456789abcdef" for character in commit)
    ):
        raise CalibrationOrchestrationError("Calibration implementation commit is invalid")
    hash_values = [
        body["approved_amendment_sha256"],
        body["calibration_origin_ledger_sha256"],
        body["evaluation_identity_map_sha256"],
    ]
    hash_values.extend(value for key, value in implementation.items() if key != "git_commit")
    exact = body["exact_input_hashes"]
    if not isinstance(exact, dict) or not exact:
        raise CalibrationOrchestrationError("Calibration exact input hashes are missing")
    hash_values.extend(exact.values())
    if not all(_valid_sha256(value) for value in hash_values):
        raise CalibrationOrchestrationError("Calibration lock contains an invalid SHA-256")
    if body["required_counts"] != {
        "calibration_origins": 60,
        "embargo_months": 12,
        "evaluation_origins": 70,
    }:
        raise CalibrationOrchestrationError("Calibration lock counts are invalid")
    settings = body["selected_settings"]
    metrics = body["calibration_metrics"]
    if not isinstance(settings, dict) or set(settings) != LOCK_SELECTED_SETTINGS:
        raise CalibrationOrchestrationError("Calibration lock selected settings are incomplete")
    if not isinstance(metrics, dict) or set(metrics) != LOCK_CALIBRATION_METRICS:
        raise CalibrationOrchestrationError("Calibration lock metrics are incomplete")


def write_complete_calibration_lock(path: Path, body: Mapping[str, Any]) -> str:
    """Validate then atomically create the one-time Stage-A lock."""
    validate_calibration_lock_body(body)
    body_bytes = _canonical_json(dict(body))
    digest = _sha256(body_bytes)
    content = _canonical_json({**body, "stage_A_sha256": digest})
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise CalibrationOrchestrationError("refusing to overwrite immutable lock") from error
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return digest


def orchestration_surface() -> Mapping[str, object]:
    """Expose the implemented OG-01--OG-09 surface and sealed boundaries."""
    return {
        "OG-01": scenario_identity.__name__,
        "OG-02": validate_pipeline_trace.__name__,
        "OG-03": prepare_history.__name__,
        "OG-04": combine_b2_history.__name__,
        "OG-05": fit_projected_observed_stable_pcp.__name__,
        "OG-06": assess_calibration_analogue.__name__,
        "OG-07": evaluation_identity_payload.__name__,
        "OG-08": (
            validate_calibration_lock_body.__name__,
            write_complete_calibration_lock.__name__,
        ),
        "OG-09": validate_and_serialize_calibration_ledger.__name__,
        "official_fit_performed": False,
        "evaluation_fit_or_label_accessed": False,
        "transmission_module_imported": False,
    }
