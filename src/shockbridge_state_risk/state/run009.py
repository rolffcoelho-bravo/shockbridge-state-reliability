"""Outcome-blind orchestration for the frozen Run 009 instability diagnostic."""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
import yaml

from shockbridge_state_risk.data.download import sha256_file
from shockbridge_state_risk.state.comparison import load_monthly_matrix
from shockbridge_state_risk.state.hmm import FloatArray
from shockbridge_state_risk.state.instability import (
    detect_breach_episodes,
    gram_geometry,
    monetary_regimes,
    sign_materiality,
    standardization_drift,
)
from shockbridge_state_risk.state.subspace import (
    economic_anchor_matrix,
    estimate_anchored_subspace,
)


class Run009Error(ValueError):
    """Raised when the Run 009 contract or artifact bundle fails closed."""


@dataclass(frozen=True)
class GeometryReferences:
    core_second_cosine: float
    summary_second_cosine_p10: float
    core_projector_distance: float
    summary_projector_distance_p90: float
    weak_policy_anchor_capture: float
    weak_relative_eigengap: float
    high_perturbation_to_gap_ratio: float
    weak_identification_coincidence_rate: float


@dataclass(frozen=True)
class EpisodeRule:
    minimum_consecutive_breaches: int
    recovery_consecutive_stable: int
    primary: bool


@dataclass(frozen=True)
class Run009Config:
    config_sha256: str
    experiment_id: str
    evidence_status: str
    approved_design_path: Path
    approved_design_sha256: str
    panel_path: Path
    panel_sha256: str
    run_008_manifest_path: Path
    run_008_manifest_sha256: str
    run_008_fixed_factor_path: Path
    run_008_fixed_factor_sha256: str
    features: tuple[str, ...]
    factor_dimension: int
    rolling_months: tuple[int, ...]
    panel_start: str
    panel_end: str
    common_origin_start: str
    common_origin_end: str
    geometry_references: GeometryReferences
    episode_rules: tuple[EpisodeRule, ...]
    policy_rate_zero_tolerance: float
    sign_materiality_thresholds: tuple[float, ...]
    leave_one_feature_out: bool
    outcomes_accessed: bool
    run_009_state_diagnostic_execution_authorized: bool
    transmission_outcome_execution_authorized: bool


@dataclass(frozen=True)
class DiagnosticRow:
    month_id: str
    cutoff_timestamp: str
    panel_variant: str
    omitted_feature: Optional[str]
    rolling_months: int
    primary_common_sample: bool
    expanding_training_months: int
    rolling_training_months: int
    second_principal_cosine: float
    normalized_projector_distance: float
    gram_spectral_distance: float
    gram_normalized_frobenius_distance: float
    expanding_absolute_eigengap: float
    rolling_absolute_eigengap: float
    expanding_relative_eigengap: float
    rolling_relative_eigengap: float
    perturbation_to_minimum_eigengap_ratio: float
    core_breach: bool
    weak_identification_concurrent: bool
    expanding_slack_anchor_capture: Optional[float]
    rolling_slack_anchor_capture: Optional[float]
    expanding_policy_anchor_capture: Optional[float]
    rolling_policy_anchor_capture: Optional[float]
    weak_policy_anchor: Optional[bool]
    policy_rate_regime: Optional[str]
    location_shift_json: Optional[str]
    log_scale_ratio_json: Optional[str]
    expanding_missing_rate_json: Optional[str]
    rolling_missing_rate_json: Optional[str]
    upper_triangle_drift_contribution_json: Optional[str]


@dataclass(frozen=True)
class EpisodeRow:
    panel_variant: str
    omitted_feature: Optional[str]
    rolling_months: int
    minimum_consecutive_breaches: int
    recovery_consecutive_stable: int
    primary_rule: bool
    episode_number: int
    start_month: str
    end_month: str
    duration_months: int
    breach_months: int
    open_at_sample_end: bool


@dataclass(frozen=True)
class Run009Result:
    diagnostic_rows: tuple[DiagnosticRow, ...]
    episode_rows: tuple[EpisodeRow, ...]
    audit: Mapping[str, Any]


