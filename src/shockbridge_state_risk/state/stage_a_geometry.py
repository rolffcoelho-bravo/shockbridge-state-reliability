"""Scenario-geometry kernel for the prospective Run 031 Stage-A runner.

The kernel accepts in-memory histories only.  File binding, origin generation,
future-failure labels, and calibration selection remain separate transactions.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from shockbridge_state_risk.state.calibration_orchestration import (
    B2Member,
    CalibrationOrchestrationError,
    PreparedHistory,
    ScenarioIdentity,
    SeriesDescriptor,
    combine_b2_history,
    fit_projected_observed_stable_pcp,
    prepare_history,
    scenario_identity,
)
from shockbridge_state_risk.state.hmm import FloatArray
from shockbridge_state_risk.state.reliability_engine import (
    ReliabilityEngineError,
    build_channel_map,
    channel_projector,
    compare_projectors,
    score_projector,
    select_em_pca_rank,
)
from shockbridge_state_risk.state.reliability_execution_harness import (
    ReliabilityExecutionHarnessError,
    rank_invariant_anchor_state,
    recover_complete_case_scores,
)
from shockbridge_state_risk.state.stage_a_calibration import GeometryRecord

CHANNEL_ORDER = (
    "prices_and_expectations",
    "real_activity_and_labour",
    "policy_stance_and_money_market",
    "sovereign_curve_and_term_structure",
    "bank_funding_and_lending_rates",
    "credit_and_money_quantities",
    "financial_conditions_and_systemic_stress",
    "external_value_and_cross_border_conditions",
)
MISSINGNESS_POLICIES = ("observed_ragged_edge", "complete_case_common_window")


class StageAGeometryError(CalibrationOrchestrationError):
    """Raised when a frozen scenario geometry cannot be constructed."""


@dataclass(frozen=True)
class HistoryGeometry:
    """Common-space geometry and rank-invariant scalar for one history."""

    standardized_anchor_scalar: FloatArray
    score_projector: FloatArray
    channel_projector: FloatArray
    anchor_capture: float
    channel_count: int
    selected_rank: int


@dataclass(frozen=True)
class ScenarioPairGeometry:
    """Expanding/rolling fit for one complete analytic scenario identity."""

    identity: ScenarioIdentity
    expanding: HistoryGeometry
    rolling: HistoryGeometry
    score_distance: float
    channel_distance: float
    minimum_anchor_capture: float


def _channel_map(history: PreparedHistory, channels: Sequence[str] | None) -> FloatArray:
    series_channels = tuple(channels) if channels is not None else history.series_channels
    if len(series_channels) != len(history.retained_series_ids):
        raise StageAGeometryError("Channel assignment does not match retained series")
    try:
        return build_channel_map(series_channels, history.signs, channel_order=CHANNEL_ORDER).matrix
    except ReliabilityEngineError as error:
        raise StageAGeometryError(str(error)) from error


def _anchor_from_complete_case(
    final_scores: FloatArray,
    training_scores: FloatArray,
    loadings: FloatArray,
    mapping: FloatArray,
) -> tuple[FloatArray, float]:
    try:
        training = rank_invariant_anchor_state(training_scores, loadings, mapping)
    except ReliabilityExecutionHarnessError as error:
        raise StageAGeometryError(str(error)) from error
    training_scalar = training.scalar_scores
    scale = float(np.std(training_scalar, ddof=1))
    mean = float(np.mean(training_scalar))
    scalar = final_scores @ training.coefficient
    standardized = (scalar - mean) / scale
    if standardized.shape != (120,) or np.any(~np.isfinite(standardized)):
        raise StageAGeometryError("Complete-case final scalar is invalid")
    return np.asarray(standardized, dtype=np.float64), training.capture


def fit_history_geometry(
    history: PreparedHistory,
    *,
    missingness_policy: str,
    channel_assignments: Sequence[str] | None = None,
    pcp_lambda_multiplier: float | None = None,
) -> HistoryGeometry:
    """Fit one history under ragged, complete-case, or projected-PCP rules."""
    if missingness_policy not in MISSINGNESS_POLICIES:
        raise StageAGeometryError("Missingness policy is not registered")
    if history.standardized.shape[0] < 120:
        raise StageAGeometryError("History lacks the common final 120-month calendar")
    mapping = _channel_map(history, channel_assignments)
    weights = np.sum(np.abs(mapping), axis=0)
    try:
        if pcp_lambda_multiplier is not None:
            if missingness_policy != "observed_ragged_edge":
                raise StageAGeometryError("B3 PCP is defined only for observed ragged input")
            recovered = fit_projected_observed_stable_pcp(
                history.standardized, lambda_multiplier=pcp_lambda_multiplier
            )
            selection = select_em_pca_rank(recovered.low_rank, weights)
            fit = selection.selected
            anchor = rank_invariant_anchor_state(fit.scores, fit.loadings, mapping)
            scalar = anchor.standardized_scores[-120:]
            loadings = fit.loadings
            rank = fit.rank
            capture_value = anchor.capture
        elif missingness_policy == "observed_ragged_edge":
            selection = select_em_pca_rank(history.standardized, weights)
            fit = selection.selected
            anchor = rank_invariant_anchor_state(fit.scores, fit.loadings, mapping)
            scalar = anchor.standardized_scores[-120:]
            loadings = fit.loadings
            rank = fit.rank
            capture_value = anchor.capture
        else:
            recovered_fit = recover_complete_case_scores(history.standardized, weights)
            scalar, capture = _anchor_from_complete_case(
                recovered_fit.final_window_scores,
                recovered_fit.fit.scores,
                recovered_fit.loadings,
                mapping,
            )
            loadings = recovered_fit.loadings
            rank = recovered_fit.rank
            capture_value = capture
    except (
        CalibrationOrchestrationError,
        ReliabilityEngineError,
        ReliabilityExecutionHarnessError,
    ) as error:
        raise StageAGeometryError(str(error)) from error
    try:
        scalar_projector = score_projector(np.asarray(scalar)[:, None])
        loading_projector = channel_projector(loadings, mapping)
    except ReliabilityEngineError as error:
        raise StageAGeometryError(str(error)) from error
    return HistoryGeometry(
        np.asarray(scalar, dtype=np.float64),
        scalar_projector,
        loading_projector,
        float(capture_value),
        len(set(history.series_channels if channel_assignments is None else channel_assignments)),
        rank,
    )


def fit_scenario_pair(
    full_scenario_id: str,
    expanding_values: object,
    rolling_values: object,
    descriptors: Sequence[SeriesDescriptor],
    *,
    missingness_policy: str,
    channel_assignments: Sequence[str] | None = None,
    pcp_lambda_multiplier: float | None = None,
) -> ScenarioPairGeometry:
    """Prepare histories independently, fit them, and construct common geometry."""
    expanding = prepare_history(expanding_values, descriptors)
    rolling = prepare_history(rolling_values, descriptors)
    identity = scenario_identity(full_scenario_id, expanding, rolling)
    if channel_assignments is not None:
        if len(channel_assignments) != len(descriptors):
            raise StageAGeometryError("Channel assignment does not match descriptors")
        by_id = {
            descriptor.series_id: channel
            for descriptor, channel in zip(descriptors, channel_assignments)
        }
        expanding_channels = tuple(by_id[item] for item in expanding.retained_series_ids)
        rolling_channels = tuple(by_id[item] for item in rolling.retained_series_ids)
    else:
        expanding_channels = None
        rolling_channels = None
    expanding_fit = fit_history_geometry(
        expanding,
        missingness_policy=missingness_policy,
        channel_assignments=expanding_channels,
        pcp_lambda_multiplier=pcp_lambda_multiplier,
    )
    rolling_fit = fit_history_geometry(
        rolling,
        missingness_policy=missingness_policy,
        channel_assignments=rolling_channels,
        pcp_lambda_multiplier=pcp_lambda_multiplier,
    )
    score = compare_projectors(expanding_fit.score_projector, rolling_fit.score_projector)
    channel = compare_projectors(expanding_fit.channel_projector, rolling_fit.channel_projector)
    return ScenarioPairGeometry(
        identity,
        expanding_fit,
        rolling_fit,
        score.spectral_distance,
        channel.spectral_distance,
        min(expanding_fit.anchor_capture, rolling_fit.anchor_capture),
    )


def envelope_record(origin_month: str, scenarios: Sequence[ScenarioPairGeometry]) -> GeometryRecord:
    """Construct the primary cross-scenario envelope over unique identities."""
    unique: dict[str, ScenarioPairGeometry] = {}
    for scenario in scenarios:
        unique.setdefault(scenario.identity.sha256, scenario)
    ordered = tuple(unique[key] for key in sorted(unique))
    if len(ordered) < 2:
        return GeometryRecord(origin_month, 1.0, 1.0, 0.0, len(ordered), False)
    histories = tuple(
        history for scenario in ordered for history in (scenario.expanding, scenario.rolling)
    )
    score_distance = max(
        compare_projectors(
            histories[left].score_projector, histories[right].score_projector
        ).spectral_distance
        for left in range(len(histories))
        for right in range(left + 1, len(histories))
    )
    channel_distance = max(
        compare_projectors(
            histories[left].channel_projector, histories[right].channel_projector
        ).spectral_distance
        for left in range(len(histories))
        for right in range(left + 1, len(histories))
    )
    capture = min(history.anchor_capture for history in histories)
    return GeometryRecord(
        origin_month,
        float(score_distance),
        float(channel_distance),
        float(capture),
        len(ordered),
        True,
    )


def single_scenario_record(origin_month: str, scenario: ScenarioPairGeometry) -> GeometryRecord:
    """Convert B1 or B3 scenario geometry to the common calibration record."""
    return GeometryRecord(
        origin_month,
        scenario.score_distance,
        scenario.channel_distance,
        scenario.minimum_anchor_capture,
        1,
        True,
    )


def b2_record(origin_month: str, scenarios: Sequence[ScenarioPairGeometry]) -> GeometryRecord:
    """Combine every unique nondegenerate analytic scenario with equal weight."""
    unique: dict[str, ScenarioPairGeometry] = {}
    for scenario in scenarios:
        unique.setdefault(scenario.identity.sha256, scenario)
    ordered = tuple(unique[key] for key in sorted(unique))
    if len(ordered) < 2:
        return GeometryRecord(origin_month, 1.0, 1.0, 0.0, len(ordered), False)
    expanding = combine_b2_history(
        tuple(
            B2Member(
                item.identity.sha256,
                item.expanding.standardized_anchor_scalar,
                item.expanding.channel_projector,
                item.expanding.anchor_capture,
            )
            for item in ordered
        )
    )
    rolling = combine_b2_history(
        tuple(
            B2Member(
                item.identity.sha256,
                item.rolling.standardized_anchor_scalar,
                item.rolling.channel_projector,
                item.rolling.anchor_capture,
            )
            for item in ordered
        )
    )
    score_distance = compare_projectors(
        score_projector(expanding.standardized_anchor_scalar[:, None]),
        score_projector(rolling.standardized_anchor_scalar[:, None]),
    ).spectral_distance
    channel_distance = float(
        np.linalg.norm(expanding.channel_operator - rolling.channel_operator, ord=2)
    )
    return GeometryRecord(
        origin_month,
        score_distance,
        channel_distance,
        min(expanding.mean_anchor_capture, rolling.mean_anchor_capture),
        len(ordered),
        True,
    )
