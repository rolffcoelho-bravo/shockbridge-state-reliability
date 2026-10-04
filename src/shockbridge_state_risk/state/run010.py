"""Matched-period latest-vintage robustness audit for Run 010."""

from __future__ import annotations

import csv
import json
import math
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np
import yaml

from shockbridge_state_risk.data.download import DownloadError, download_https, sha256_file
from shockbridge_state_risk.state.comparison import load_monthly_matrix
from shockbridge_state_risk.state.hmm import FloatArray
from shockbridge_state_risk.state.instability import detect_breach_episodes, gram_geometry

APPROVED_DESIGN_SHA256 = "f85116d407019b9386101242e94381fa2973a1e39addfb24e4255653444db457"
FEATURES = (
    "hicp_yoy",
    "industrial_production_yoy",
    "unemployment_rate",
    "deposit_facility_rate",
)
MACRO_FEATURES = FEATURES[:3]
SOURCE_FILENAMES = {
    "hicp_yoy": "run010_latest_hicp.csv",
    "industrial_production_yoy": "run010_latest_ip.csv",
    "unemployment_rate": "run010_latest_unemployment.csv",
}
SOURCE_PROPOSAL_KEYS = {
    "hicp_yoy": "hicp_index",
    "industrial_production_yoy": "industrial_production_index",
    "unemployment_rate": "unemployment_rate",
}


class Run010Error(ValueError):
    """Raised when the Run 010 contract or evidence bundle fails closed."""


@dataclass(frozen=True)
class LatestSource:
    feature_id: str
    path: Path
    url: str
    series_key: str
    sha256: str
    bytes: int
    retrieved_at_utc: str


@dataclass(frozen=True)
class GeometryReferences:
    core_second_cosine: float
    summary_second_cosine_p10: float
    core_projector_distance: float
    summary_projector_distance_p90: float
    weak_relative_eigengap: float
    high_perturbation_to_gap_ratio: float
    weak_identification_coincidence_rate: float


@dataclass(frozen=True)
class BootstrapContract:
    replications: int
    random_seed: int
    primary_block_months: int
    sensitivity_block_months: tuple[int, ...]


@dataclass(frozen=True)
class Run010Config:
    config_sha256: str
    experiment_id: str
    evidence_status: str
    approved_design_path: Path
    approved_design_sha256: str
    panel_path: Path
    panel_sha256: str
    run009_diagnostic_path: Path
    run009_diagnostic_sha256: str
    source_manifest_path: Path
    source_manifest_sha256: str
    sources: Mapping[str, LatestSource]
    features: tuple[str, ...]
    factor_dimension: int
    rolling_months: tuple[int, ...]
    panel_start: str
    panel_end: str
    common_origin_start: str
    common_origin_end: str
    development_start: str
    development_end: str
    geometry_references: GeometryReferences
    bootstrap: BootstrapContract
    outcomes_accessed: bool
    synthetic_observations_allowed: bool
    run_010_execution_authorized: bool
    transmission_outcome_execution_authorized: bool


@dataclass(frozen=True)
class VintageComparisonRow:
    month_id: str
    cutoff_timestamp: str
    feature_id: str
    observation_period: str
    point_in_time_value: Optional[float]
    latest_vintage_value: Optional[float]
    latest_minus_point_in_time: Optional[float]
    standardized_difference: Optional[float]
    originally_missing: bool
    latest_source_series_id: str
    latest_source_sha256: str
    evidence_status: str


@dataclass(frozen=True)
class VintageGeometryRow:
    month_id: str
    cutoff_timestamp: str
    panel_vintage: str
    panel_variant: str
    omitted_feature: Optional[str]
    rolling_months: int
    primary_common_sample: bool
    second_principal_cosine: float
    normalized_projector_distance: float
    gram_spectral_distance: float
    gram_normalized_frobenius_distance: float
    expanding_relative_eigengap: float
    rolling_relative_eigengap: float
    perturbation_to_minimum_eigengap_ratio: float
    off_diagonal_gram_drift_share: float
    core_breach: bool
    weak_identification_concurrent: bool


@dataclass(frozen=True)
class VintageEpisodeRow:
    panel_vintage: str
    panel_variant: str
    omitted_feature: Optional[str]
    rolling_months: int
    episode_number: int
    start_month: str
    end_month: str
    duration_months: int
    breach_months: int
    open_at_sample_end: bool


@dataclass(frozen=True)
class Run010Result:
    comparison_rows: tuple[VintageComparisonRow, ...]
    geometry_rows: tuple[VintageGeometryRow, ...]
    episode_rows: tuple[VintageEpisodeRow, ...]
    audit: Mapping[str, Any]


