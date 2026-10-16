"""Run 025 official deposit-facility-rate effective-date audit and amendment."""

from __future__ import annotations

import csv
import json
import math
import os
import re
import shutil
import tempfile
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import yaml

from shockbridge_state_risk.data import full_panel_build as run023
from shockbridge_state_risk.data.download import sha256_file

PROTOCOL_STATUS = (
    "APPROVED_AND_FROZEN_AFTER_LOCATOR_INSPECTION_BEFORE_CANONICAL_RETRIEVAL_OR_REBUILD"
)
DFR_SERIES_ID = "ECB_DEPOSIT_FACILITY_RATE"
DFR_SERIES_KEY = "FM.D.U2.EUR.4F.KR.DFR.LEV"
PANEL_FIELDS = (
    "panel_id",
    "origin_month",
    "origin_timestamp",
    "series_id",
    "observation_period",
    "usable_timestamp",
    "transformed_value",
    "is_missing",
    "missing_reason",
    "source_response_sha256",
)
MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}
DATE_CELL = re.compile(r"^(?P<day>[1-9]|[12][0-9]|3[01]) (?P<month>[A-Z][a-z]{2})\.?$")


@dataclass(frozen=True)
class EffectiveRateEvent:
    """One official deposit-facility rate and its effective date."""

    effective_date: date
    rate: Decimal


@dataclass(frozen=True)
class Run025Audit:
    """Outcome-blind audit of the official DFR effective-date amendment."""

    audit_id: str
    protocol_sha256: str
    source_manifest_sha256: str
    bound_inputs_verified: int
    source_response: dict[str, Any]
    parser: dict[str, Any]
    cross_validation: dict[str, Any]
    panel_scenarios: dict[str, Any]
    scenario_comparisons: dict[str, Any]
    integrity: dict[str, Any]
    reliability_engine_imported: bool
    state_estimation_performed: bool
    scenario_evaluation_performed: bool
    transmission_outcomes_accessed: bool
    synthetic_empirical_observations_used: bool
    passed: bool


