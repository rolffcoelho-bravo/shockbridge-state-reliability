"""Run 020 series-history pilot validation and aggregate auditing."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import yaml

from shockbridge_state_risk.data.download import download_https, sha256_file


class SeriesHistoryError(ValueError):
    """Raised when the pilot manifest or a response violates the frozen contract."""


ALLOWED_TIMING_CLASSES = {
    "A_REPLAY_ELIGIBLE",
    "B_RELEASE_LAG_ELIGIBLE",
    "C_BUILD_FORWARD_ONLY",
    "D_INELIGIBLE",
    "PILOT_TO_CLASSIFY",
}

RETAINED_TIMING_CLASSES = {"A_REPLAY_ELIGIBLE", "B_RELEASE_LAG_ELIGIBLE"}

REQUIRED_CHANNELS = {
    "prices_and_expectations",
    "real_activity_and_labour",
    "policy_stance_and_money_market",
    "sovereign_curve_and_term_structure",
    "bank_funding_and_lending_rates",
    "credit_and_money_quantities",
    "financial_conditions_and_systemic_stress",
    "external_value_and_cross_border_conditions",
}

REQUIRED_SERIES_FIELDS = {
    "pilot_id",
    "full_series_key",
    "api_path",
    "channel",
    "panel_role",
    "expected_frequency",
    "expected_unit",
    "proposed_transformation",
    "sample_start",
    "sample_end",
    "expected_timing_class",
    "query_url",
    "series_locator",
}


@dataclass(frozen=True)
class SeriesPilotAudit:
    """Value-free aggregate audit for one official pilot response."""

    pilot_id: str
    full_series_key: str
    channel: str
    response_path: str
    response_bytes: int
    response_sha256: str
    rows: int
    distinct_observation_periods: int
    earliest_observation_period: str
    latest_observation_period: str
    frequencies: list[str]
    units: list[str]
    actions: dict[str, int]
    nonempty_valid_from_rows: int
    distinct_valid_from_timestamps: int
    earliest_valid_from: str | None
    latest_valid_from: str | None
    maximum_version_delay_days: int | None
    observed_timing_class: str
    timing_reason: str


@dataclass(frozen=True)
class Run020PilotAudit:
    """Aggregate audit for the complete frozen pilot."""

    audit_id: str
    manifest_id: str
    manifest_path: str
    manifest_sha256: str
    manifest_bytes: int
    series_count: int
    channel_count: int
    timing_class_counts: dict[str, int]
    panel_results: list[dict[str, Any]]
    all_series: list[SeriesPilotAudit]
    synthetic_empirical_observations_used: bool
    transmission_outcomes_accessed: bool
    state_estimation_performed: bool
    passed: bool


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SeriesHistoryError(f"{label} must be a mapping")
    return value


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SeriesHistoryError(f"{label} must be a nonempty string")
    return value.strip()


def _validate_official_url(value: object, label: str, expected_host: str) -> str:
    url = _nonempty(value, label)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != expected_host:
        raise SeriesHistoryError(f"{label} must use official host {expected_host}")
    if not parsed.path or parsed.path == "/":
        raise SeriesHistoryError(f"{label} must include a non-root path")
    return url


def load_and_validate_series_manifest(path: Path) -> dict[str, Any]:
    """Load the frozen manifest and reject silent scope or timing changes."""

    payload = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "manifest")
    if payload.get("status") != "FROZEN_BEFORE_PILOT_OBSERVATION_RETRIEVAL":
        raise SeriesHistoryError("manifest must be frozen before pilot retrieval")
    if payload.get("real_official_data_only") is not True:
        raise SeriesHistoryError("pilot requires real official data only")
    if payload.get("synthetic_empirical_observations_allowed") is not False:
        raise SeriesHistoryError("synthetic empirical observations must be prohibited")
    if payload.get("transmission_outcomes_allowed") is not False:
        raise SeriesHistoryError("transmission outcomes must remain prohibited")
    service_root = _validate_official_url(
        payload.get("service_root"), "service_root", "data-api.ecb.europa.eu"
    ).rstrip("/")
    _validate_official_url(payload.get("rights_locator"), "rights_locator", "www.ecb.europa.eu")

    limits = _mapping(payload.get("pilot_limits"), "pilot_limits")
    maximum_bytes = limits.get("maximum_response_bytes_per_series")
    if type(maximum_bytes) is not int or maximum_bytes <= 0:
        raise SeriesHistoryError("maximum response bytes must be a positive integer")
    if limits.get("state_estimation") != "prohibited":
        raise SeriesHistoryError("pilot state estimation must be prohibited")

    raw_series = payload.get("series")
    if not isinstance(raw_series, list) or len(raw_series) < 2:
        raise SeriesHistoryError("pilot must register at least two series")

    identifiers: set[str] = set()
    keys: set[str] = set()
    for index, raw in enumerate(raw_series):
        series = _mapping(raw, f"series {index}")
        missing = sorted(REQUIRED_SERIES_FIELDS - set(series))
        if missing:
            raise SeriesHistoryError(f"series {index} missing fields: {missing}")
        pilot_id = _nonempty(series["pilot_id"], f"series {index} pilot_id")
        full_key = _nonempty(series["full_series_key"], f"{pilot_id} full_series_key")
        if pilot_id in identifiers or full_key in keys:
            raise SeriesHistoryError("pilot identifiers and full series keys must be unique")
        identifiers.add(pilot_id)
        keys.add(full_key)
        channel = _nonempty(series["channel"], f"{pilot_id} channel")
        if channel not in REQUIRED_CHANNELS:
            raise SeriesHistoryError(f"{pilot_id} has unknown channel {channel}")
        timing_class = _nonempty(
            series["expected_timing_class"], f"{pilot_id} expected_timing_class"
        )
        if timing_class not in ALLOWED_TIMING_CLASSES:
            raise SeriesHistoryError(f"{pilot_id} has unknown timing class")

        api_path = _nonempty(series["api_path"], f"{pilot_id} api_path")
        query_url = _validate_official_url(
            series["query_url"], f"{pilot_id} query_url", "data-api.ecb.europa.eu"
        )
        parsed = urlparse(query_url)
        if parsed.path.rstrip("/") != f"{urlparse(service_root).path.rstrip('/')}/{api_path}":
            raise SeriesHistoryError(f"{pilot_id} query path does not match api_path")
        query = parse_qs(parsed.query)
        if query.get("includeHistory") != ["true"] or query.get("format") != ["csvdata"]:
            raise SeriesHistoryError(f"{pilot_id} must request CSV history explicitly")
        if query.get("startPeriod") != [str(series["sample_start"])] or query.get("endPeriod") != [
            str(series["sample_end"])
        ]:
            raise SeriesHistoryError(f"{pilot_id} query period differs from frozen sample")
        _validate_official_url(
            series["series_locator"], f"{pilot_id} series_locator", "data.ecb.europa.eu"
        )

    panels = payload.get("candidate_panels")
    if not isinstance(panels, list) or len(panels) < 2:
        raise SeriesHistoryError("at least two candidate panels are required")
    panel_ids: set[str] = set()
    resolved: dict[str, list[str]] = {}
    for index, raw in enumerate(panels):
        panel = _mapping(raw, f"panel {index}")
        panel_id = _nonempty(panel.get("panel_id"), f"panel {index} panel_id")
        if panel_id in panel_ids:
            raise SeriesHistoryError(f"duplicate panel_id: {panel_id}")
        panel_ids.add(panel_id)
        if "extends" in panel:
            parent = _nonempty(panel["extends"], f"{panel_id} extends")
            if parent not in resolved:
                raise SeriesHistoryError(f"{panel_id} extends an unknown or later panel")
            additions = panel.get("additional_series_ids")
            if not isinstance(additions, list) or not additions:
                raise SeriesHistoryError(f"{panel_id} requires additional_series_ids")
            members = [*resolved[parent], *map(str, additions)]
        else:
            members_raw = panel.get("series_ids")
            if not isinstance(members_raw, list) or not members_raw:
                raise SeriesHistoryError(f"{panel_id} requires series_ids")
            members = list(map(str, members_raw))
        if len(members) != len(set(members)):
            raise SeriesHistoryError(f"{panel_id} contains duplicate series")
        unknown = sorted(set(members) - identifiers)
        if unknown:
            raise SeriesHistoryError(f"{panel_id} references unknown series: {unknown}")
        resolved[panel_id] = members

    if len({tuple(members) for members in resolved.values()}) != len(resolved):
        raise SeriesHistoryError("candidate panels must be substantively distinct")
    return payload


def _parse_iso_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SeriesHistoryError(f"invalid VALID_FROM timestamp: {value}") from exc


def _parse_period_start(value: str) -> date:
    try:
        if len(value) == 7:
            return date.fromisoformat(f"{value}-01")
        return date.fromisoformat(value[:10])
    except ValueError as exc:
        raise SeriesHistoryError(f"unsupported observation period: {value}") from exc


def classify_timing(
    expected_class: str,
    observation_periods: list[str],
    valid_from_values: list[str],
) -> tuple[str, str, int | None]:
    """Classify timing without using observation values or model results."""

    if expected_class == "C_BUILD_FORWARD_ONLY":
        return expected_class, "frozen forward-only classification", None
    if expected_class == "D_INELIGIBLE":
        return expected_class, "frozen ineligible classification", None

    if len(observation_periods) != len(valid_from_values):
        raise SeriesHistoryError("timing arrays must have equal length")
    parsed_valid = [_parse_iso_datetime(value) for value in valid_from_values]
    pairs = [
        (_parse_period_start(period), valid)
        for period, valid in zip(observation_periods, parsed_valid)
        if valid is not None
    ]
    maximum_delay = max(((valid.date() - period).days for period, valid in pairs), default=None)

    if expected_class == "A_REPLAY_ELIGIBLE":
        if len(pairs) != len(observation_periods):
            return (
                "D_INELIGIBLE",
                "expected replay series lacks VALID_FROM on one or more rows",
                maximum_delay,
            )
        return expected_class, "archived/API history timestamps present on every row", maximum_delay

    if expected_class == "B_RELEASE_LAG_ELIGIBLE":
        return expected_class, "frozen release-lag treatment retained", maximum_delay

    if pairs and maximum_delay is not None and maximum_delay <= 7:
        return (
            "A_REPLAY_ELIGIBLE",
            "dated market observations have history timestamps within seven days",
            maximum_delay,
        )
    return (
        "B_RELEASE_LAG_ELIGIBLE",
        "exact decision-time history is incomplete; conservative release lag required",
        maximum_delay,
    )


def _portable_path(path: Path, canonical_root: Path | None) -> str:
    """Return a portable path and reject data outside the canonical project."""

    resolved = path.resolve()
    if canonical_root is None:
        return resolved.name
    try:
        return resolved.relative_to(canonical_root.resolve()).as_posix()
    except ValueError as exc:
        message = f"artifact is outside the canonical project: {resolved.name}"
        raise SeriesHistoryError(message) from exc


def _project_root_from_manifest(manifest_path: Path) -> Path:
    """Locate the nearest project root without serializing host-specific paths."""

    for parent in (manifest_path.resolve().parent, *manifest_path.resolve().parents):
        if (parent / "pyproject.toml").is_file():
            return parent
    raise SeriesHistoryError("manifest is not inside a project with pyproject.toml")


def audit_series_response(
    spec: dict[str, Any],
    path: Path,
    maximum_bytes: int,
    canonical_root: Path | None = None,
) -> SeriesPilotAudit:
    """Audit one response and retain no observation values in the result."""

    size = path.stat().st_size
    if size > maximum_bytes:
        raise SeriesHistoryError(f"{spec['pilot_id']} response exceeds the frozen byte limit")
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        fields = set(reader.fieldnames or [])
        required = {"KEY", "FREQ", "TIME_PERIOD", "OBS_VALUE"}
        if not required.issubset(fields):
            raise SeriesHistoryError(
                f"{spec['pilot_id']} response lacks columns: {sorted(required - fields)}"
            )
        rows = list(reader)
    if not rows:
        raise SeriesHistoryError(f"{spec['pilot_id']} response contains no rows")
    if {row["KEY"] for row in rows} != {spec["full_series_key"]}:
        raise SeriesHistoryError(f"{spec['pilot_id']} response key differs from the manifest")
    frequencies = sorted({row["FREQ"] for row in rows})
    if frequencies != [spec["expected_frequency"]]:
        raise SeriesHistoryError(f"{spec['pilot_id']} response frequency differs from the manifest")
    periods = [row["TIME_PERIOD"] for row in rows]
    if any(not row["OBS_VALUE"].strip() for row in rows):
        raise SeriesHistoryError(f"{spec['pilot_id']} contains an empty pilot observation")
    units = sorted({row.get("UNIT", "").strip() for row in rows if row.get("UNIT", "").strip()})
    if units != [spec["expected_unit"]]:
        raise SeriesHistoryError(
            f"{spec['pilot_id']} response unit differs from the manifest: {units!r}"
        )
    valid_from = [row.get("VALID_FROM", "").strip() for row in rows]
    nonempty_valid = [value for value in valid_from if value]
    timing_class, timing_reason, maximum_delay = classify_timing(
        spec["expected_timing_class"], periods, valid_from
    )
    actions = Counter(row.get("ACTION", "").strip() or "NOT_REPORTED" for row in rows)
    return SeriesPilotAudit(
        pilot_id=spec["pilot_id"],
        full_series_key=spec["full_series_key"],
        channel=spec["channel"],
        response_path=_portable_path(path, canonical_root),
        response_bytes=size,
        response_sha256=sha256_file(path),
        rows=len(rows),
        distinct_observation_periods=len(set(periods)),
        earliest_observation_period=min(periods),
        latest_observation_period=max(periods),
        frequencies=frequencies,
        units=units,
        actions=dict(sorted(actions.items())),
        nonempty_valid_from_rows=len(nonempty_valid),
        distinct_valid_from_timestamps=len(set(nonempty_valid)),
        earliest_valid_from=min(nonempty_valid) if nonempty_valid else None,
        latest_valid_from=max(nonempty_valid) if nonempty_valid else None,
        maximum_version_delay_days=maximum_delay,
        observed_timing_class=timing_class,
        timing_reason=timing_reason,
    )


def _resolve_panels(payload: dict[str, Any]) -> dict[str, list[str]]:
    resolved: dict[str, list[str]] = {}
    for raw in payload["candidate_panels"]:
        panel = _mapping(raw, "panel")
        panel_id = str(panel["panel_id"])
        if "extends" in panel:
            resolved[panel_id] = [
                *resolved[str(panel["extends"])],
                *map(str, panel["additional_series_ids"]),
            ]
        else:
            resolved[panel_id] = list(map(str, panel["series_ids"]))
    return resolved


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _assemble_pilot_audit(
    manifest_path: Path,
    payload: dict[str, Any],
    audits: list[SeriesPilotAudit],
    audit_output: Path,
) -> Run020PilotAudit:
    """Assemble panel gates and write the immutable aggregate audit."""

    if audit_output.exists():
        raise SeriesHistoryError(f"refusing to overwrite existing audit: {audit_output}")
    canonical_root = _project_root_from_manifest(manifest_path)
    audit_by_id = {audit.pilot_id: audit for audit in audits}
    spec_by_id = {str(spec["pilot_id"]): spec for spec in payload["series"]}
    resolved_panels = _resolve_panels(payload)
    panel_results: list[dict[str, Any]] = []
    passed = True
    for panel in payload["candidate_panels"]:
        panel_id = str(panel["panel_id"])
        members = resolved_panels[panel_id]
        retained = [
            member
            for member in members
            if audit_by_id[member].observed_timing_class in RETAINED_TIMING_CLASSES
        ]
        channel_count = len({str(spec_by_id[member]["channel"]) for member in retained})
        minimum_channels = int(panel["required_distinct_channels"])
        panel_passed = len(retained) == len(members) and channel_count >= minimum_channels
        passed = passed and panel_passed
        panel_results.append(
            {
                "panel_id": panel_id,
                "declared_series": members,
                "retained_series": retained,
                "distinct_channels": channel_count,
                "required_distinct_channels": minimum_channels,
                "passed": panel_passed,
            }
        )

    counts = Counter(audit.observed_timing_class for audit in audits)
    result = Run020PilotAudit(
        audit_id="run-020-series-history-pilot-v1",
        manifest_id=str(payload["manifest_id"]),
        manifest_path=_portable_path(manifest_path, canonical_root),
        manifest_sha256=sha256_file(manifest_path),
        manifest_bytes=manifest_path.stat().st_size,
        series_count=len(audits),
        channel_count=len({audit.channel for audit in audits}),
        timing_class_counts=dict(sorted(counts.items())),
        panel_results=panel_results,
        all_series=audits,
        synthetic_empirical_observations_used=False,
        transmission_outcomes_accessed=False,
        state_estimation_performed=False,
        passed=passed,
    )
    _write_json_atomic(audit_output, asdict(result))
    return result


def audit_existing_series_pilot(
    manifest_path: Path,
    raw_directory: Path,
    audit_output: Path,
) -> Run020PilotAudit:
    """Re-audit immutable downloaded bytes after a metadata-only amendment."""

    payload = load_and_validate_series_manifest(manifest_path)
    canonical_root = _project_root_from_manifest(manifest_path)
    limits = _mapping(payload["pilot_limits"], "pilot_limits")
    maximum_bytes = int(limits["maximum_response_bytes_per_series"])
    audits: list[SeriesPilotAudit] = []
    for raw in payload["series"]:
        spec = _mapping(raw, "series")
        response = raw_directory / f"{spec['pilot_id'].lower()}.csv"
        if not response.is_file():
            raise SeriesHistoryError(f"missing frozen pilot response: {response}")
        audits.append(audit_series_response(spec, response, maximum_bytes, canonical_root))
    return _assemble_pilot_audit(manifest_path, payload, audits, audit_output)


def fetch_and_audit_series_pilot(
    manifest_path: Path,
    raw_directory: Path,
    audit_output: Path,
) -> Run020PilotAudit:
    """Fetch the exact frozen samples once and write a value-free aggregate audit."""

    payload = load_and_validate_series_manifest(manifest_path)
    canonical_root = _project_root_from_manifest(manifest_path)
    limits = _mapping(payload["pilot_limits"], "pilot_limits")
    maximum_bytes = int(limits["maximum_response_bytes_per_series"])
    audits: list[SeriesPilotAudit] = []
    for raw in payload["series"]:
        spec = _mapping(raw, "series")
        destination = raw_directory / f"{spec['pilot_id'].lower()}.csv"
        if destination.exists():
            raise SeriesHistoryError(f"refusing to overwrite existing response: {destination}")
        download_https(str(spec["query_url"]), destination)
        audits.append(audit_series_response(spec, destination, maximum_bytes, canonical_root))

    return _assemble_pilot_audit(manifest_path, payload, audits, audit_output)