def _mapping(value: object, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise Run010Error(f"{context} must be a mapping.")
    return value


def _sequence(value: object, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise Run010Error(f"{context} must be a list.")
    return value


def _boolean(value: object, context: str) -> bool:
    if not isinstance(value, bool):
        raise Run010Error(f"{context} must be a boolean.")
    return value


def _integer(value: object, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise Run010Error(f"{context} must be an integer.")
    return value


def _exact_fields(payload: Mapping[str, Any], expected: set[str], context: str) -> None:
    if set(payload) != expected:
        missing = sorted(expected - payload.keys())
        unexpected = sorted(payload.keys() - expected)
        raise Run010Error(f"{context} fields differ: {missing=}, {unexpected=}.")


def _canonical_float(value: float) -> float:
    scalar = float(value)
    if not np.isfinite(scalar):
        raise Run010Error("Run 010 cannot serialize a non-finite value.")
    if abs(scalar) < 1e-12:
        return 0.0
    return float(f"{scalar:.12g}")


def _month_number(month_id: str) -> int:
    try:
        prefix, year_text, month_text = month_id.split("-")
        year, month = int(year_text), int(month_text)
        datetime(year, month, 1)
    except (AttributeError, TypeError, ValueError) as error:
        raise Run010Error(f"Invalid month identifier: {month_id}") from error
    if prefix != "month":
        raise Run010Error(f"Invalid month identifier: {month_id}")
    return year * 12 + month - 1


def _previous_year(period: str) -> str:
    try:
        parsed = datetime.strptime(period, "%Y-%m")
    except ValueError as error:
        raise Run010Error(f"Invalid monthly observation period: {period}") from error
    return f"{parsed.year - 1:04d}-{parsed.month:02d}"


def _approved_proposal(path: Path) -> dict[str, Any]:
    if not path.is_file() or sha256_file(path) != APPROVED_DESIGN_SHA256:
        raise Run010Error("The approved Run 010 design is missing or has changed.")
    proposal = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "Run 010 design")
    authorization = _mapping(proposal.get("implementation_and_execution"), "Run 010 authorization")
    if (
        proposal.get("status") != "APPROVED_AND_FROZEN_FOR_OUTCOME_BLIND_EXECUTION"
        or proposal.get("outcomes_accessed") is not False
        or proposal.get("synthetic_observations_allowed_in_empirical_artifacts") is not False
        or authorization.get("source_download_authorized") is not True
        or authorization.get("implementation_authorized") is not True
        or authorization.get("empirical_execution_authorized") is not True
        or authorization.get("transmission_outcome_execution_authorized") is not False
    ):
        raise Run010Error("The Run 010 design is not fully authorized and outcome blind.")
    return proposal


def _validate_latest_series(
    path: Path,
    expected_key: str,
    expected_dimensions: tuple[str, str, str, str, str, str],
) -> dict[str, float]:
    required = {
        "KEY",
        "FREQ",
        "REF_AREA",
        "ADJUSTMENT",
        "RT_ECON_CONCEPT",
        "RT_DENOM",
        "TIME_PERIOD",
        "OBS_VALUE",
    }
    values: dict[str, float] = {}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise Run010Error(f"Latest-vintage source schema is incomplete: {path}")
        for row in reader:
            observed_dimensions = tuple(
                row[field]
                for field in (
                    "FREQ",
                    "REF_AREA",
                    "ADJUSTMENT",
                    "RT_ECON_CONCEPT",
                    "RT_DENOM",
                    "KEY",
                )
            )
            if observed_dimensions != expected_dimensions or row["KEY"] != expected_key:
                raise Run010Error(f"Latest-vintage source metadata changed: {path}")
            if row.get("ACTION", "Replace") not in {"", "Replace"}:
                raise Run010Error("Current-production latest-vintage rows cannot be deletions.")
            period = row["TIME_PERIOD"]
            try:
                datetime.strptime(period, "%Y-%m")
                value = float(row["OBS_VALUE"])
            except ValueError as error:
                raise Run010Error(f"Invalid latest-vintage observation in {path}.") from error
            if period in values or not np.isfinite(value):
                raise Run010Error(f"Duplicate or non-finite latest-vintage value in {path}.")
            values[period] = value
    if not values:
        raise Run010Error(f"Latest-vintage source is empty: {path}")
    return values


def fetch_run010_sources(
    approved_design_path: Path,
    output_directory: Path,
    manifest_path: Path,
) -> Mapping[str, Any]:
    """Retrieve the three approved ECB sources as one fail-closed local bundle."""
    proposal = _approved_proposal(approved_design_path)
    if manifest_path.exists() or any(
        (output_directory / filename).exists() for filename in SOURCE_FILENAMES.values()
    ):
        raise Run010Error("Run 010 source outputs are immutable and already exist.")
    retrieval = _mapping(proposal["proposed_latest_vintage_sources"], "source retrieval")
    retry = _mapping(retrieval["retry_policy"], "source retry policy")
    attempts = _integer(retry["maximum_attempts"], "maximum_attempts")
    backoff = tuple(float(value) for value in _sequence(retry["backoff_seconds"], "backoff"))
    if attempts != 3 or backoff != (0.0, 5.0, 20.0):
        raise Run010Error("Run 010 retry policy differs from the approved contract.")
    source_payload = _mapping(retrieval["series"], "source series")
    output_directory.mkdir(parents=True, exist_ok=True)
    temporary_paths: list[Path] = []
    final_paths: list[Path] = []
    records: dict[str, Any] = {}
    try:
        for feature in MACRO_FEATURES:
            spec = _mapping(source_payload[SOURCE_PROPOSAL_KEYS[feature]], feature)
            target = output_directory / SOURCE_FILENAMES[feature]
            temporary = target.with_suffix(target.suffix + ".download")
            temporary_paths.append(temporary)
            attempt_log: list[dict[str, Any]] = []
            manifest = None
            for attempt in range(1, attempts + 1):
                if backoff[attempt - 1] > 0.0:
                    time.sleep(backoff[attempt - 1])
                try:
                    manifest = download_https(
                        str(spec["url"]),
                        temporary,
                        timeout_seconds=float(retry["read_timeout_seconds"]),
                    )
                    attempt_log.append({"attempt": attempt, "status": "success"})
                    break
                except DownloadError as error:
                    message = str(error)
                    retryable = "timed out" in message.lower() or any(
                        token in message
                        for token in (
                            "HTTP Error 429",
                            "HTTP Error 500",
                            "HTTP Error 502",
                            "HTTP Error 503",
                            "HTTP Error 504",
                            "status 429",
                            "status 500",
                            "status 502",
                            "status 503",
                            "status 504",
                        )
                    )
                    attempt_log.append(
                        {
                            "attempt": attempt,
                            "status": "retryable_failure" if retryable else "terminal_failure",
                            "error": message,
                        }
                    )
                    if not retryable:
                        raise Run010Error(
                            f"Run 010 source retrieval failed without retry: {feature}"
                        ) from error
            if manifest is None:
                raise Run010Error(f"Run 010 source retrieval failed: {feature}")
            dimensions = (
                "M",
                str(spec["reference_area"]),
                str(spec["adjustment"]),
                str(spec["concept"]),
                str(spec["denomination"]),
                str(spec["series_key"]),
            )
            _validate_latest_series(temporary, str(spec["series_key"]), dimensions)
            records[feature] = {
                "path": str(target),
                "url": str(spec["url"]),
                "final_url": manifest.final_url,
                "series_key": str(spec["series_key"]),
                "sha256": manifest.sha256,
                "bytes": manifest.bytes,
                "retrieved_at_utc": manifest.retrieved_at_utc,
                "attempts": attempt_log,
            }
            final_paths.append(target)
        payload = {
            "schema_version": 1,
            "manifest_id": "run010-latest-sources-v1",
            "approved_design_path": str(approved_design_path),
            "approved_design_sha256": APPROVED_DESIGN_SHA256,
            "evidence_status": "REAL_OFFICIAL_DATA_EX_POST_LATEST_VINTAGE",
            "outcomes_accessed": False,
            "sources": records,
        }
        manifest_temporary = manifest_path.with_suffix(manifest_path.suffix + ".part")
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_temporary.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        for temporary, target in zip(temporary_paths, final_paths):
            temporary.replace(target)
        manifest_temporary.replace(manifest_path)
        return payload
    except Exception:
        for path in (
            *temporary_paths,
            *final_paths,
            manifest_path.with_suffix(manifest_path.suffix + ".part"),
        ):
            path.unlink(missing_ok=True)
        raise


def _load_source_manifest(
    path: Path, expected_hash: str, approved_proposal: Mapping[str, Any]
) -> Mapping[str, LatestSource]:
    if not path.is_file() or sha256_file(path) != expected_hash:
        raise Run010Error("Run 010 source manifest is missing or has changed.")
    payload = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "source manifest")
    _exact_fields(
        payload,
        {
            "schema_version",
            "manifest_id",
            "approved_design_path",
            "approved_design_sha256",
            "evidence_status",
            "outcomes_accessed",
            "sources",
        },
        "source manifest",
    )
    if (
        payload.get("manifest_id") != "run010-latest-sources-v1"
        or payload.get("approved_design_sha256") != APPROVED_DESIGN_SHA256
        or payload.get("evidence_status") != "REAL_OFFICIAL_DATA_EX_POST_LATEST_VINTAGE"
        or payload.get("outcomes_accessed") is not False
    ):
        raise Run010Error("Run 010 source manifest metadata are invalid.")
    source_payload = _mapping(payload.get("sources"), "source manifest sources")
    if set(source_payload) != set(MACRO_FEATURES):
        raise Run010Error("Run 010 source manifest must contain exactly three macro sources.")
    sources: dict[str, LatestSource] = {}
    approved_sources = _mapping(
        _mapping(
            approved_proposal["proposed_latest_vintage_sources"],
            "approved source retrieval",
        )["series"],
        "approved source series",
    )
    for feature in MACRO_FEATURES:
        item = _mapping(source_payload[feature], feature)
        _exact_fields(
            item,
            {
                "path",
                "url",
                "final_url",
                "series_key",
                "sha256",
                "bytes",
                "retrieved_at_utc",
                "attempts",
            },
            f"source manifest {feature}",
        )
        approved = _mapping(approved_sources[SOURCE_PROPOSAL_KEYS[feature]], feature)
        attempts = _sequence(item["attempts"], f"{feature} attempts")
        if not attempts:
            raise Run010Error(f"Run 010 source manifest lacks attempts: {feature}")
        for expected_attempt, attempt_value in enumerate(attempts, start=1):
            attempt = _mapping(attempt_value, f"{feature} attempt")
            status = attempt.get("status")
            if attempt.get("attempt") != expected_attempt or status not in {
                "retryable_failure",
                "success",
            }:
                raise Run010Error(f"Run 010 source attempt audit is invalid: {feature}")
            if (status == "success") != (expected_attempt == len(attempts)):
                raise Run010Error(f"Run 010 source attempt sequence is invalid: {feature}")
        try:
            retrieved = datetime.fromisoformat(str(item["retrieved_at_utc"]))
        except ValueError as error:
            raise Run010Error(f"Run 010 retrieval timestamp is invalid: {feature}") from error
        if (
            str(item["url"]) != str(approved["url"])
            or str(item["series_key"]) != str(approved["series_key"])
            or not str(item["final_url"]).startswith("https://")
            or Path(str(item["path"])).name != SOURCE_FILENAMES[feature]
            or retrieved.tzinfo is None
            or len(str(item["sha256"])) != 64
            or int(item["bytes"]) < 1
        ):
            raise Run010Error(f"Run 010 source provenance differs from approval: {feature}")
        source = LatestSource(
            feature_id=feature,
            path=Path(str(item["path"])),
            url=str(item["url"]),
            series_key=str(item["series_key"]),
            sha256=str(item["sha256"]),
            bytes=int(item["bytes"]),
            retrieved_at_utc=str(item["retrieved_at_utc"]),
        )
        if (
            not source.path.is_file()
            or sha256_file(source.path) != source.sha256
            or source.path.stat().st_size != source.bytes
        ):
            raise Run010Error(f"Run 010 source artifact changed: {feature}")
        sources[feature] = source
    return sources


def load_run010_config(path: Path) -> Run010Config:
    """Load and validate the frozen empirical Run 010 configuration."""
    payload = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "Run 010 config")
    expected_fields = {
        "schema_version",
        "experiment_id",
        "evidence_status",
        "approved_design_path",
        "approved_design_sha256",
        "panel_path",
        "panel_sha256",
        "run009_diagnostic_path",
        "run009_diagnostic_sha256",
        "source_manifest_path",
        "source_manifest_sha256",
        "features",
        "factor_dimension",
        "rolling_months",
        "panel_start",
        "panel_end",
        "common_origin_start",
        "common_origin_end",
        "development_start",
        "development_end",
        "geometry_references",
        "bootstrap",
        "outcomes_accessed",
        "synthetic_observations_allowed",
        "run_010_execution_authorized",
        "transmission_outcome_execution_authorized",
    }
    _exact_fields(payload, expected_fields, "Run 010 config")
    if payload["schema_version"] != 1:
        raise Run010Error("Run 010 schema version must be one.")
    design = Path(str(payload["approved_design_path"]))
    if str(payload["approved_design_sha256"]) != APPROVED_DESIGN_SHA256:
        raise Run010Error("Run 010 approved-design hash differs from the frozen contract.")
    proposal = _approved_proposal(design)
    panel = Path(str(payload["panel_path"]))
    diagnostic = Path(str(payload["run009_diagnostic_path"]))
    source_manifest = Path(str(payload["source_manifest_path"]))
    for candidate, expected_hash, context in (
        (panel, str(payload["panel_sha256"]), "point-in-time panel"),
        (diagnostic, str(payload["run009_diagnostic_sha256"]), "Run 009 diagnostic"),
    ):
        if not candidate.is_file() or sha256_file(candidate) != expected_hash:
            raise Run010Error(f"Run 010 {context} is missing or has changed.")
    sources = _load_source_manifest(
        source_manifest, str(payload["source_manifest_sha256"]), proposal
    )
    reference = _mapping(payload["geometry_references"], "geometry references")
    bootstrap = _mapping(payload["bootstrap"], "bootstrap")
    _exact_fields(reference, set(GeometryReferences.__dataclass_fields__), "geometry references")
    _exact_fields(bootstrap, set(BootstrapContract.__dataclass_fields__), "bootstrap")
    config = Run010Config(
        config_sha256=sha256_file(path),
        experiment_id=str(payload["experiment_id"]),
        evidence_status=str(payload["evidence_status"]),
        approved_design_path=design,
        approved_design_sha256=APPROVED_DESIGN_SHA256,
        panel_path=panel,
        panel_sha256=str(payload["panel_sha256"]),
        run009_diagnostic_path=diagnostic,
        run009_diagnostic_sha256=str(payload["run009_diagnostic_sha256"]),
        source_manifest_path=source_manifest,
        source_manifest_sha256=str(payload["source_manifest_sha256"]),
        sources=sources,
        features=tuple(str(item) for item in _sequence(payload["features"], "features")),
        factor_dimension=_integer(payload["factor_dimension"], "factor_dimension"),
        rolling_months=tuple(
            _integer(item, "rolling month")
            for item in _sequence(payload["rolling_months"], "rolling_months")
        ),
        panel_start=str(payload["panel_start"]),
        panel_end=str(payload["panel_end"]),
        common_origin_start=str(payload["common_origin_start"]),
        common_origin_end=str(payload["common_origin_end"]),
        development_start=str(payload["development_start"]),
        development_end=str(payload["development_end"]),
        geometry_references=GeometryReferences(
            **{field: float(reference[field]) for field in GeometryReferences.__dataclass_fields__}
        ),
        bootstrap=BootstrapContract(
            replications=_integer(bootstrap["replications"], "bootstrap replications"),
            random_seed=_integer(bootstrap["random_seed"], "bootstrap seed"),
            primary_block_months=_integer(
                bootstrap["primary_block_months"], "primary block months"
            ),
            sensitivity_block_months=tuple(
                _integer(item, "sensitivity block months")
                for item in _sequence(
                    bootstrap["sensitivity_block_months"], "sensitivity block months"
                )
            ),
        ),
        outcomes_accessed=_boolean(payload["outcomes_accessed"], "outcomes_accessed"),
        synthetic_observations_allowed=_boolean(
            payload["synthetic_observations_allowed"], "synthetic_observations_allowed"
        ),
        run_010_execution_authorized=_boolean(
            payload["run_010_execution_authorized"], "run_010_execution_authorized"
        ),
        transmission_outcome_execution_authorized=_boolean(
            payload["transmission_outcome_execution_authorized"],
            "transmission_outcome_execution_authorized",
        ),
    )
    _validate_config(config)
    return config