def _mapping(value: object, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise Run009Error(f"{context} must be a mapping.")
    return value


def _sequence(value: object, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise Run009Error(f"{context} must be a list.")
    return value


def _boolean(value: object, context: str) -> bool:
    if not isinstance(value, bool):
        raise Run009Error(f"{context} must be a boolean.")
    return value


def _integer(value: object, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise Run009Error(f"{context} must be an integer.")
    return value


def _exact_fields(payload: Mapping[str, Any], expected: set[str], context: str) -> None:
    if set(payload) != expected:
        missing = sorted(expected - payload.keys())
        unexpected = sorted(payload.keys() - expected)
        raise Run009Error(
            f"{context} fields differ from the frozen contract: {missing=}, {unexpected=}."
        )


def _canonical_float(value: float) -> float:
    scalar = float(value)
    if not np.isfinite(scalar):
        raise Run009Error("Run 009 cannot serialize a non-finite value.")
    if abs(scalar) < 1e-12:
        return 0.0
    return float(f"{scalar:.12g}")


def _json_array(values: FloatArray) -> str:
    array = np.asarray(values, dtype=np.float64)
    if np.any(~np.isfinite(array)):
        raise Run009Error("Run 009 cannot serialize a non-finite array.")
    canonical = np.asarray([_canonical_float(value) for value in array.ravel()]).reshape(
        array.shape
    )
    return json.dumps(canonical.tolist(), separators=(",", ":"))


def _validate_execution_config(config: Run009Config) -> None:
    if (
        config.outcomes_accessed
        or not config.run_009_state_diagnostic_execution_authorized
        or config.transmission_outcome_execution_authorized
    ):
        raise Run009Error("Run 009 must remain authorized, outcome blind, and diagnostic only.")
    if len(config.features) != len(set(config.features)) or len(config.features) != 4:
        raise Run009Error("Run 009 requires four unique state features.")
    if config.factor_dimension != 2 or config.factor_dimension >= len(config.features) - 1:
        raise Run009Error("Run 009 requires two factors in both full and deletion panels.")
    if config.rolling_months != (96, 120, 144):
        raise Run009Error("Run 009 rolling histories differ from the frozen contract.")
    if len(config.episode_rules) != 3 or {
        (
            rule.minimum_consecutive_breaches,
            rule.recovery_consecutive_stable,
            rule.primary,
        )
        for rule in config.episode_rules
    } != {(3, 3, True), (1, 1, False), (6, 6, False)}:
        raise Run009Error("Run 009 episode rules differ from the frozen contract.")
    if any(
        isinstance(rule.minimum_consecutive_breaches, bool)
        or isinstance(rule.recovery_consecutive_stable, bool)
        or rule.minimum_consecutive_breaches < 1
        or rule.recovery_consecutive_stable < 1
        for rule in config.episode_rules
    ):
        raise Run009Error("Run 009 episode persistence must use positive integers.")
    numerical = (
        *config.geometry_references.__dict__.values(),
        config.policy_rate_zero_tolerance,
        *config.sign_materiality_thresholds,
    )
    if any(not np.isfinite(value) or value < 0.0 for value in numerical):
        raise Run009Error("Run 009 numerical settings must be finite and nonnegative.")
    if config.sign_materiality_thresholds != (0.25, 0.10, 0.50):
        raise Run009Error("Run 009 sign-materiality thresholds differ from the frozen contract.")
    if not config.leave_one_feature_out:
        raise Run009Error("The approved Run 009 feature-deletion sensitivity is required.")
    if config.evidence_status != "REAL_DATA_OUTCOME_BLIND":
        return
    expected = (
        config.experiment_id == "state-instability-run009-v1",
        config.features
        == (
            "hicp_yoy",
            "industrial_production_yoy",
            "unemployment_rate",
            "deposit_facility_rate",
        ),
        config.panel_start == "month-2002-01",
        config.panel_end == "month-2025-10",
        config.common_origin_start == "month-2014-02",
        config.common_origin_end == "month-2025-10",
        config.geometry_references
        == GeometryReferences(0.75, 0.90, 0.35, 0.35, 0.35, 0.20, 1.00, 0.50),
        config.approved_design_sha256
        == "b88a0bd9f945d2662f716cb129bb7aba0279be1b8955e8e4be3475dc9a4b45cf",
        config.panel_sha256 == "80d5e5f4b04fb7551bc69d4c4b429271258efad09987d9971551fd4a477f527e",
        config.run_008_manifest_sha256
        == "cdddd08dfff175726afccdd8c8e89c6d3bd1addf0db5f711999998b2ffd02237",
        config.run_008_fixed_factor_sha256
        == "2afdaba561833a16d18bda92cc22534c55b5516cc7f5714b8212ae40c3691d95",
    )
    if not all(expected):
        raise Run009Error("Run 009 settings differ from the approved frozen empirical contract.")


def _validate_upstream_manifest(config: Run009Config) -> None:
    manifest = _mapping(
        yaml.safe_load(config.run_008_manifest_path.read_text(encoding="utf-8")),
        "Run 008 manifest",
    )
    frozen = _mapping(manifest.get("frozen_design"), "Run 008 frozen design")
    decision = _mapping(manifest.get("decision"), "Run 008 decision")
    outputs = _mapping(manifest.get("outputs"), "Run 008 outputs")
    fixed = _mapping(outputs.get("fixed_factor"), "Run 008 fixed-factor output")
    if (
        frozen.get("outcomes_accessed") is not False
        or frozen.get("synthetic_observations_used") is not False
        or decision.get("selected_primary_state_representation") is not None
        or decision.get("transmission_estimation_authorized") is not False
        or manifest.get("selection_status") != "KILL_GATE_RUN_008_REQUIRED_GATES_FAILED"
        or str(fixed.get("path")) != str(config.run_008_fixed_factor_path)
        or str(fixed.get("sha256")) != config.run_008_fixed_factor_sha256
    ):
        raise Run009Error("The referenced Run 008 evidence does not match the required kill gate.")


def load_run009_config(path: Path) -> Run009Config:
    """Load and fail closed on any departure from the approved Run 009 contract."""
    payload = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "Run 009 config")
    fields = {
        "schema_version",
        "experiment_id",
        "evidence_status",
        "approved_design_path",
        "approved_design_sha256",
        "panel_path",
        "panel_sha256",
        "run_008_manifest_path",
        "run_008_manifest_sha256",
        "run_008_fixed_factor_path",
        "run_008_fixed_factor_sha256",
        "features",
        "factor_dimension",
        "rolling_months",
        "panel_start",
        "panel_end",
        "common_origin_start",
        "common_origin_end",
        "geometry_references",
        "episode_rules",
        "policy_rate_zero_tolerance",
        "sign_materiality_thresholds",
        "leave_one_feature_out",
        "outcomes_accessed",
        "run_009_state_diagnostic_execution_authorized",
        "transmission_outcome_execution_authorized",
    }
    _exact_fields(payload, fields, "Run 009 config")
    reference_payload = _mapping(payload["geometry_references"], "geometry_references")
    _exact_fields(
        reference_payload, set(GeometryReferences.__dataclass_fields__), "geometry_references"
    )
    rule_payloads = _sequence(payload["episode_rules"], "episode_rules")
    approved_design_path = Path(str(payload["approved_design_path"]))
    panel_path = Path(str(payload["panel_path"]))
    manifest_path = Path(str(payload["run_008_manifest_path"]))
    fixed_path = Path(str(payload["run_008_fixed_factor_path"]))
    bound_files = (
        (approved_design_path, str(payload["approved_design_sha256"]), "approved design"),
        (panel_path, str(payload["panel_sha256"]), "panel"),
        (manifest_path, str(payload["run_008_manifest_sha256"]), "Run 008 manifest"),
        (fixed_path, str(payload["run_008_fixed_factor_sha256"]), "Run 008 fixed factor"),
    )
    for candidate, expected_hash, context in bound_files:
        if not candidate.is_file() or sha256_file(candidate) != expected_hash:
            raise Run009Error(f"The Run 009 {context} is missing or has a hash mismatch.")
    approved = _mapping(
        yaml.safe_load(approved_design_path.read_text(encoding="utf-8")),
        "approved Run 009 design",
    )
    if (
        approved.get("status") != "APPROVED_AND_FROZEN_FOR_OUTCOME_BLIND_DIAGNOSTIC_EXECUTION"
        or approved.get("outcomes_accessed") is not False
        or approved.get("run_009_state_diagnostic_execution_authorized") is not True
        or approved.get("transmission_outcome_execution_authorized") is not False
        or _mapping(
            approved.get("leave_one_feature_out_sensitivity"),
            "approved feature-deletion sensitivity",
        ).get("approved")
        is not True
    ):
        raise Run009Error("The referenced Run 009 design is not authorized and outcome blind.")
    try:
        rules = []
        for item in rule_payloads:
            rule = _mapping(item, "episode rule")
            _exact_fields(rule, set(EpisodeRule.__dataclass_fields__), "episode rule")
            rules.append(
                EpisodeRule(
                    _integer(
                        rule["minimum_consecutive_breaches"],
                        "minimum_consecutive_breaches",
                    ),
                    _integer(
                        rule["recovery_consecutive_stable"],
                        "recovery_consecutive_stable",
                    ),
                    _boolean(rule["primary"], "episode primary"),
                )
            )
        config = Run009Config(
            config_sha256=sha256_file(path),
            experiment_id=str(payload["experiment_id"]),
            evidence_status=str(payload["evidence_status"]),
            approved_design_path=approved_design_path,
            approved_design_sha256=str(payload["approved_design_sha256"]),
            panel_path=panel_path,
            panel_sha256=str(payload["panel_sha256"]),
            run_008_manifest_path=manifest_path,
            run_008_manifest_sha256=str(payload["run_008_manifest_sha256"]),
            run_008_fixed_factor_path=fixed_path,
            run_008_fixed_factor_sha256=str(payload["run_008_fixed_factor_sha256"]),
            features=tuple(str(value) for value in _sequence(payload["features"], "features")),
            factor_dimension=_integer(payload["factor_dimension"], "factor_dimension"),
            rolling_months=tuple(
                _integer(value, "rolling_months")
                for value in _sequence(payload["rolling_months"], "rolling_months")
            ),
            panel_start=str(payload["panel_start"]),
            panel_end=str(payload["panel_end"]),
            common_origin_start=str(payload["common_origin_start"]),
            common_origin_end=str(payload["common_origin_end"]),
            geometry_references=GeometryReferences(
                **{
                    field: float(reference_payload[field])
                    for field in GeometryReferences.__dataclass_fields__
                }
            ),
            episode_rules=tuple(rules),
            policy_rate_zero_tolerance=float(payload["policy_rate_zero_tolerance"]),
            sign_materiality_thresholds=tuple(
                float(value)
                for value in _sequence(
                    payload["sign_materiality_thresholds"], "sign_materiality_thresholds"
                )
            ),
            leave_one_feature_out=_boolean(
                payload["leave_one_feature_out"], "leave_one_feature_out"
            ),
            outcomes_accessed=_boolean(payload["outcomes_accessed"], "outcomes_accessed"),
            run_009_state_diagnostic_execution_authorized=_boolean(
                payload["run_009_state_diagnostic_execution_authorized"],
                "run_009_state_diagnostic_execution_authorized",
            ),
            transmission_outcome_execution_authorized=_boolean(
                payload["transmission_outcome_execution_authorized"],
                "transmission_outcome_execution_authorized",
            ),
        )
    except (TypeError, ValueError) as error:
        if isinstance(error, Run009Error):
            raise
        raise Run009Error(f"Run 009 config contains an invalid value: {error}") from error
    if payload["schema_version"] != 1:
        raise Run009Error("Run 009 schema version differs from the frozen contract.")
    _validate_execution_config(config)
    _validate_upstream_manifest(config)
    return config


def _load_fixed_scalar_pairs(config: Run009Config) -> tuple[FloatArray, FloatArray]:
    histories: dict[str, dict[str, float]] = {"expanding": {}, "rolling_120": {}}
    with config.run_008_fixed_factor_path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            history = row.get("history_window", "")
            month = row.get("month_id", "")
            if history not in histories:
                raise Run009Error(f"Unexpected Run 008 fixed-factor history: {history}")
            if month in histories[history]:
                raise Run009Error(f"Duplicate Run 008 fixed-factor key: {history}, {month}")
            try:
                value = float(row["standardized_factor_mean"])
            except (KeyError, ValueError) as error:
                raise Run009Error("Invalid Run 008 standardized scalar value.") from error
            if not np.isfinite(value):
                raise Run009Error("Run 008 standardized scalar values must be finite.")
            histories[history][month] = value
    months = tuple(sorted(set(histories["expanding"]) & set(histories["rolling_120"])))
    common = tuple(
        month for month in months if config.common_origin_start <= month <= config.common_origin_end
    )
    expected_count = (
        _month_number(config.common_origin_end) - _month_number(config.common_origin_start) + 1
    )
    if len(common) != expected_count:
        raise Run009Error("Run 008 fixed scalar does not cover the complete common sample.")
    return (
        np.asarray([histories["expanding"][month] for month in common]),
        np.asarray([histories["rolling_120"][month] for month in common]),
    )


def _month_number(month_id: str) -> int:
    try:
        prefix, year_text, month_text = month_id.split("-")
        year = int(year_text)
        month = int(month_text)
    except (AttributeError, TypeError, ValueError) as error:
        raise Run009Error(f"Invalid Run 009 month identifier: {month_id}") from error
    if prefix != "month" or year < 1 or not 1 <= month <= 12:
        raise Run009Error(f"Invalid Run 009 month identifier: {month_id}")
    return year * 12 + month - 1


def _variant_specifications(
    features: tuple[str, ...],
) -> tuple[tuple[str, Optional[str], tuple[int, ...]], ...]:
    full = ("full", None, tuple(range(len(features))))
    deletions = tuple(
        (
            f"omit_{omitted}",
            omitted,
            tuple(index for index, feature in enumerate(features) if feature != omitted),
        )
        for omitted in features
    )
    return (full, *deletions)


def _summarize_rows(
    rows: tuple[DiagnosticRow, ...], config: Run009Config
) -> tuple[dict[str, Any], bool]:
    summaries: dict[str, Any] = {}
    full_failures: list[bool] = []
    for variant, omitted, _ in _variant_specifications(config.features):
        variant_summary: dict[str, Any] = {"omitted_feature": omitted, "windows": {}}
        for window in config.rolling_months:
            selected = [
                row
                for row in rows
                if row.panel_variant == variant
                and row.rolling_months == window
                and row.primary_common_sample
            ]
            if not selected:
                raise Run009Error(f"Run 009 has no common rows for {variant}, {window}.")
            cosines = np.asarray([row.second_principal_cosine for row in selected])
            distances = np.asarray([row.normalized_projector_distance for row in selected])
            breaches = np.asarray([row.core_breach for row in selected], dtype=bool)
            concurrent = np.asarray(
                [row.weak_identification_concurrent for row in selected], dtype=bool
            )
            p10 = float(np.percentile(cosines, 10.0))
            p90 = float(np.percentile(distances, 90.0))
            failed = (
                p10 < config.geometry_references.summary_second_cosine_p10
                and p90 > config.geometry_references.summary_projector_distance_p90
            )
            coincidence = float(np.mean(concurrent[breaches])) if np.any(breaches) else 0.0
            variant_summary["windows"][str(window)] = {
                "common_origins": len(selected),
                "second_principal_cosine_p10": _canonical_float(p10),
                "projector_distance_p90": _canonical_float(p90),
                "core_breach_rate": _canonical_float(float(np.mean(breaches))),
                "weak_identification_coincidence_rate_among_breaches": _canonical_float(
                    coincidence
                ),
                "weak_identification_flag": coincidence
                >= config.geometry_references.weak_identification_coincidence_rate,
                "window_specific_geometry_failure": failed,
            }
            if variant == "full":
                full_failures.append(failed)
        summaries[variant] = variant_summary
    return summaries, all(full_failures)


def _regime_summaries(rows: tuple[DiagnosticRow, ...], config: Run009Config) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for window in config.rolling_months:
        window_payload: dict[str, Any] = {}
        for regime in ("negative", "zero", "positive"):
            selected = [
                row
                for row in rows
                if row.panel_variant == "full"
                and row.rolling_months == window
                and row.primary_common_sample
                and row.policy_rate_regime == regime
            ]
            if not selected:
                window_payload[regime] = {"observations": 0}
                continue
            window_payload[regime] = {
                "observations": len(selected),
                "core_breach_rate": _canonical_float(
                    float(np.mean([row.core_breach for row in selected]))
                ),
                "weak_policy_anchor_rate": _canonical_float(
                    float(np.mean([bool(row.weak_policy_anchor) for row in selected]))
                ),
                "median_second_principal_cosine": _canonical_float(
                    float(np.median([row.second_principal_cosine for row in selected]))
                ),
                "median_projector_distance": _canonical_float(
                    float(np.median([row.normalized_projector_distance for row in selected]))
                ),
            }
        payload[str(window)] = window_payload
    return payload


def _standardization_summaries(
    rows: tuple[DiagnosticRow, ...], config: Run009Config
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for window in config.rolling_months:
        selected = [
            row
            for row in rows
            if row.panel_variant == "full"
            and row.rolling_months == window
            and row.primary_common_sample
        ]
        location = np.asarray([json.loads(str(row.location_shift_json)) for row in selected])
        scale = np.asarray([json.loads(str(row.log_scale_ratio_json)) for row in selected])
        features: dict[str, Any] = {}
        for column, feature in enumerate(config.features):
            features[feature] = {
                "location_shift_absolute_median": _canonical_float(
                    float(np.median(np.abs(location[:, column])))
                ),
                "location_shift_absolute_p90": _canonical_float(
                    float(np.percentile(np.abs(location[:, column]), 90.0))
                ),
                "location_shift_absolute_maximum": _canonical_float(
                    float(np.max(np.abs(location[:, column])))
                ),
                "log_scale_ratio_absolute_median": _canonical_float(
                    float(np.median(np.abs(scale[:, column])))
                ),
                "log_scale_ratio_absolute_p90": _canonical_float(
                    float(np.percentile(np.abs(scale[:, column]), 90.0))
                ),
                "log_scale_ratio_absolute_maximum": _canonical_float(
                    float(np.max(np.abs(scale[:, column])))
                ),
            }
        payload[str(window)] = features
    return payload


def run_run009(config: Run009Config) -> Run009Result:
    """Execute the frozen Run 009 diagnostic without loading transmission outcomes."""
    _validate_execution_config(config)
    for path, expected, context in (
        (config.approved_design_path, config.approved_design_sha256, "approved design"),
        (config.panel_path, config.panel_sha256, "panel"),
        (config.run_008_manifest_path, config.run_008_manifest_sha256, "Run 008 manifest"),
        (
            config.run_008_fixed_factor_path,
            config.run_008_fixed_factor_sha256,
            "Run 008 fixed factor",
        ),
    ):
        if sha256_file(path) != expected:
            raise Run009Error(f"The Run 009 {context} changed after validation.")
    _validate_upstream_manifest(config)
    matrix = load_monthly_matrix(config.panel_path, config.features)
    month_numbers = tuple(_month_number(month) for month in matrix.month_ids)
    if (
        matrix.month_ids[0] != config.panel_start
        or matrix.month_ids[-1] != config.panel_end
        or config.common_origin_start not in matrix.month_ids
        or config.common_origin_end != matrix.month_ids[-1]
        or any(
            current != previous + 1 for previous, current in zip(month_numbers, month_numbers[1:])
        )
    ):
        raise Run009Error("Run 009 panel or common-sample boundaries are invalid.")
    policy_index = config.features.index("deposit_facility_rate")
    anchors = economic_anchor_matrix()
    references = config.geometry_references
    diagnostic_rows: list[DiagnosticRow] = []
    for variant, omitted, columns in _variant_specifications(config.features):
        for window in config.rolling_months:
            for index in range(window + 1, len(matrix.month_ids)):
                month = matrix.month_ids[index]
                expanding = matrix.values[:index, columns]
                rolling = matrix.values[index - window : index, columns]
                geometry = gram_geometry(expanding, rolling, config.factor_dimension)
                full = variant == "full"
                expanding_capture: Optional[FloatArray] = None
                rolling_capture: Optional[FloatArray] = None
                drift = None
                regime: Optional[str] = None
                if full:
                    expanding_capture = estimate_anchored_subspace(
                        expanding, anchors, config.factor_dimension
                    ).anchor_capture
                    rolling_capture = estimate_anchored_subspace(
                        rolling, anchors, config.factor_dimension
                    ).anchor_capture
                    drift = standardization_drift(expanding, rolling)
                    policy_rate = matrix.values[index, policy_index]
                    regime = monetary_regimes(
                        np.asarray([policy_rate]), config.policy_rate_zero_tolerance
                    )[0]
                second_cosine = float(geometry.principal_cosines[1])
                projector_distance = geometry.normalized_projector_distance
                min_relative_gap = min(
                    geometry.expanding_relative_eigengap,
                    geometry.rolling_relative_eigengap,
                )
                core_breach = (
                    second_cosine < references.core_second_cosine
                    or projector_distance > references.core_projector_distance
                )
                weak_concurrent = (
                    min_relative_gap < references.weak_relative_eigengap
                    and geometry.perturbation_to_minimum_eigengap_ratio
                    > references.high_perturbation_to_gap_ratio
                )
                diagnostic_rows.append(
                    DiagnosticRow(
                        month_id=month,
                        cutoff_timestamp=matrix.cutoff_timestamps[index],
                        panel_variant=variant,
                        omitted_feature=omitted,
                        rolling_months=window,
                        primary_common_sample=(
                            config.common_origin_start <= month <= config.common_origin_end
                        ),
                        expanding_training_months=index,
                        rolling_training_months=window,
                        second_principal_cosine=second_cosine,
                        normalized_projector_distance=projector_distance,
                        gram_spectral_distance=geometry.gram_spectral_distance,
                        gram_normalized_frobenius_distance=(
                            geometry.gram_normalized_frobenius_distance
                        ),
                        expanding_absolute_eigengap=geometry.expanding_absolute_eigengap,
                        rolling_absolute_eigengap=geometry.rolling_absolute_eigengap,
                        expanding_relative_eigengap=geometry.expanding_relative_eigengap,
                        rolling_relative_eigengap=geometry.rolling_relative_eigengap,
                        perturbation_to_minimum_eigengap_ratio=(
                            geometry.perturbation_to_minimum_eigengap_ratio
                        ),
                        core_breach=core_breach,
                        weak_identification_concurrent=weak_concurrent,
                        expanding_slack_anchor_capture=(
                            float(expanding_capture[0]) if expanding_capture is not None else None
                        ),
                        rolling_slack_anchor_capture=(
                            float(rolling_capture[0]) if rolling_capture is not None else None
                        ),
                        expanding_policy_anchor_capture=(
                            float(expanding_capture[1]) if expanding_capture is not None else None
                        ),
                        rolling_policy_anchor_capture=(
                            float(rolling_capture[1]) if rolling_capture is not None else None
                        ),
                        weak_policy_anchor=(
                            min(float(expanding_capture[1]), float(rolling_capture[1]))
                            < references.weak_policy_anchor_capture
                            if expanding_capture is not None and rolling_capture is not None
                            else None
                        ),
                        policy_rate_regime=regime,
                        location_shift_json=(
                            _json_array(drift.location_shift) if drift is not None else None
                        ),
                        log_scale_ratio_json=(
                            _json_array(drift.log_scale_ratio) if drift is not None else None
                        ),
                        expanding_missing_rate_json=(
                            _json_array(drift.expanding_missing_rate) if drift is not None else None
                        ),
                        rolling_missing_rate_json=(
                            _json_array(drift.rolling_missing_rate) if drift is not None else None
                        ),
                        upper_triangle_drift_contribution_json=(
                            _json_array(geometry.upper_triangle_drift_contribution)
                            if full
                            else None
                        ),
                    )
                )
    rows = tuple(diagnostic_rows)
    summaries, pervasive = _summarize_rows(rows, config)
    episode_rows: list[EpisodeRow] = []
    episode_counts: dict[str, int] = {}
    for variant, omitted, _ in _variant_specifications(config.features):
        for window in config.rolling_months:
            selected = [
                row
                for row in rows
                if row.panel_variant == variant
                and row.rolling_months == window
                and row.primary_common_sample
            ]
            month_ids = tuple(row.month_id for row in selected)
            breaches = np.asarray([row.core_breach for row in selected], dtype=bool)
            for rule in config.episode_rules:
                episodes = detect_breach_episodes(
                    month_ids,
                    breaches,
                    rule.minimum_consecutive_breaches,
                    rule.recovery_consecutive_stable,
                )
                key = (
                    f"{variant}__rolling_{window}__"
                    f"{rule.minimum_consecutive_breaches}_{rule.recovery_consecutive_stable}"
                )
                episode_counts[key] = len(episodes)
                for number, episode in enumerate(episodes, start=1):
                    episode_rows.append(
                        EpisodeRow(
                            panel_variant=variant,
                            omitted_feature=omitted,
                            rolling_months=window,
                            minimum_consecutive_breaches=rule.minimum_consecutive_breaches,
                            recovery_consecutive_stable=rule.recovery_consecutive_stable,
                            primary_rule=rule.primary,
                            episode_number=number,
                            start_month=episode.start_month,
                            end_month=episode.end_month,
                            duration_months=episode.duration_months,
                            breach_months=episode.breach_months,
                            open_at_sample_end=episode.open_at_sample_end,
                        )
                    )
    left_scalar, right_scalar = _load_fixed_scalar_pairs(config)
    sign_payload = {
        str(threshold): asdict(sign_materiality(left_scalar, right_scalar, threshold))
        for threshold in config.sign_materiality_thresholds
    }
    real_data = config.evidence_status == "REAL_DATA_OUTCOME_BLIND"
    audit = {
        "experiment_id": config.experiment_id,
        "evidence_status": (
            "REAL_DATA_OUTCOME_BLIND_RUN_009_DIAGNOSTIC" if real_data else "SOFTWARE_TEST_ONLY"
        ),
        "config_sha256": config.config_sha256,
        "approved_design_sha256": config.approved_design_sha256,
        "panel_sha256": config.panel_sha256,
        "run_008_manifest_sha256": config.run_008_manifest_sha256,
        "run_008_fixed_factor_sha256": config.run_008_fixed_factor_sha256,
        "features": list(config.features),
        "rolling_months": list(config.rolling_months),
        "panel_period": [config.panel_start, config.panel_end],
        "common_origin_period": [config.common_origin_start, config.common_origin_end],
        "common_origins": _month_number(config.common_origin_end)
        - _month_number(config.common_origin_start)
        + 1,
        "diagnostic_rows": len(rows),
        "episode_rows": len(episode_rows),
        "geometry_summary": summaries,
        "full_panel_pervasive_geometry_failure": pervasive,
        "monetary_regime_summary_descriptive_only": _regime_summaries(rows, config),
        "standardization_drift_summary": _standardization_summaries(rows, config),
        "fixed_scalar_sign_materiality": sign_payload,
        "episode_counts": episode_counts,
        "leave_one_feature_out_interpretation": (
            "descriptive_sensitivity_not_causal_driver_attribution_or_state_rescue"
        ),
        "large_n_structural_break_inference_performed": False,
        "state_selection_performed": False,
        "run_008_decision_recalculated": False,
        "outcomes_accessed": False,
        "synthetic_observations_used": not real_data,
        "transmission_estimation_authorized": False,
    }
    return Run009Result(rows, tuple(episode_rows), audit)


def _write_rows(rows: tuple[Any, ...], path: Path, fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(fields))
        writer.writeheader()
        for row in rows:
            payload = asdict(row)
            writer.writerow(
                {
                    key: _canonical_float(value) if isinstance(value, float) else value
                    for key, value in payload.items()
                }
            )


def write_run009_outputs(
    result: Run009Result,
    diagnostic_path: Path,
    episode_path: Path,
    audit_path: Path,
) -> None:
    """Write the complete Run 009 bundle after every temporary artifact succeeds."""
    if not result.diagnostic_rows or not result.audit:
        raise Run009Error("Run 009 cannot write an incomplete artifact bundle.")
    paths = (diagnostic_path, episode_path, audit_path)
    if len(set(paths)) != len(paths):
        raise Run009Error("Run 009 output paths must be distinct.")
    temporary_paths = tuple(path.with_suffix(path.suffix + ".part") for path in paths)
    if any(path.exists() for path in temporary_paths):
        raise Run009Error("Run 009 found a pre-existing incomplete temporary artifact.")
    try:
        _write_rows(
            result.diagnostic_rows,
            diagnostic_path,
            tuple(DiagnosticRow.__dataclass_fields__),
        )
        _write_rows(result.episode_rows, episode_path, tuple(EpisodeRow.__dataclass_fields__))
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.with_suffix(audit_path.suffix + ".part").write_text(
            json.dumps(result.audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except Exception:
        for temporary in temporary_paths:
            temporary.unlink(missing_ok=True)
        raise
    for target, temporary in zip(paths, temporary_paths):
        temporary.replace(target)