class _TableParser(HTMLParser):
    """Collect table cell text while excluding footnote markers."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self.all_text: list[str] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._sup_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag == "table":
            if self._table is not None:
                raise run023.FullPanelBuildError("nested official-rate tables are not allowed")
            self._table = []
        elif tag == "tr" and self._table is not None:
            if self._row is not None:
                raise run023.FullPanelBuildError("nested official-rate rows are not allowed")
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            if self._cell is not None:
                raise run023.FullPanelBuildError("nested official-rate cells are not allowed")
            self._cell = []
        elif tag == "sup":
            self._sup_depth += 1

    def handle_data(self, data: str) -> None:
        value = " ".join(data.replace("\xa0", " ").split())
        if not value or self._sup_depth:
            return
        self.all_text.append(value)
        if self._cell is not None:
            self._cell.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag == "sup":
            if self._sup_depth <= 0:
                raise run023.FullPanelBuildError("unbalanced official-rate footnote marker")
            self._sup_depth -= 1
        elif tag in {"td", "th"} and self._cell is not None:
            assert self._row is not None
            self._row.append(" ".join(self._cell))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            assert self._table is not None
            self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._row is not None or self._cell is not None:
                raise run023.FullPanelBuildError("incomplete official-rate table")
            self.tables.append(self._table)
            self._table = None

    def close(self) -> None:
        super().close()
        if self._table is not None or self._row is not None or self._cell is not None:
            raise run023.FullPanelBuildError("unterminated official-rate table")
        if self._sup_depth:
            raise run023.FullPanelBuildError("unterminated official-rate footnote marker")


def _load_protocol(protocol_path: Path) -> tuple[Path, dict[str, Any]]:
    root = run023._project_root(protocol_path)
    protocol = run023._mapping(
        yaml.safe_load(protocol_path.read_text(encoding="utf-8")), "Run 025 protocol"
    )
    if protocol.get("status") != PROTOCOL_STATUS:
        raise run023.FullPanelBuildError("Run 025 protocol is not prospectively frozen")
    boundary = run023._mapping(protocol.get("scientific_boundary"), "scientific_boundary")
    expected = {
        "real_official_data_only": True,
        "zero_cost_sources_only": True,
        "new_network_retrieval_allowed": True,
        "synthetic_empirical_observations_allowed": False,
        "reliability_engine_import_allowed": False,
        "empirical_state_estimation_allowed": False,
        "scenario_evaluation_allowed": False,
        "transmission_outcomes_access_allowed": False,
    }
    for key, value in expected.items():
        if boundary.get(key) is not value:
            raise run023.FullPanelBuildError(f"Run 025 boundary changed: {key}")
    bound = run023._mapping(protocol.get("bound_inputs"), "bound_inputs")
    for label, raw in bound.items():
        spec = run023._mapping(raw, f"bound input {label}")
        relative = run023._nonempty(spec.get("path"), f"{label} path")
        path = run023._inside(root, relative, f"bound input {label}")
        expected_bytes = spec.get("bytes")
        if type(expected_bytes) is not int or expected_bytes <= 0:
            raise run023.FullPanelBuildError(f"invalid bound byte count: {label}")
        if not path.is_file() or path.stat().st_size != expected_bytes:
            raise run023.FullPanelBuildError(f"bound input byte mismatch: {label}")
        if sha256_file(path) != run023._nonempty(spec.get("sha256"), f"{label} hash"):
            raise run023.FullPanelBuildError(f"bound input hash mismatch: {label}")
    return root, protocol


def _parse_decimal(raw: str, label: str) -> Decimal:
    normalized = raw.strip().replace("\N{MINUS SIGN}", "-").replace("\N{EN DASH}", "-")
    if not normalized or normalized == "-":
        raise run023.FullPanelBuildError(f"{label} is missing")
    try:
        value = Decimal(normalized)
    except InvalidOperation as error:
        raise run023.FullPanelBuildError(f"{label} is not a decimal") from error
    if not value.is_finite():
        raise run023.FullPanelBuildError(f"{label} is nonfinite")
    return value


def _protocol_date(value: object, label: str) -> date:
    if isinstance(value, datetime):
        raise run023.FullPanelBuildError(f"{label} must be a date without time")
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise run023.FullPanelBuildError(f"{label} is not an ISO date") from error
    raise run023.FullPanelBuildError(f"{label} must be an ISO date")


def parse_effective_rate_table(
    payload: bytes, protocol: Mapping[str, Any]
) -> list[EffectiveRateEvent]:
    """Parse the one official table admitted by the frozen source contract."""

    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise run023.FullPanelBuildError("official rate page is not UTF-8") from error
    parser = _TableParser()
    parser.feed(text)
    parser.close()
    contract = run023._mapping(protocol.get("canonical_source_contract"), "source contract")
    semantics = run023._mapping(contract.get("required_visible_semantics"), "visible semantics")
    visible = " ".join(parser.all_text)
    for key in ("page_heading", "table_date_heading", "value_heading", "unit_text"):
        required = run023._nonempty(semantics.get(key), key)
        if required not in visible:
            raise run023.FullPanelBuildError(f"official page lacks required semantics: {key}")
    date_heading = str(semantics["table_date_heading"])
    value_heading = str(semantics["value_heading"])
    candidates = [
        table
        for table in parser.tables
        if date_heading in " ".join(cell for row in table for cell in row)
        and value_heading in " ".join(cell for row in table for cell in row)
    ]
    if len(candidates) != 1:
        raise run023.FullPanelBuildError("expected exactly one official effective-rate table")

    parser_contract = run023._mapping(protocol.get("parser_contract"), "parser_contract")
    window = run023._mapping(parser_contract.get("target_event_window"), "target window")
    start = _protocol_date(window.get("first_required_baseline_date"), "start")
    end = _protocol_date(window.get("last_admissible_effective_date"), "end")
    current_year: int | None = None
    events: dict[date, Decimal] = {}
    for row in candidates[0]:
        if len(row) < 3:
            continue
        year_cell, date_cell, value_cell = (value.strip() for value in row[:3])
        if re.fullmatch(r"[0-9]{4}", year_cell):
            current_year = int(year_cell)
        elif year_cell:
            continue
        match = DATE_CELL.fullmatch(date_cell)
        if match is None:
            continue
        if current_year is None:
            raise run023.FullPanelBuildError("official date row precedes a valid year block")
        month = MONTHS.get(match.group("month"))
        if month is None:
            raise run023.FullPanelBuildError("official date row uses an unregistered month")
        try:
            effective = date(current_year, month, int(match.group("day")))
        except ValueError as error:
            raise run023.FullPanelBuildError("official table contains an invalid date") from error
        value = _parse_decimal(value_cell, f"deposit rate on {effective.isoformat()}")
        prior = events.get(effective)
        if prior is not None and prior != value:
            raise run023.FullPanelBuildError(f"official table conflicts on {effective.isoformat()}")
        events[effective] = value
    selected = [
        EffectiveRateEvent(day, value)
        for day, value in sorted(events.items())
        if start <= day <= end
    ]
    if not selected or selected[0].effective_date != start:
        raise run023.FullPanelBuildError("official table lacks the frozen baseline event")
    if any(
        left.effective_date >= right.effective_date for left, right in zip(selected, selected[1:])
    ):
        raise run023.FullPanelBuildError("official effective dates are not strictly increasing")
    minimum = run023._mapping(
        protocol.get("cross_validation_contract"), "cross_validation_contract"
    ).get("acceptance_requirements", {})
    minimum_events = int(
        run023._mapping(minimum, "acceptance requirements")["minimum_official_events_in_window"]
    )
    if len(selected) < minimum_events:
        raise run023.FullPanelBuildError("official table has too few in-window events")
    return selected


def _database_time(row: Mapping[str, str]) -> datetime:
    raw = row.get("VALID_FROM", "").strip() or row.get("VALID_TO", "").strip()
    if not raw:
        raise run023.FullPanelBuildError("retained DFR version lacks a database timestamp")
    return run023._parse_timestamp(raw, DFR_SERIES_ID)


def _active_api_values(path: Path) -> dict[date, Decimal]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if not rows:
        raise run023.FullPanelBuildError("retained DFR response is empty")
    versions: dict[str, tuple[datetime, Mapping[str, str]]] = {}
    for row in rows:
        if row.get("KEY", "").strip() != DFR_SERIES_KEY:
            raise run023.FullPanelBuildError("retained response contains an unexpected series")
        period = row.get("TIME_PERIOD", "").strip()
        try:
            date.fromisoformat(period)
        except ValueError as error:
            raise run023.FullPanelBuildError(
                "retained DFR response has an invalid period"
            ) from error
        timestamp = _database_time(row)
        prior = versions.get(period)
        if prior is None or timestamp > prior[0]:
            versions[period] = (timestamp, row)
        elif timestamp == prior[0] and dict(row) != dict(prior[1]):
            raise run023.FullPanelBuildError("retained DFR versions conflict at one timestamp")
    active: dict[date, Decimal] = {}
    for period, (_, version_row) in versions.items():
        if (version_row.get("ACTION", "").strip() or "Replace").lower() == "delete":
            continue
        if "date of changes (raw data)" not in version_row.get("TITLE", ""):
            raise run023.FullPanelBuildError("retained DFR title lacks frozen semantics")
        if version_row.get("UNIT", "").strip() != "PCPA":
            raise run023.FullPanelBuildError("retained DFR unit is not percent per annum")
        active[date.fromisoformat(period)] = _parse_decimal(
            version_row.get("OBS_VALUE", ""), f"retained DFR value on {period}"
        )
    return active


def cross_validate_effective_rates(
    events: Sequence[EffectiveRateEvent],
    api_values: Mapping[date, Decimal],
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare every retained official daily value with the effective-date step function."""

    contract = run023._mapping(
        protocol.get("cross_validation_contract"), "cross_validation_contract"
    )
    window = run023._mapping(contract.get("comparison_window"), "comparison_window")
    start = _protocol_date(window.get("start"), "comparison start")
    end = _protocol_date(window.get("end"), "comparison end")
    selected_days = sorted(day for day in api_values if start <= day <= end)
    conflicts: list[dict[str, str]] = []
    unmatched_days: list[str] = []
    matched_event_dates: set[date] = set()
    event_index = -1
    compared = 0
    agreements = 0
    for day in selected_days:
        while event_index + 1 < len(events) and events[event_index + 1].effective_date <= day:
            event_index += 1
        if event_index < 0:
            unmatched_days.append(day.isoformat())
            continue
        event = events[event_index]
        compared += 1
        matched_event_dates.add(event.effective_date)
        observed = api_values[day]
        if observed == event.rate:
            agreements += 1
        else:
            conflicts.append(
                {
                    "date": day.isoformat(),
                    "table_rate": str(event.rate),
                    "api_rate": str(observed),
                }
            )
    unmatched_events = [
        item.effective_date.isoformat()
        for item in events
        if item.effective_date not in matched_event_dates
    ]
    requirements = run023._mapping(contract.get("acceptance_requirements"), "requirements")
    agreement_percent = (
        Decimal(100) * Decimal(agreements) / Decimal(compared) if compared else Decimal(0)
    )
    passed = (
        len(events) >= int(requirements["minimum_official_events_in_window"])
        and compared >= int(requirements["minimum_compared_api_days"])
        and agreement_percent == Decimal(str(requirements["exact_value_agreement_percent"]))
        and len(conflicts) == int(requirements["conflicting_days"])
        and len(unmatched_days) == int(requirements["unmatched_api_days"])
        and len(unmatched_events) == int(requirements["unmatched_effective_events"])
    )
    return {
        "api_days_in_window": len(selected_days),
        "compared_api_days": compared,
        "exact_agreements": agreements,
        "exact_agreement_percent": float(agreement_percent),
        "conflicting_days": len(conflicts),
        "conflict_examples": conflicts[:10],
        "unmatched_api_days": len(unmatched_days),
        "unmatched_api_day_examples": unmatched_days[:10],
        "unmatched_effective_events": len(unmatched_events),
        "unmatched_effective_event_dates": unmatched_events,
        "passed": passed,
    }