def _validate_config(config: Run010Config) -> None:
    if (
        config.outcomes_accessed
        or config.synthetic_observations_allowed
        or not config.run_010_execution_authorized
        or config.transmission_outcome_execution_authorized
    ):
        raise Run010Error(
            "Run 010 must use real state data, remain outcome blind, and be authorized."
        )
    if config.features != FEATURES or config.factor_dimension != 2:
        raise Run010Error("Run 010 feature or factor contract changed.")
    if config.rolling_months != (96, 120, 144):
        raise Run010Error("Run 010 rolling windows changed.")
    if (
        config.bootstrap.replications < 1
        or config.bootstrap.primary_block_months < 1
        or not config.bootstrap.sensitivity_block_months
        or any(block < 1 for block in config.bootstrap.sensitivity_block_months)
    ):
        raise Run010Error("Run 010 bootstrap settings must be positive and complete.")
    expected_references = GeometryReferences(0.75, 0.90, 0.35, 0.35, 0.20, 1.00, 0.50)
    if config.geometry_references != expected_references:
        raise Run010Error("Run 010 geometry references changed.")
    if config.evidence_status == "REAL_DATA_OUTCOME_BLIND":
        if config.bootstrap != BootstrapContract(1999, 10092026, 12, (24, 36)):
            raise Run010Error("Run 010 empirical bootstrap contract changed.")
        if (
            config.experiment_id != "state-vintage-robustness-run010-v1"
            or config.panel_start != "month-2002-01"
            or config.panel_end != "month-2025-10"
            or config.common_origin_start != "month-2014-02"
            or config.common_origin_end != "month-2025-10"
            or config.development_start != "month-2002-01"
            or config.development_end != "month-2011-12"
        ):
            raise Run010Error("Run 010 empirical identity or calendar contract changed.")


