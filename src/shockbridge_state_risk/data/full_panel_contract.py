"""Fail-closed validation for the frozen Run 021 full-panel contract."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import yaml


class FullPanelContractError(ValueError):
    """Raised when the Run 021 protocol or manifest is incomplete or changed."""


EXPECTED_SERIES_IDS = {
    "RTD_HICP",
    "RTD_INDUSTRIAL_PRODUCTION",
    "RTD_UNEMPLOYMENT",
    "ECB_DEPOSIT_FACILITY_RATE",
    "ECB_YIELD_CURVE_2Y",
    "ECB_YIELD_CURVE_10Y",
    "ECB_USD_EUR_REFERENCE_RATE",
    "MIR_NFC_COST_OF_BORROWING",
    "BSI_NFC_ADJUSTED_LOANS",
    "BSI_MONETARY_AGGREGATE_M3",
}

EXPECTED_QUERY_PERIODS = {
    "RTD_HICP": ("2002-01", "2025-10"),
    "RTD_INDUSTRIAL_PRODUCTION": ("2002-01", "2025-10"),
    "RTD_UNEMPLOYMENT": ("2002-01", "2025-10"),
    "ECB_DEPOSIT_FACILITY_RATE": ("2002-01-01", "2025-10-31"),
    "ECB_YIELD_CURVE_2Y": ("2002-01-01", "2025-10-31"),
    "ECB_YIELD_CURVE_10Y": ("2002-01-01", "2025-10-31"),
    "ECB_USD_EUR_REFERENCE_RATE": ("2002-01-01", "2025-10-31"),
    "MIR_NFC_COST_OF_BORROWING": ("2003-01", "2025-10"),
    "BSI_NFC_ADJUSTED_LOANS": ("2003-01", "2025-10"),
    "BSI_MONETARY_AGGREGATE_M3": ("2003-01", "2025-10"),
}

ALLOWED_CHANNELS = {
    "prices_and_expectations",
    "real_activity_and_labour",
    "policy_stance_and_money_market",
    "sovereign_curve_and_term_structure",
    "bank_funding_and_lending_rates",
    "credit_and_money_quantities",
    "external_value_and_cross_border_conditions",
}

ALLOWED_TIMING_CLASSES = {"A_REPLAY_ELIGIBLE", "B_RELEASE_LAG_ELIGIBLE"}
OFFICIAL_HOSTS = {
    "data-api.ecb.europa.eu",
    "data.ecb.europa.eu",
    "www.ecb.europa.eu",
}


@dataclass(frozen=True)
class FullPanelContractAudit:
    """Value-free Run 021 preflight result."""

    audit_id: str
    protocol_id: str
    manifest_id: str
    protocol_path: str
    protocol_sha256: str
    manifest_path: str
    manifest_sha256: str
    bound_inputs_verified: int
    series_count: int
    panel_count: int
    channel_count: int
    timing_class_counts: dict[str, int]
    maximum_scenarios_before_deduplication: int
    evaluation_labels_matured: bool
    full_history_retrieval_performed: bool
    state_estimation_performed: bool
    transmission_outcomes_accessed: bool
    synthetic_empirical_observations_used: bool
    passed: bool


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FullPanelContractError(f"{label} must be a mapping")
    return value


def _list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise FullPanelContractError(f"{label} must be a nonempty list")
    return value


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FullPanelContractError(f"{label} must be a nonempty string")
    return value.strip()


def _exact_bool(value: object, expected: bool, label: str) -> None:
    if value is not expected:
        raise FullPanelContractError(f"{label} must be {expected}")


def _positive_int(value: object, label: str, *, allow_zero: bool = False) -> int:
    if type(value) is not int or value < (0 if allow_zero else 1):
        qualifier = "nonnegative" if allow_zero else "positive"
        raise FullPanelContractError(f"{label} must be a {qualifier} integer")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_root(path: Path) -> Path:
    for candidate in (path.resolve().parent, *path.resolve().parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise FullPanelContractError("cannot locate project root containing pyproject.toml")


def _inside(root: Path, relative: str, label: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise FullPanelContractError(f"{label} escapes the project root") from error
    return candidate


def _official_url(value: object, label: str, *, api: bool = False) -> str:
    url = _nonempty(value, label)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in OFFICIAL_HOSTS:
        raise FullPanelContractError(f"{label} must use an approved official HTTPS host")
    if api and parsed.hostname != "data-api.ecb.europa.eu":
        raise FullPanelContractError(f"{label} must use the ECB data API host")
    if not parsed.path or parsed.path == "/":
        raise FullPanelContractError(f"{label} must include a non-root path")
    return url


def _parse_month(value: object, label: str) -> tuple[int, int]:
    text = _nonempty(value, label)
    try:
        parsed = date.fromisoformat(f"{text}-01")
    except ValueError as error:
        raise FullPanelContractError(f"{label} must use YYYY-MM") from error
    return parsed.year, parsed.month


def _month_index(value: object, label: str) -> int:
    year, month = _parse_month(value, label)
    return year * 12 + month - 1


def _resolve_pilot_panels(payload: dict[str, Any]) -> dict[str, list[str]]:
    resolved: dict[str, list[str]] = {}
    for raw in _list(payload.get("candidate_panels"), "pilot candidate_panels"):
        panel = _mapping(raw, "pilot panel")
        panel_id = _nonempty(panel.get("panel_id"), "pilot panel_id")
        if "extends" in panel:
            parent = _nonempty(panel.get("extends"), f"{panel_id} extends")
            if parent not in resolved:
                raise FullPanelContractError(f"pilot panel {panel_id} has unknown parent")
            additions = [
                str(value) for value in _list(panel.get("additional_series_ids"), "additions")
            ]
            resolved[panel_id] = [*resolved[parent], *additions]
        else:
            resolved[panel_id] = [
                str(value) for value in _list(panel.get("series_ids"), "pilot series_ids")
            ]
    return resolved


def _validate_bound_inputs(protocol: dict[str, Any], root: Path) -> int:
    entries = _list(protocol.get("bound_inputs"), "bound_inputs")
    seen: set[str] = set()
    for index, raw in enumerate(entries):
        entry = _mapping(raw, f"bound input {index}")
        relative = _nonempty(entry.get("path"), f"bound input {index} path")
        expected = _nonempty(entry.get("sha256"), f"bound input {index} sha256")
        if len(expected) != 64 or any(
            character not in "0123456789abcdef" for character in expected
        ):
            raise FullPanelContractError(f"bound input {relative} must have an exact SHA-256")
        if relative in seen:
            raise FullPanelContractError(f"duplicate bound input: {relative}")
        seen.add(relative)
        path = _inside(root, relative, f"bound input {relative}")
        if not path.is_file() or _sha256(path) != expected:
            raise FullPanelContractError(f"bound input hash mismatch: {relative}")
    return len(entries)


def _validate_protocol(protocol: dict[str, Any]) -> tuple[str, bool, int]:
    if protocol.get("status") != "APPROVED_AND_FROZEN_BEFORE_FULL_RETRIEVAL":
        raise FullPanelContractError("protocol must be frozen before full retrieval")
    protocol_id = _nonempty(protocol.get("protocol_id"), "protocol_id")
    boundary = _mapping(protocol.get("scientific_boundary"), "scientific_boundary")
    _exact_bool(boundary.get("real_official_data_only"), True, "real_official_data_only")
    _exact_bool(
        boundary.get("synthetic_empirical_observations_allowed"),
        False,
        "synthetic_empirical_observations_allowed",
    )
    _exact_bool(
        boundary.get("transmission_outcomes_access_allowed"),
        False,
        "transmission_outcomes_access_allowed",
    )
    _exact_bool(
        boundary.get("full_history_retrieval_allowed_in_run_021"),
        False,
        "full_history_retrieval_allowed_in_run_021",
    )
    _exact_bool(
        boundary.get("state_estimation_allowed_in_run_021"),
        False,
        "state_estimation_allowed_in_run_021",
    )

    estimator = _mapping(protocol.get("factor_estimator"), "factor_estimator")
    if estimator.get("implementation_status") != "NOT_IMPLEMENTED":
        raise FullPanelContractError("Run 021 estimator must remain unimplemented")
    if estimator.get("candidate_ranks") != [1, 2, 3]:
        raise FullPanelContractError("candidate ranks must remain [1, 2, 3]")
    rank = _mapping(estimator.get("rank_selection"), "rank_selection")
    if rank.get("name") != "observed_entry_ICp2_adaptation":
        raise FullPanelContractError("ragged-edge rank rule must be explicit")
    if rank.get("language_boundary") != "adaptation_not_textbook_Bai_Ng_under_balanced_data":
        raise FullPanelContractError("rank-rule language boundary is required")

    scenarios = _mapping(
        protocol.get("admissible_information_set_generator"),
        "admissible_information_set_generator",
    )
    declared_maximum = _positive_int(
        scenarios.get("maximum_scenarios_before_deduplication"),
        "maximum_scenarios_before_deduplication",
    )
    expected_maximum = (1 + 5 + 1 + 7) * 2 * 2
    if declared_maximum != expected_maximum:
        raise FullPanelContractError(
            f"maximum scenarios must equal deterministic generator count {expected_maximum}"
        )

    validation = _mapping(protocol.get("chronological_validation"), "chronological_validation")
    evaluation_end = _month_index(validation.get("evaluation_end"), "evaluation_end")
    diagnostic_end = _month_index(validation.get("diagnostic_tail_end"), "diagnostic_tail_end")
    matured = evaluation_end + 12 <= diagnostic_end
    if not matured or validation.get("every_evaluation_label_matured") is not True:
        raise FullPanelContractError("every 12-month evaluation label must be matured")
    if validation.get("evaluation_once_only") is not True:
        raise FullPanelContractError("evaluation must be one-time only")

    reference = _mapping(
        protocol.get("within_panel_reference_failure"), "within_panel_reference_failure"
    )
    if reference.get("candidate_envelope_thresholds_do_not_enter_label") is not True:
        raise FullPanelContractError("future failure label must be threshold-independent")
    if "months_t_plus_1_through_t_plus_12" not in str(reference.get("future_failure_label")):
        raise FullPanelContractError("future failure horizon must be exactly 12 months")
    return protocol_id, matured, declared_maximum


def _validate_manifest(
    manifest: dict[str, Any], pilot: dict[str, Any]
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    if manifest.get("status") != "FROZEN_BEFORE_FULL_RETRIEVAL":
        raise FullPanelContractError("manifest must be frozen before full retrieval")
    manifest_id = _nonempty(manifest.get("manifest_id"), "manifest_id")
    _exact_bool(manifest.get("real_official_data_only"), True, "real_official_data_only")
    _exact_bool(
        manifest.get("synthetic_empirical_observations_allowed"),
        False,
        "synthetic_empirical_observations_allowed",
    )
    _exact_bool(
        manifest.get("transmission_outcomes_allowed"),
        False,
        "transmission_outcomes_allowed",
    )
    _official_url(manifest.get("service_root"), "service_root", api=True)
    _official_url(manifest.get("rights_locator"), "rights_locator")

    retrieval = _mapping(manifest.get("retrieval_contract"), "retrieval_contract")
    _exact_bool(
        retrieval.get("retrieval_allowed_in_run_021"),
        False,
        "retrieval_allowed_in_run_021",
    )
    _exact_bool(
        retrieval.get("next_stage_requires_separate_owner_approval"),
        True,
        "next_stage_requires_separate_owner_approval",
    )
    _positive_int(retrieval.get("maximum_response_bytes_per_series"), "maximum response bytes")
    if retrieval.get("response_hash_state_before_retrieval") != "PENDING_NOT_INVENTED":
        raise FullPanelContractError("pre-retrieval response hashes must remain explicitly pending")

    for name, url in _mapping(manifest.get("release_sources"), "release_sources").items():
        if name != "rule":
            _official_url(url, f"release_sources.{name}")

    raw_series = _list(manifest.get("series"), "series")
    pilot_series = {
        str(item["pilot_id"]): _mapping(item, "pilot series")
        for item in _list(pilot.get("series"), "pilot series")
    }
    if len(raw_series) != 10:
        raise FullPanelContractError(
            "full panel manifest must contain exactly ten pilot-qualified series"
        )
    identifiers: set[str] = set()
    keys: set[str] = set()
    filenames: set[str] = set()
    parsed_series: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_series):
        series = _mapping(raw, f"series {index}")
        series_id = _nonempty(series.get("series_id"), f"series {index} series_id")
        full_key = _nonempty(series.get("full_series_key"), f"{series_id} full_series_key")
        filename = _nonempty(series.get("filename"), f"{series_id} filename")
        if Path(filename).name != filename or not filename.endswith(".csv"):
            raise FullPanelContractError(f"{series_id} filename must be a plain CSV name")
        if series_id in identifiers or full_key in keys or filename in filenames:
            raise FullPanelContractError("series identifiers, keys, and filenames must be unique")
        identifiers.add(series_id)
        keys.add(full_key)
        filenames.add(filename)
        if series.get("channel") not in ALLOWED_CHANNELS:
            raise FullPanelContractError(f"{series_id} has an unknown channel")
        if series.get("timing_class") not in ALLOWED_TIMING_CLASSES:
            raise FullPanelContractError(f"{series_id} has an ineligible timing class")
        sign = series.get("sign")
        if type(sign) is not int or sign not in {-1, 1}:
            raise FullPanelContractError(f"{series_id} sign must be exactly -1 or 1")
        _positive_int(
            series.get("transformation_lookback_periods"),
            f"{series_id} transformation lookback",
            allow_zero=True,
        )
        if series.get("response_sha256") != "PENDING_NOT_INVENTED":
            raise FullPanelContractError(f"{series_id} pre-retrieval hash must remain pending")
        query_url = _official_url(series.get("query_url"), f"{series_id} query_url", api=True)
        parsed = urlparse(query_url)
        api_path = _nonempty(series.get("api_path"), f"{series_id} api_path")
        if not parsed.path.endswith(f"/service/data/{api_path}"):
            raise FullPanelContractError(f"{series_id} query path differs from api_path")
        query = parse_qs(parsed.query)
        if query.get("includeHistory") != ["true"] or query.get("format") != ["csvdata"]:
            raise FullPanelContractError(f"{series_id} query must request explicit CSV history")
        if set(query) != {"includeHistory", "format", "startPeriod", "endPeriod"}:
            raise FullPanelContractError(f"{series_id} query has unregistered parameters")
        if series_id not in EXPECTED_QUERY_PERIODS:
            raise FullPanelContractError(f"{series_id} is not pilot-qualified")
        expected_start, expected_end = EXPECTED_QUERY_PERIODS[series_id]
        if query.get("startPeriod") != [expected_start] or query.get("endPeriod") != [expected_end]:
            raise FullPanelContractError(f"{series_id} query period differs from the frozen range")
        pilot_item = pilot_series.get(series_id)
        if pilot_item is None or (
            full_key != pilot_item.get("full_series_key")
            or api_path != pilot_item.get("api_path")
            or series.get("frequency") != pilot_item.get("expected_frequency")
            or series.get("unit") != pilot_item.get("expected_unit")
            or series.get("channel") != pilot_item.get("channel")
        ):
            raise FullPanelContractError(f"{series_id} metadata differs from the accepted pilot")
        _nonempty(series.get("availability_algorithm"), f"{series_id} availability_algorithm")
        _nonempty(series.get("revision_exposure"), f"{series_id} revision_exposure")
        _nonempty(series.get("transformation"), f"{series_id} transformation")
        parsed_series.append(series)
    if identifiers != EXPECTED_SERIES_IDS:
        raise FullPanelContractError("manifest series differ from the pilot-qualified set")

    pilot_panels = _resolve_pilot_panels(pilot)
    raw_panels = _list(manifest.get("panels"), "panels")
    if len(raw_panels) != 2:
        raise FullPanelContractError("manifest must contain exactly two frozen panels")
    panel_ids: set[str] = set()
    parsed_panels: list[dict[str, Any]] = []
    for raw in raw_panels:
        panel = _mapping(raw, "panel")
        panel_id = _nonempty(panel.get("panel_id"), "panel_id")
        members = [str(value) for value in _list(panel.get("series_ids"), f"{panel_id} series_ids")]
        if panel_id in panel_ids or len(members) != len(set(members)):
            raise FullPanelContractError("panel IDs and memberships must be unique")
        panel_ids.add(panel_id)
        if members != pilot_panels.get(panel_id):
            raise FullPanelContractError(f"{panel_id} differs from the accepted pilot panel")
        channels = {series["channel"] for series in parsed_series if series["series_id"] in members}
        minimum = _positive_int(
            panel.get("minimum_distinct_channels"), f"{panel_id} minimum_distinct_channels"
        )
        if len(channels) != minimum:
            raise FullPanelContractError(
                f"{panel_id} channel count differs from its frozen minimum"
            )
        parsed_panels.append(panel)
    if panel_ids != {"P0_CORE_REPLAY_AND_FAST", "P1_AUGMENTED_BANK_CREDIT"}:
        raise FullPanelContractError("panel IDs differ from the accepted pilot")

    language = _mapping(manifest.get("scientific_language"), "scientific_language")
    _exact_bool(
        language.get("high_dimensional_claim_allowed_before_execution"),
        False,
        "high_dimensional_claim_allowed_before_execution",
    )
    return manifest_id, parsed_series, parsed_panels


def audit_full_panel_contract(protocol_path: Path, manifest_path: Path) -> FullPanelContractAudit:
    """Validate the value-free Run 021 protocol and its exact source manifest."""

    root = _project_root(protocol_path)
    protocol_path = protocol_path.resolve()
    manifest_path = manifest_path.resolve()
    protocol = _mapping(yaml.safe_load(protocol_path.read_text(encoding="utf-8")), "protocol")
    manifest = _mapping(yaml.safe_load(manifest_path.read_text(encoding="utf-8")), "manifest")
    protocol_id, labels_matured, scenario_count = _validate_protocol(protocol)
    bound_count = _validate_bound_inputs(protocol, root)

    pilot_path = root / "research/data/run_020_series_pilot_manifest_v1_amendment_1.yaml"
    pilot = _mapping(yaml.safe_load(pilot_path.read_text(encoding="utf-8")), "pilot manifest")
    manifest_id, series, panels = _validate_manifest(manifest, pilot)

    registered_manifest = _inside(
        root,
        "research/data/run_021_full_panel_manifest_v1.yaml",
        "registered Run 021 manifest",
    )
    if manifest_path != registered_manifest:
        raise FullPanelContractError("audit must use the registered Run 021 manifest path")

    timing_counts: dict[str, int] = {}
    for item in series:
        timing = str(item["timing_class"])
        timing_counts[timing] = timing_counts.get(timing, 0) + 1
    return FullPanelContractAudit(
        audit_id="run-021-protocol-preflight-v1",
        protocol_id=protocol_id,
        manifest_id=manifest_id,
        protocol_path=protocol_path.relative_to(root).as_posix(),
        protocol_sha256=_sha256(protocol_path),
        manifest_path=manifest_path.relative_to(root).as_posix(),
        manifest_sha256=_sha256(manifest_path),
        bound_inputs_verified=bound_count,
        series_count=len(series),
        panel_count=len(panels),
        channel_count=len({str(item["channel"]) for item in series}),
        timing_class_counts=dict(sorted(timing_counts.items())),
        maximum_scenarios_before_deduplication=scenario_count,
        evaluation_labels_matured=labels_matured,
        full_history_retrieval_performed=False,
        state_estimation_performed=False,
        transmission_outcomes_accessed=False,
        synthetic_empirical_observations_used=False,
        passed=True,
    )


def write_full_panel_contract_audit(audit: FullPanelContractAudit, output: Path) -> None:
    """Write one immutable, atomically published preflight audit."""

    if output.exists():
        raise FullPanelContractError(f"refusing to overwrite existing audit: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(asdict(audit), indent=2, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        dir=output.parent, prefix=f".{output.name}.", suffix=".part", text=True
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