def _read_panel(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != PANEL_FIELDS:
            raise run023.FullPanelBuildError(f"unexpected panel schema: {path}")
        return list(reader)


def _decimal_text(value: Decimal) -> str:
    normalized = format(value, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def _select_event(
    events: Sequence[EffectiveRateEvent], origin: datetime, *, next_day: bool
) -> tuple[EffectiveRateEvent, datetime] | None:
    selected: tuple[EffectiveRateEvent, datetime] | None = None
    for event in events:
        usable_day = event.effective_date + timedelta(days=1 if next_day else 0)
        usable = datetime.combine(usable_day, time(0, 0), tzinfo=run023.FRANKFURT)
        if usable < origin:
            selected = event, usable
        else:
            break
    return selected


def _write_panel(rows: Sequence[Mapping[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PANEL_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _complete_origins(rows: Sequence[Mapping[str, str]]) -> int:
    grouped: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["origin_month"]].append(row)
    return sum(all(item["is_missing"] == "0" for item in items) for items in grouped.values())


def _rebuild_panel(
    source_rows: Sequence[Mapping[str, str]],
    events: Sequence[EffectiveRateEvent],
    source_hash: str,
    *,
    next_day: bool,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    rebuilt: list[dict[str, str]] = []
    source_dfr: dict[str, Mapping[str, str]] = {}
    non_dfr_unchanged = 0
    point_in_time_violations = 0
    duplicate_keys = 0
    nonfinite_values = 0
    keys: set[tuple[str, str, str]] = set()
    for raw in source_rows:
        row = dict(raw)
        if row["series_id"] == DFR_SERIES_ID:
            source_dfr[row["origin_month"]] = raw
            origin = datetime.fromisoformat(row["origin_timestamp"])
            selected = _select_event(events, origin, next_day=next_day)
            if selected is None:
                row.update(
                    observation_period="",
                    usable_timestamp="",
                    transformed_value="",
                    is_missing="1",
                    missing_reason="no_strictly_prior_official_effective_rate",
                    source_response_sha256=source_hash,
                )
            else:
                event, usable = selected
                row.update(
                    observation_period=event.effective_date.isoformat(),
                    usable_timestamp=usable.isoformat(),
                    transformed_value=_decimal_text(event.rate),
                    is_missing="0",
                    missing_reason="",
                    source_response_sha256=source_hash,
                )
        else:
            non_dfr_unchanged += 1
            if row != dict(raw):
                raise run023.FullPanelBuildError("a non-DFR panel row changed")
        key = (row["panel_id"], row["origin_month"], row["series_id"])
        if key in keys:
            duplicate_keys += 1
        keys.add(key)
        if row["is_missing"] == "0":
            try:
                numeric = float(row["transformed_value"])
            except ValueError:
                nonfinite_values += 1
            else:
                if not math.isfinite(numeric):
                    nonfinite_values += 1
            if datetime.fromisoformat(row["usable_timestamp"]) >= datetime.fromisoformat(
                row["origin_timestamp"]
            ):
                point_in_time_violations += 1
        rebuilt.append(row)

    rebuilt_dfr = {row["origin_month"]: row for row in rebuilt if row["series_id"] == DFR_SERIES_ID}
    if set(source_dfr) != set(rebuilt_dfr):
        raise run023.FullPanelBuildError("DFR origin keys changed during rebuild")
    missingness_changes = 0
    transformed_value_changes = 0
    changed_origins: list[str] = []
    for origin_month in sorted(source_dfr):
        before = source_dfr[origin_month]
        after = rebuilt_dfr[origin_month]
        if before["is_missing"] != after["is_missing"]:
            missingness_changes += 1
        if (
            before["is_missing"] == "0"
            and after["is_missing"] == "0"
            and Decimal(before["transformed_value"]) != Decimal(after["transformed_value"])
        ):
            transformed_value_changes += 1
        if dict(before) != dict(after):
            changed_origins.append(origin_month)
    observed = sum(row["is_missing"] == "0" for row in rebuilt_dfr.values())
    first_usable = next(
        (origin for origin in sorted(rebuilt_dfr) if rebuilt_dfr[origin]["is_missing"] == "0"),
        None,
    )
    audit = {
        "rows": len(rebuilt),
        "DFR_origins": len(rebuilt_dfr),
        "observed_DFR_origins": observed,
        "first_usable_DFR_origin": first_usable,
        "fully_observed_origins": _complete_origins(rebuilt),
        "DFR_rows_changed_against_bound_Run_024": len(changed_origins),
        "missingness_status_changes": missingness_changes,
        "transformed_value_changes": transformed_value_changes,
        "exact_changed_origin_months": changed_origins,
        "non_DFR_rows_unchanged": non_dfr_unchanged,
        "duplicate_keys": duplicate_keys,
        "nonfinite_values": nonfinite_values,
        "point_in_time_violations": point_in_time_violations,
    }
    return rebuilt, audit


def _atomic_json(payload: Mapping[str, Any], destination: Path) -> None:
    if destination.exists():
        raise run023.FullPanelBuildError(f"refusing to overwrite immutable audit: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent, prefix=f".{destination.name}.", suffix=".part"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def build_run025_dfr_effective_date_amendment(
    protocol_path: Path,
    source_manifest_path: Path,
    output_directory: Path,
    audit_output: Path,
) -> Run025Audit:
    """Audit the official table and conditionally build four outcome-blind panels."""

    root, protocol = _load_protocol(protocol_path)
    if output_directory.exists():
        raise run023.FullPanelBuildError(
            f"refusing to overwrite immutable Run 025 output: {output_directory}"
        )
    manifest = run023._mapping(
        yaml.safe_load(source_manifest_path.read_text(encoding="utf-8")), "source manifest"
    )
    if manifest.get("manifest_id") != "run-025-dfr-effective-date-source-v1":
        raise run023.FullPanelBuildError("unexpected Run 025 source manifest")
    if manifest.get("protocol_sha256") != sha256_file(protocol_path):
        raise run023.FullPanelBuildError("Run 025 source manifest protocol hash mismatch")
    retrieval = run023._mapping(manifest.get("retrieval"), "retrieval")
    canonical = run023._mapping(protocol.get("canonical_source_contract"), "source contract")
    raw_path = run023._inside(
        root,
        run023._nonempty(retrieval.get("relative_path"), "retrieval path"),
        "Run 025 response",
    )
    if not raw_path.is_file():
        raise run023.FullPanelBuildError("Run 025 canonical response is missing")
    if raw_path.stat().st_size != retrieval.get("response_bytes"):
        raise run023.FullPanelBuildError("Run 025 response byte count mismatch")
    if sha256_file(raw_path) != retrieval.get("sha256"):
        raise run023.FullPanelBuildError("Run 025 response hash mismatch")
    if retrieval.get("content_type") not in canonical.get("accepted_content_types", []):
        raise run023.FullPanelBuildError("Run 025 response content type is not admitted")
    if retrieval.get("final_url") != canonical.get("url"):
        raise run023.FullPanelBuildError("Run 025 final URL changed")

    events = parse_effective_rate_table(raw_path.read_bytes(), protocol)
    retained = run023._inside(
        root,
        protocol["bound_inputs"]["retained_ecb_dfr_api_response"]["path"],
        "retained DFR response",
    )
    api_values = _active_api_values(retained)
    validation = cross_validate_effective_rates(events, api_values, protocol)
    if not validation["passed"]:
        raise run023.FullPanelBuildError("Run 025 exact official-source cross-validation failed")

    rebuild = run023._mapping(protocol.get("conditional_panel_rebuild"), "panel rebuild")
    scenario_grid = list(rebuild.get("scenario_grid", []))
    if scenario_grid != [
        "registered_mir_bsi__effective_day_dfr",
        "registered_mir_bsi__next_day_dfr",
        "next_day_mir_bsi__effective_day_dfr",
        "next_day_mir_bsi__next_day_dfr",
    ]:
        raise run023.FullPanelBuildError("Run 025 scenario grid changed")
    source_panels = run023._mapping(rebuild.get("source_panels"), "source panels")
    staging_parent = output_directory.parent
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".run025.", dir=staging_parent))
    scenario_audits: dict[str, Any] = {}
    scenario_rows: dict[str, dict[str, list[dict[str, str]]]] = {}
    try:
        for scenario in scenario_grid:
            source_clock, dfr_clock = scenario.split("__", 1)
            raw_paths = source_panels.get(source_clock + "_clock")
            if not isinstance(raw_paths, list) or len(raw_paths) != 2:
                raise run023.FullPanelBuildError(f"invalid source panel set: {source_clock}")
            next_day = dfr_clock == "next_day_dfr"
            if dfr_clock not in {"effective_day_dfr", "next_day_dfr"}:
                raise run023.FullPanelBuildError(f"invalid DFR clock: {dfr_clock}")
            scenario_audits[scenario] = {}
            scenario_rows[scenario] = {}
            for relative in raw_paths:
                source_path = run023._inside(root, str(relative), "Run 024 panel")
                source = _read_panel(source_path)
                panel_ids = {row["panel_id"] for row in source}
                if len(panel_ids) != 1:
                    raise run023.FullPanelBuildError("source file does not contain one panel")
                panel_id = next(iter(panel_ids))
                rows, panel_audit = _rebuild_panel(
                    source, events, str(retrieval["sha256"]), next_day=next_day
                )
                filename = (
                    "p0_core_replay_and_fast.csv"
                    if panel_id == "P0_CORE_REPLAY_AND_FAST"
                    else "p1_augmented_bank_credit.csv"
                    if panel_id == "P1_AUGMENTED_BANK_CREDIT"
                    else None
                )
                if filename is None:
                    raise run023.FullPanelBuildError(f"unexpected panel id: {panel_id}")
                _write_panel(rows, staging / scenario / filename)
                scenario_audits[scenario][panel_id] = panel_audit
                scenario_rows[scenario][panel_id] = rows

        with (staging / "dfr_effective_date_events.csv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.writer(handle)
            writer.writerow(("effective_date", "deposit_facility_rate_percent_per_annum"))
            for event in events:
                writer.writerow((event.effective_date.isoformat(), _decimal_text(event.rate)))
        processed_manifest = {
            "schema_version": 1,
            "manifest_id": "run-025-dfr-effective-date-processed-v1",
            "protocol_sha256": sha256_file(protocol_path),
            "source_manifest_sha256": sha256_file(source_manifest_path),
            "source_response_sha256": retrieval["sha256"],
            "retained_api_response_sha256": sha256_file(retained),
            "official_events": len(events),
            "scenario_grid": scenario_grid,
        }
        (staging / "source_manifest.yaml").write_text(
            yaml.safe_dump(processed_manifest, sort_keys=False), encoding="utf-8"
        )

        comparisons: dict[str, Any] = {}
        for source_clock in ("registered_mir_bsi", "next_day_mir_bsi"):
            effective_name = source_clock + "__effective_day_dfr"
            next_name = source_clock + "__next_day_dfr"
            comparisons[source_clock] = {}
            for panel_id in ("P0_CORE_REPLAY_AND_FAST", "P1_AUGMENTED_BANK_CREDIT"):
                left = {
                    row["origin_month"]: row
                    for row in scenario_rows[effective_name][panel_id]
                    if row["series_id"] == DFR_SERIES_ID
                }
                right = {
                    row["origin_month"]: row
                    for row in scenario_rows[next_name][panel_id]
                    if row["series_id"] == DFR_SERIES_ID
                }
                changed_values = [
                    origin
                    for origin in sorted(left)
                    if left[origin]["transformed_value"] != right[origin]["transformed_value"]
                    or left[origin]["is_missing"] != right[origin]["is_missing"]
                ]
                changed_timestamps = [
                    origin
                    for origin in sorted(left)
                    if left[origin]["usable_timestamp"] != right[origin]["usable_timestamp"]
                ]
                changed_observations = [
                    origin
                    for origin in sorted(left)
                    if left[origin]["observation_period"] != right[origin]["observation_period"]
                ]
                comparisons[source_clock][panel_id] = {
                    "effective_vs_next_day_timestamp_changes": len(changed_timestamps),
                    "effective_vs_next_day_observation_period_changes": len(changed_observations),
                    "effective_vs_next_day_value_or_missingness_changes": len(changed_values),
                    "changed_origin_months": changed_values,
                }

        integrity = {
            "scenario_count": len(scenario_grid),
            "panel_file_count": len(scenario_grid) * 2,
            "duplicate_keys": sum(
                panel["duplicate_keys"]
                for scenario in scenario_audits.values()
                for panel in scenario.values()
            ),
            "nonfinite_values": sum(
                panel["nonfinite_values"]
                for scenario in scenario_audits.values()
                for panel in scenario.values()
            ),
            "point_in_time_violations": sum(
                panel["point_in_time_violations"]
                for scenario in scenario_audits.values()
                for panel in scenario.values()
            ),
            "non_DFR_rows_changed": 0,
        }
        passed = (
            validation["passed"]
            and integrity["duplicate_keys"] == 0
            and integrity["nonfinite_values"] == 0
            and integrity["point_in_time_violations"] == 0
            and integrity["non_DFR_rows_changed"] == 0
        )
        audit = Run025Audit(
            audit_id="run-025-dfr-effective-date-source-audit-v1",
            protocol_sha256=sha256_file(protocol_path),
            source_manifest_sha256=sha256_file(source_manifest_path),
            bound_inputs_verified=len(protocol["bound_inputs"]),
            source_response={
                "url": retrieval["registered_source_url"],
                "final_url": retrieval["final_url"],
                "retrieved_at_utc": retrieval["retrieved_at_utc"],
                "bytes": retrieval["response_bytes"],
                "sha256": retrieval["sha256"],
                "content_type": retrieval["content_type"],
            },
            parser={
                "official_events": len(events),
                "first_effective_date": events[0].effective_date.isoformat(),
                "last_effective_date": events[-1].effective_date.isoformat(),
                "date_heading_verified": True,
                "deposit_facility_heading_verified": True,
                "unit_verified": True,
            },
            cross_validation=validation,
            panel_scenarios=scenario_audits,
            scenario_comparisons=comparisons,
            integrity=integrity,
            reliability_engine_imported=False,
            state_estimation_performed=False,
            scenario_evaluation_performed=False,
            transmission_outcomes_accessed=False,
            synthetic_empirical_observations_used=False,
            passed=passed,
        )
        if not passed:
            raise run023.FullPanelBuildError("Run 025 integrity contract failed")
        staging.replace(output_directory)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    _atomic_json(asdict(audit), audit_output)
    return audit