def _panel_records(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    required = {
        "event_id",
        "state_cutoff_timestamp",
        "feature_id",
        "observation_period",
        "value",
        "missing",
    }
    records: dict[tuple[str, str], dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise Run010Error("Point-in-time panel schema is incomplete.")
        for row in reader:
            key = (row["event_id"], row["feature_id"])
            if key in records or row["missing"] not in {"True", "False"}:
                raise Run010Error("Point-in-time panel contains duplicate keys or bad flags.")
            missing = row["missing"] == "True"
            if missing != (row["value"] == ""):
                raise Run010Error("Point-in-time value and missing flag disagree.")
            records[key] = row
    return records


def _source_dimensions(feature: str, source: LatestSource) -> tuple[str, str, str, str, str, str]:
    if feature == "hicp_yoy":
        return ("M", "S0", "N", "P_C_OV", "X", source.series_key)
    if feature == "industrial_production_yoy":
        return ("M", "S0", "Y", "I_XCONS", "X", source.series_key)
    return ("M", "S0", "S", "L_UNETO", "F", source.series_key)


def _rankdata(values: FloatArray) -> FloatArray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=np.float64)
    start = 0
    while start < values.size:
        end = start + 1
        while end < values.size and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = (start + end - 1) / 2.0 + 1.0
        start = end
    return ranks


def _correlation(left: FloatArray, right: FloatArray) -> float:
    if left.size < 2 or np.std(left) < 1e-12 or np.std(right) < 1e-12:
        raise Run010Error("Run 010 correlation requires two variable series.")
    return float(np.corrcoef(left, right)[0, 1])


def _variant_specs(
    features: tuple[str, ...],
) -> tuple[tuple[str, Optional[str], tuple[int, ...]], ...]:
    return (
        ("full", None, tuple(range(len(features)))),
        *tuple(
            (
                f"omit_{feature}",
                feature,
                tuple(index for index, candidate in enumerate(features) if candidate != feature),
            )
            for feature in features
        ),
    )


def _geometry_rows(
    values: np.ndarray[Any, np.dtype[np.float64]],
    month_ids: tuple[str, ...],
    cutoff_timestamps: tuple[str, ...],
    panel_vintage: str,
    config: Run010Config,
) -> tuple[VintageGeometryRow, ...]:
    rows: list[VintageGeometryRow] = []
    references = config.geometry_references
    for variant, omitted, columns in _variant_specs(config.features):
        for window in config.rolling_months:
            for index in range(window + 1, len(month_ids)):
                geometry = gram_geometry(
                    values[:index, columns],
                    values[index - window : index, columns],
                    config.factor_dimension,
                )
                second_cosine = float(geometry.principal_cosines[1])
                projector = geometry.normalized_projector_distance
                core = (
                    second_cosine < references.core_second_cosine
                    or projector > references.core_projector_distance
                )
                min_gap = min(
                    geometry.expanding_relative_eigengap,
                    geometry.rolling_relative_eigengap,
                )
                weak = (
                    min_gap < references.weak_relative_eigengap
                    and geometry.perturbation_to_minimum_eigengap_ratio
                    > references.high_perturbation_to_gap_ratio
                )
                contribution = geometry.upper_triangle_drift_contribution
                diagonal = float(np.trace(contribution))
                rows.append(
                    VintageGeometryRow(
                        month_id=month_ids[index],
                        cutoff_timestamp=cutoff_timestamps[index],
                        panel_vintage=panel_vintage,
                        panel_variant=variant,
                        omitted_feature=omitted,
                        rolling_months=window,
                        primary_common_sample=(
                            config.common_origin_start
                            <= month_ids[index]
                            <= config.common_origin_end
                        ),
                        second_principal_cosine=second_cosine,
                        normalized_projector_distance=projector,
                        gram_spectral_distance=geometry.gram_spectral_distance,
                        gram_normalized_frobenius_distance=(
                            geometry.gram_normalized_frobenius_distance
                        ),
                        expanding_relative_eigengap=geometry.expanding_relative_eigengap,
                        rolling_relative_eigengap=geometry.rolling_relative_eigengap,
                        perturbation_to_minimum_eigengap_ratio=(
                            geometry.perturbation_to_minimum_eigengap_ratio
                        ),
                        off_diagonal_gram_drift_share=max(0.0, 1.0 - diagonal),
                        core_breach=core,
                        weak_identification_concurrent=weak,
                    )
                )
    return tuple(rows)


def _validate_point_geometry_against_run009(
    rows: tuple[VintageGeometryRow, ...], path: Path
) -> None:
    expected: dict[tuple[str, str, int], dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for source_row in csv.DictReader(stream):
            key = (
                source_row["month_id"],
                source_row["panel_variant"],
                int(source_row["rolling_months"]),
            )
            if key in expected:
                raise Run010Error("Frozen Run 009 diagnostic contains duplicate keys.")
            expected[key] = source_row
    if len(expected) != len(rows):
        raise Run010Error("Run 010 point-in-time geometry row count differs from Run 009.")
    metrics = (
        "second_principal_cosine",
        "normalized_projector_distance",
        "gram_spectral_distance",
        "gram_normalized_frobenius_distance",
        "expanding_relative_eigengap",
        "rolling_relative_eigengap",
        "perturbation_to_minimum_eigengap_ratio",
    )
    for row in rows:
        key = (row.month_id, row.panel_variant, row.rolling_months)
        source = expected.pop(key, None)
        if source is None:
            raise Run010Error(f"Run 010 point-in-time geometry key is new: {key}")
        for metric in metrics:
            if not math.isclose(
                float(getattr(row, metric)), float(source[metric]), rel_tol=2e-9, abs_tol=2e-10
            ):
                raise Run010Error(f"Run 010 does not reproduce Run 009 metric: {key}, {metric}")
        if row.core_breach != (source["core_breach"] == "True"):
            raise Run010Error(f"Run 010 does not reproduce Run 009 breach: {key}")
    if expected:
        raise Run010Error("Run 010 did not reproduce every Run 009 geometry row.")


def _summaries(rows: tuple[VintageGeometryRow, ...], config: Run010Config) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for vintage in ("point_in_time", "latest_vintage"):
        vintage_payload: dict[str, Any] = {}
        for variant, omitted, _ in _variant_specs(config.features):
            windows: dict[str, Any] = {}
            for window in config.rolling_months:
                selected = [
                    row
                    for row in rows
                    if row.panel_vintage == vintage
                    and row.panel_variant == variant
                    and row.rolling_months == window
                    and row.primary_common_sample
                ]
                cosines = np.asarray([row.second_principal_cosine for row in selected])
                projectors = np.asarray([row.normalized_projector_distance for row in selected])
                breaches = np.asarray([row.core_breach for row in selected], dtype=bool)
                concurrent = np.asarray(
                    [row.weak_identification_concurrent for row in selected], dtype=bool
                )
                p10 = float(np.percentile(cosines, 10.0))
                p90 = float(np.percentile(projectors, 90.0))
                coincidence = float(np.mean(concurrent[breaches])) if np.any(breaches) else 0.0
                windows[str(window)] = {
                    "common_origins": len(selected),
                    "second_principal_cosine_p10": _canonical_float(p10),
                    "projector_distance_p90": _canonical_float(p90),
                    "core_breach_rate": _canonical_float(float(np.mean(breaches))),
                    "weak_identification_coincidence_rate_among_breaches": _canonical_float(
                        coincidence
                    ),
                    "mean_off_diagonal_gram_drift_share": _canonical_float(
                        float(np.mean([row.off_diagonal_gram_drift_share for row in selected]))
                    ),
                    "window_specific_geometry_failure": (
                        p10 < config.geometry_references.summary_second_cosine_p10
                        and p90 > config.geometry_references.summary_projector_distance_p90
                    ),
                }
            vintage_payload[variant] = {"omitted_feature": omitted, "windows": windows}
        payload[vintage] = vintage_payload
    return payload


def _episode_rows(
    geometry_rows: tuple[VintageGeometryRow, ...], config: Run010Config
) -> tuple[VintageEpisodeRow, ...]:
    rows: list[VintageEpisodeRow] = []
    for vintage in ("point_in_time", "latest_vintage"):
        for variant, omitted, _ in _variant_specs(config.features):
            for window in config.rolling_months:
                selected = [
                    row
                    for row in geometry_rows
                    if row.panel_vintage == vintage
                    and row.panel_variant == variant
                    and row.rolling_months == window
                    and row.primary_common_sample
                ]
                episodes = detect_breach_episodes(
                    tuple(row.month_id for row in selected),
                    np.asarray([row.core_breach for row in selected], dtype=bool),
                    3,
                    3,
                )
                for number, episode in enumerate(episodes, start=1):
                    rows.append(
                        VintageEpisodeRow(
                            panel_vintage=vintage,
                            panel_variant=variant,
                            omitted_feature=omitted,
                            rolling_months=window,
                            episode_number=number,
                            start_month=episode.start_month,
                            end_month=episode.end_month,
                            duration_months=episode.duration_months,
                            breach_months=episode.breach_months,
                            open_at_sample_end=episode.open_at_sample_end,
                        )
                    )
    return tuple(rows)


def _episode_comparison(
    geometry_rows: tuple[VintageGeometryRow, ...],
    episodes: tuple[VintageEpisodeRow, ...],
    config: Run010Config,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for variant, _, _ in _variant_specs(config.features):
        windows: dict[str, Any] = {}
        for window in config.rolling_months:
            breach_sets: dict[str, set[str]] = {}
            episode_sets: dict[str, list[VintageEpisodeRow]] = {}
            for vintage in ("point_in_time", "latest_vintage"):
                breach_sets[vintage] = {
                    row.month_id
                    for row in geometry_rows
                    if row.panel_vintage == vintage
                    and row.panel_variant == variant
                    and row.rolling_months == window
                    and row.primary_common_sample
                    and row.core_breach
                }
                episode_sets[vintage] = [
                    row
                    for row in episodes
                    if row.panel_vintage == vintage
                    and row.panel_variant == variant
                    and row.rolling_months == window
                ]
            union = breach_sets["point_in_time"] | breach_sets["latest_vintage"]
            intersection = breach_sets["point_in_time"] & breach_sets["latest_vintage"]
            paired_episode_count = min(
                len(episode_sets["point_in_time"]), len(episode_sets["latest_vintage"])
            )
            windows[str(window)] = {
                "breach_month_jaccard_similarity": _canonical_float(
                    len(intersection) / len(union) if union else 1.0
                ),
                "point_in_time_episode_count": len(episode_sets["point_in_time"]),
                "latest_vintage_episode_count": len(episode_sets["latest_vintage"]),
                "paired_episode_boundaries": [
                    {
                        "episode_number": index + 1,
                        "onset_month_difference": _month_number(
                            episode_sets["latest_vintage"][index].start_month
                        )
                        - _month_number(episode_sets["point_in_time"][index].start_month),
                        "end_month_difference": _month_number(
                            episode_sets["latest_vintage"][index].end_month
                        )
                        - _month_number(episode_sets["point_in_time"][index].end_month),
                    }
                    for index in range(paired_episode_count)
                ],
            }
        payload[variant] = windows
    return payload


def _circular_indices(
    observations: int, block: int, rng: np.random.Generator
) -> np.ndarray[Any, np.dtype[np.int64]]:
    if observations < 1 or block < 1:
        raise Run010Error("Bootstrap observations and block length must be positive.")
    blocks = math.ceil(observations / block)
    starts = rng.integers(0, observations, size=blocks)
    indices = np.concatenate(
        [(start + np.arange(block, dtype=np.int64)) % observations for start in starts]
    )[:observations]
    return np.asarray(indices, dtype=np.int64)


def _observed_value(value: Optional[float], context: str) -> float:
    if value is None or not np.isfinite(value):
        raise Run010Error(f"Run 010 unexpectedly lacks an observed {context} value.")
    return float(value)


def _bootstrap_summary(
    geometry_rows: tuple[VintageGeometryRow, ...], config: Run010Config
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for window in config.rolling_months:
        paired: dict[str, list[VintageGeometryRow]] = {}
        for vintage in ("point_in_time", "latest_vintage"):
            paired[vintage] = [
                row
                for row in geometry_rows
                if row.panel_vintage == vintage
                and row.panel_variant == "full"
                and row.rolling_months == window
                and row.primary_common_sample
            ]
        if [row.month_id for row in paired["point_in_time"]] != [
            row.month_id for row in paired["latest_vintage"]
        ]:
            raise Run010Error("Bootstrap diagnostic sequences are not paired by month.")
        point_cos = np.asarray([row.second_principal_cosine for row in paired["point_in_time"]])
        latest_cos = np.asarray([row.second_principal_cosine for row in paired["latest_vintage"]])
        point_projector = np.asarray(
            [row.normalized_projector_distance for row in paired["point_in_time"]]
        )
        latest_projector = np.asarray(
            [row.normalized_projector_distance for row in paired["latest_vintage"]]
        )
        point_breach = np.asarray(
            [row.core_breach for row in paired["point_in_time"]], dtype=np.float64
        )
        latest_breach = np.asarray(
            [row.core_breach for row in paired["latest_vintage"]], dtype=np.float64
        )
        blocks_payload: dict[str, Any] = {}
        for block in (
            config.bootstrap.primary_block_months,
            *config.bootstrap.sensitivity_block_months,
        ):
            rng = np.random.default_rng(config.bootstrap.random_seed + window * 100 + block)
            draws = np.empty((config.bootstrap.replications, 3), dtype=np.float64)
            for draw in range(config.bootstrap.replications):
                index = _circular_indices(point_cos.size, block, rng)
                draws[draw] = (
                    np.percentile(latest_cos[index], 10.0) - np.percentile(point_cos[index], 10.0),
                    np.percentile(latest_projector[index], 90.0)
                    - np.percentile(point_projector[index], 90.0),
                    np.mean(latest_breach[index]) - np.mean(point_breach[index]),
                )
            names = (
                "second_principal_cosine_p10_difference",
                "projector_distance_p90_difference",
                "core_breach_rate_difference",
            )
            blocks_payload[str(block)] = {
                name: {
                    "lower_95": _canonical_float(float(np.percentile(draws[:, column], 2.5))),
                    "upper_95": _canonical_float(float(np.percentile(draws[:, column], 97.5))),
                }
                for column, name in enumerate(names)
            }
        payload[str(window)] = blocks_payload
    return payload


def run_run010(config: Run010Config) -> Run010Result:
    """Execute the approved outcome-blind matched-period latest-vintage comparison."""
    _validate_config(config)
    for path, expected, context in (
        (config.approved_design_path, config.approved_design_sha256, "design"),
        (config.panel_path, config.panel_sha256, "panel"),
        (config.run009_diagnostic_path, config.run009_diagnostic_sha256, "Run 009 diagnostic"),
        (config.source_manifest_path, config.source_manifest_sha256, "source manifest"),
    ):
        if sha256_file(path) != expected:
            raise Run010Error(f"Run 010 {context} changed after validation.")
    for feature, source_artifact in config.sources.items():
        if (
            not source_artifact.path.is_file()
            or sha256_file(source_artifact.path) != source_artifact.sha256
            or source_artifact.path.stat().st_size != source_artifact.bytes
        ):
            raise Run010Error(f"Run 010 source changed after validation: {feature}")
    matrix = load_monthly_matrix(config.panel_path, config.features)
    if matrix.month_ids[0] != config.panel_start or matrix.month_ids[-1] != config.panel_end:
        raise Run010Error("Run 010 panel boundaries differ from the frozen contract.")
    records = _panel_records(config.panel_path)
    if len(records) != len(matrix.month_ids) * len(config.features):
        raise Run010Error("Run 010 point-in-time panel is incomplete.")
    latest_levels = {
        feature: _validate_latest_series(
            source.path, source.series_key, _source_dimensions(feature, source)
        )
        for feature, source in config.sources.items()
    }
    development_mask = np.asarray(
        [config.development_start <= month <= config.development_end for month in matrix.month_ids]
    )
    scales: dict[str, float] = {}
    for column, feature in enumerate(config.features):
        observed = matrix.values[development_mask, column]
        observed = observed[np.isfinite(observed)]
        scale = float(np.std(observed, ddof=1))
        if observed.size < 2 or not np.isfinite(scale) or scale < 1e-12:
            raise Run010Error(f"Run 010 development scale is unidentified: {feature}")
        scales[feature] = scale
    latest_matrix = np.full_like(matrix.values, np.nan)
    comparison_rows: list[VintageComparisonRow] = []
    for row_index, month in enumerate(matrix.month_ids):
        for column, feature in enumerate(config.features):
            record = records[(month, feature)]
            original = matrix.values[row_index, column]
            missing = not np.isfinite(original)
            period = record["observation_period"]
            if feature == "deposit_facility_rate":
                latest = original
                source_key = "FM.D.U2.EUR.4F.KR.DFR.LEV"
                source_hash = record.get("source_artifact_sha256", "")
            elif missing:
                latest = float("nan")
                source_key = config.sources[feature].series_key
                source_hash = config.sources[feature].sha256
            else:
                source = latest_levels[feature]
                if period not in source:
                    raise Run010Error(
                        f"Latest-vintage source lacks required period: {feature}, {period}"
                    )
                if feature in {"hicp_yoy", "industrial_production_yoy"}:
                    lag = _previous_year(period)
                    if lag not in source or source[lag] <= 0.0:
                        raise Run010Error(
                            f"Latest-vintage source lacks valid YoY lag: {feature}, {lag}"
                        )
                    latest = 100.0 * (source[period] / source[lag] - 1.0)
                else:
                    latest = source[period]
                source_key = config.sources[feature].series_key
                source_hash = config.sources[feature].sha256
            if missing != (not np.isfinite(latest)):
                raise Run010Error("Run 010 latest-vintage missingness mask changed.")
            latest_matrix[row_index, column] = latest
            difference = None if missing else float(latest - original)
            comparison_rows.append(
                VintageComparisonRow(
                    month_id=month,
                    cutoff_timestamp=matrix.cutoff_timestamps[row_index],
                    feature_id=feature,
                    observation_period=period,
                    point_in_time_value=None if missing else float(original),
                    latest_vintage_value=None if missing else float(latest),
                    latest_minus_point_in_time=difference,
                    standardized_difference=(
                        None if difference is None else difference / scales[feature]
                    ),
                    originally_missing=missing,
                    latest_source_series_id=source_key,
                    latest_source_sha256=source_hash,
                    evidence_status="EX_POST_LATEST_VINTAGE_NOT_DECISION_TIME",
                )
            )
    if not np.array_equal(np.isnan(matrix.values), np.isnan(latest_matrix)):
        raise Run010Error("Run 010 missingness changed after construction.")
    point_geometry = _geometry_rows(
        matrix.values, matrix.month_ids, matrix.cutoff_timestamps, "point_in_time", config
    )
    _validate_point_geometry_against_run009(point_geometry, config.run009_diagnostic_path)
    latest_geometry = _geometry_rows(
        latest_matrix, matrix.month_ids, matrix.cutoff_timestamps, "latest_vintage", config
    )
    geometry_rows = (*point_geometry, *latest_geometry)
    summaries = _summaries(geometry_rows, config)
    episodes = _episode_rows(geometry_rows, config)
    value_summary: dict[str, Any] = {}
    for feature in MACRO_FEATURES:
        selected = [
            row
            for row in comparison_rows
            if row.feature_id == feature and not row.originally_missing
        ]
        point = np.asarray(
            [_observed_value(row.point_in_time_value, "point-in-time") for row in selected]
        )
        latest = np.asarray(
            [_observed_value(row.latest_vintage_value, "latest-vintage") for row in selected]
        )
        difference = latest - point
        standardized = difference / scales[feature]
        value_summary[feature] = {
            "compared_rows": len(selected),
            "unique_observation_periods": len({row.observation_period for row in selected}),
            "mean_signed_difference": _canonical_float(float(np.mean(difference))),
            "median_absolute_difference": _canonical_float(float(np.median(np.abs(difference)))),
            "ninetieth_percentile_absolute_difference": _canonical_float(
                float(np.percentile(np.abs(difference), 90.0))
            ),
            "maximum_absolute_difference": _canonical_float(float(np.max(np.abs(difference)))),
            "root_mean_squared_difference": _canonical_float(
                float(np.sqrt(np.mean(difference**2)))
            ),
            "pearson_correlation": _canonical_float(_correlation(point, latest)),
            "spearman_correlation": _canonical_float(
                _correlation(_rankdata(point), _rankdata(latest))
            ),
            "median_absolute_difference_in_development_standard_deviations": _canonical_float(
                float(np.median(np.abs(standardized)))
            ),
            "ninetieth_percentile_absolute_difference_in_development_standard_deviations": (
                _canonical_float(float(np.percentile(np.abs(standardized), 90.0)))
            ),
        }
    latest_failures = [
        bool(
            summaries["latest_vintage"]["full"]["windows"][str(window)][
                "window_specific_geometry_failure"
            ]
        )
        for window in config.rolling_months
    ]
    classification = (
        "LATEST_VINTAGE_ROBUST_INSTABILITY"
        if all(latest_failures)
        else "VINTAGE_SENSITIVE_INSTABILITY"
    )
    real_data = config.evidence_status == "REAL_DATA_OUTCOME_BLIND"
    audit = {
        "experiment_id": config.experiment_id,
        "evidence_status": (
            "REAL_DATA_OUTCOME_BLIND_EX_POST_LATEST_VINTAGE" if real_data else "SOFTWARE_TEST_ONLY"
        ),
        "config_sha256": config.config_sha256,
        "approved_design_sha256": config.approved_design_sha256,
        "point_in_time_panel_sha256": config.panel_sha256,
        "run009_diagnostic_sha256": config.run009_diagnostic_sha256,
        "source_manifest_sha256": config.source_manifest_sha256,
        "source_hashes": {feature: source.sha256 for feature, source in config.sources.items()},
        "comparison_rows": len(comparison_rows),
        "geometry_rows": len(geometry_rows),
        "episode_rows": len(episodes),
        "missingness_mask_exactly_preserved": True,
        "point_in_time_geometry_exactly_reproduced": True,
        "required_latest_level_and_yoy_lag_coverage": 1.0,
        "value_revision_summary": value_summary,
        "geometry_summary": summaries,
        "episode_comparison": _episode_comparison(geometry_rows, episodes, config),
        "dependent_summary_uncertainty": _bootstrap_summary(geometry_rows, config),
        "primary_classification": classification,
        "pure_numerical_revision_claim_allowed": False,
        "decision_time_state_use_allowed": False,
        "state_selection_performed": False,
        "run008_or_run009_decision_recalculated": False,
        "outcomes_accessed": False,
        "synthetic_observations_used": not real_data,
        "transmission_estimation_authorized": False,
    }
    return Run010Result(tuple(comparison_rows), geometry_rows, episodes, audit)


def _write_csv(rows: Sequence[Any], path: Path, fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(fields))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: _canonical_float(value) if isinstance(value, float) else value
                    for key, value in asdict(row).items()
                }
            )


def write_run010_outputs(
    result: Run010Result,
    comparison_path: Path,
    geometry_path: Path,
    episode_path: Path,
    audit_path: Path,
) -> None:
    """Atomically publish the complete Run 010 evidence bundle."""
    if not result.comparison_rows or not result.geometry_rows or not result.audit:
        raise Run010Error("Run 010 cannot write an incomplete evidence bundle.")
    paths = (comparison_path, geometry_path, episode_path, audit_path)
    if len(set(paths)) != len(paths):
        raise Run010Error("Run 010 output paths must be distinct.")
    if any(path.exists() for path in paths):
        raise Run010Error("Run 010 output artifacts are immutable and already exist.")
    temporary = tuple(path.with_suffix(path.suffix + ".part") for path in paths)
    if any(path.exists() for path in temporary):
        raise Run010Error("Run 010 found a stale temporary output.")
    try:
        _write_csv(
            result.comparison_rows,
            comparison_path,
            tuple(VintageComparisonRow.__dataclass_fields__),
        )
        _write_csv(
            result.geometry_rows,
            geometry_path,
            tuple(VintageGeometryRow.__dataclass_fields__),
        )
        _write_csv(result.episode_rows, episode_path, tuple(VintageEpisodeRow.__dataclass_fields__))
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.with_suffix(audit_path.suffix + ".part").write_text(
            json.dumps(result.audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except Exception:
        for path in temporary:
            path.unlink(missing_ok=True)
        raise
    for target, partial in zip(paths, temporary):
        partial.replace(target)
