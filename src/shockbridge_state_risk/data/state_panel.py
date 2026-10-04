"""Outcome-blind construction of a point-in-time ECB state panel."""

from __future__ import annotations

import calendar
import csv
import io
import math
import re
import zipfile
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Callable, Optional
from zoneinfo import ZoneInfo

import yaml

from shockbridge_state_risk.data.download import sha256_file
from shockbridge_state_risk.temporal import TimedObservation, assert_point_in_time

FRANKFURT = ZoneInfo("Europe/Berlin")
TIMING_BREAK = date(2022, 7, 21)


class StatePanelError(ValueError):
    """Raised when a state source cannot satisfy the frozen panel contract."""


@dataclass(frozen=True)
class EventCutoff:
    event_id: str
    event_date: date
    event_timestamp: datetime
    state_cutoff_timestamp: datetime


@dataclass(frozen=True)
class VintageValue:
    observation_period: date
    value: Optional[float]
    first_usable_timestamp: datetime
    vintage_id: str
    source_series_id: str
    source_url: str
    source_artifact_sha256: str


@dataclass(frozen=True)
class ArchiveSnapshot:
    first_usable_timestamp: datetime
    vintage_id: str
    source_series_id: str
    source_url: str
    source_artifact_sha256: str
    values: Mapping[date, float]


@dataclass(frozen=True)
class StateFeatureRow:
    event_id: str
    event_timestamp: str
    state_cutoff_timestamp: str
    feature_id: str
    feature_family: str
    observation_period: Optional[str]
    value: Optional[float]
    unit: str
    first_usable_timestamp: Optional[str]
    vintage_id: Optional[str]
    source_series_id: Optional[str]
    source_url: str
    source_artifact_sha256: str
    transformation_id: str
    age_at_cutoff_days: Optional[int]
    vintage_age_at_cutoff_days: Optional[float]
    missing: bool
    admission_status: str = "ADMITTED"


@dataclass(frozen=True)
class PanelAudit:
    events: int
    features: int
    rows: int
    missing_by_feature: Mapping[str, int]
    coverage_by_feature: Mapping[str, float]
    point_in_time_violations: int
    duplicate_event_feature_keys: int


@dataclass(frozen=True)
class SourceRecord:
    path: Path
    url: str
    sha256: str


REQUIRED_PANEL_SOURCES = {
    "event_dates",
    "rtd_archive",
    "rtd_hicp",
    "rtd_unemployment",
    "rtd_ip",
    "dfr",
    "yc_2y",
    "yc_10y",
}


def load_source_registry(path: Path) -> Mapping[str, SourceRecord]:
    """Load and verify every source used by the candidate panel."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("sources"), dict):
        raise StatePanelError("State source registry must contain a sources mapping.")
    records: dict[str, SourceRecord] = {}
    for key, value in payload["sources"].items():
        if not isinstance(key, str) or not isinstance(value, dict):
            raise StatePanelError("Malformed state source record.")
        try:
            record = SourceRecord(
                path=Path(str(value["path"])),
                url=str(value["url"]),
                sha256=str(value["sha256"]),
            )
        except KeyError as exc:
            raise StatePanelError(f"Source {key!r} is missing {exc.args[0]!r}.") from exc
        if not record.path.is_file():
            raise StatePanelError(f"Source file is missing: {record.path}")
        observed_hash = sha256_file(record.path)
        if observed_hash.lower() != record.sha256.lower():
            raise StatePanelError(
                f"Source hash mismatch for {key}: expected {record.sha256}, "
                f"observed {observed_hash}"
            )
        records[key] = record
    missing = sorted(REQUIRED_PANEL_SOURCES - records.keys())
    if missing:
        raise StatePanelError(f"State source registry is missing: {missing}")
    return records


def event_cutoff_for_date(event_date: date) -> EventCutoff:
    """Create the scheduled press-release cutoff in Frankfurt local time."""
    release_time = time(14, 15) if event_date >= TIMING_BREAK else time(13, 45)
    timestamp = datetime.combine(event_date, release_time, tzinfo=FRANKFURT)
    return EventCutoff(
        event_id=f"ecb-pr-{event_date.isoformat()}",
        event_date=event_date,
        event_timestamp=timestamp,
        state_cutoff_timestamp=timestamp,
    )


def load_factor_event_cutoffs(path: Path) -> tuple[EventCutoff, ...]:
    """Read only event dates from the factor artifact; never load outcome columns."""
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or "date" not in reader.fieldnames:
            raise StatePanelError("Factor event artifact must contain a date column.")
        events = [event_cutoff_for_date(date.fromisoformat(row["date"])) for row in reader]
    dates = [event.event_date for event in events]
    if dates != sorted(dates):
        raise StatePanelError("Factor event dates are not sorted.")
    if len(dates) != len(set(dates)):
        raise StatePanelError("Factor event dates are not unique.")
    return tuple(events)


def _parse_month(value: str) -> date:
    cleaned = value.strip()
    for pattern in ("%b-%y", "%b-%Y", "%Y-%m"):
        try:
            parsed = datetime.strptime(cleaned.title(), pattern)
            return date(parsed.year, parsed.month, 1)
        except ValueError:
            continue
    raise StatePanelError(f"Unsupported monthly period: {value!r}")


def _parse_number(value: str) -> Optional[float]:
    cleaned = value.strip().replace("\u00a0", "")
    if cleaned in {"", "-", "--", ":", "NA", "NaN", "nan"}:
        return None
    try:
        result = float(cleaned)
    except ValueError as exc:
        raise StatePanelError(f"Unsupported numeric value: {value!r}") from exc
    return result if math.isfinite(result) else None


def _archive_series_matchers() -> Mapping[str, Callable[[str], bool]]:
    return {
        "hicp_yoy": lambda key: key.startswith("ICP.M.") and ".N.000000.4.INX" in key,
        "unemployment_rate": lambda key: ".S.UNEH.RTT000.4.000" in key and ".JP." not in key,
        "industrial_production_yoy": lambda key: ".Y.PROD.NS0020.4.000" in key,
    }


def load_rtd_archive_snapshots(
    path: Path, source_url: str
) -> Mapping[str, tuple[ArchiveSnapshot, ...]]:
    """Load the ECB's 2001-2014 monthly RTD snapshots without extracting them."""
    artifact_hash = sha256_file(path)
    snapshots: dict[str, list[ArchiveSnapshot]] = {
        feature_id: [] for feature_id in _archive_series_matchers()
    }
    filename_pattern = re.compile(r"^monthly_(\d{4})(\d{2})\.csv$")
    with zipfile.ZipFile(path) as archive:
        for filename in sorted(archive.namelist()):
            match = filename_pattern.match(filename)
            if match is None:
                continue
            vintage_year, vintage_month = map(int, match.groups())
            next_year = vintage_year + (vintage_month == 12)
            next_month = 1 if vintage_month == 12 else vintage_month + 1
            usable_at = datetime(next_year, next_month, 1, tzinfo=FRANKFURT)
            with archive.open(filename) as binary_stream:
                text_stream = io.TextIOWrapper(
                    binary_stream, encoding="utf-8-sig", errors="replace", newline=""
                )
                rows = list(csv.reader(text_stream))
            if len(rows) < 10 or len(rows[1]) < 2:
                raise StatePanelError(f"Malformed RTD archive member: {filename}")
            keys = rows[1]
            for feature_id, matcher in _archive_series_matchers().items():
                positions = [offset for offset, key in enumerate(keys) if matcher(key)]
                if not positions:
                    continue
                if len(positions) != 1:
                    raise StatePanelError(
                        f"Ambiguous {feature_id} series in {filename}: {positions}"
                    )
                position = positions[0]
                values: dict[date, float] = {}
                for row in rows[4:]:
                    if not row or not row[0].strip() or position >= len(row):
                        continue
                    try:
                        period = _parse_month(row[0])
                    except StatePanelError:
                        continue
                    value = _parse_number(row[position])
                    if value is not None:
                        values[period] = value
                snapshots[feature_id].append(
                    ArchiveSnapshot(
                        first_usable_timestamp=usable_at,
                        vintage_id=f"archive-{vintage_year:04d}-{vintage_month:02d}",
                        source_series_id=keys[position],
                        source_url=source_url,
                        source_artifact_sha256=artifact_hash,
                        values=values,
                    )
                )
    return {key: tuple(value) for key, value in snapshots.items()}


def load_rtd_api_history(path: Path, source_url: str) -> tuple[VintageValue, ...]:
    """Load versioned ECB API rows, retaining every recorded vintage."""
    artifact_hash = sha256_file(path)
    values: list[VintageValue] = []
    seen: set[tuple[str, str]] = set()
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            action = row.get("ACTION", "Replace").lower()
            observed = _parse_number(row.get("OBS_VALUE", ""))
            valid_from = row.get("VALID_FROM", "")
            if not valid_from or (observed is None and action != "delete"):
                continue
            key = (row["TIME_PERIOD"], valid_from)
            if key in seen:
                raise StatePanelError(f"Duplicate RTD period-vintage key: {key}")
            seen.add(key)
            values.append(
                VintageValue(
                    observation_period=_parse_month(row["TIME_PERIOD"]),
                    value=observed,
                    first_usable_timestamp=datetime.fromisoformat(valid_from),
                    vintage_id=f"api-{valid_from}",
                    source_series_id=row["KEY"],
                    source_url=source_url,
                    source_artifact_sha256=artifact_hash,
                )
            )
    return tuple(values)


def _latest_archive_values(
    snapshots: Iterable[ArchiveSnapshot], cutoff: datetime
) -> dict[date, VintageValue]:
    eligible = [item for item in snapshots if item.first_usable_timestamp < cutoff]
    if not eligible:
        return {}
    snapshot = max(eligible, key=lambda item: item.first_usable_timestamp)
    return {
        period: VintageValue(
            observation_period=period,
            value=value,
            first_usable_timestamp=snapshot.first_usable_timestamp,
            vintage_id=snapshot.vintage_id,
            source_series_id=snapshot.source_series_id,
            source_url=snapshot.source_url,
            source_artifact_sha256=snapshot.source_artifact_sha256,
        )
        for period, value in snapshot.values.items()
    }


def as_of_macro_values(
    snapshots: Iterable[ArchiveSnapshot],
    api_history: Iterable[VintageValue],
    cutoff: datetime,
) -> Mapping[date, VintageValue]:
    """Reconstruct the latest value of every period strictly before cutoff."""
    selected = _latest_archive_values(snapshots, cutoff)
    for item in sorted(api_history, key=lambda value: value.first_usable_timestamp):
        if item.first_usable_timestamp >= cutoff:
            continue
        if item.value is None:
            selected.pop(item.observation_period, None)
        else:
            selected[item.observation_period] = item
    return selected


def _month_minus(period: date, months: int) -> date:
    ordinal = period.year * 12 + period.month - 1 - months
    return date(ordinal // 12, ordinal % 12 + 1, 1)


def _period_end(period: date) -> date:
    return date(period.year, period.month, calendar.monthrange(period.year, period.month)[1])


def _joined_metadata(items: Iterable[VintageValue], attribute: str) -> str:
    return ";".join(sorted({str(getattr(item, attribute)) for item in items}))


def macro_feature(
    feature_id: str,
    family: str,
    unit: str,
    transformation_id: str,
    event: EventCutoff,
    available: Mapping[date, VintageValue],
    year_over_year: bool,
    fallback_source_url: str,
    fallback_hash: str,
    maximum_age_days: int,
) -> StateFeatureRow:
    if not available:
        return _missing_row(
            event, feature_id, family, unit, transformation_id, fallback_source_url, fallback_hash
        )
    eligible_periods = list(available)
    if year_over_year:
        eligible_periods = [
            period
            for period in eligible_periods
            if _month_minus(period, 12) in available
            and available[_month_minus(period, 12)].value not in {None, 0.0}
        ]
    if not eligible_periods:
        return _missing_row(
            event, feature_id, family, unit, transformation_id, fallback_source_url, fallback_hash
        )
    latest_period = max(eligible_periods)
    latest = available[latest_period]
    if latest.value is None:
        raise StatePanelError("Selected macro value is a deletion action.")
    inputs = [latest]
    if year_over_year:
        lagged = available.get(_month_minus(latest_period, 12))
        if lagged is None or lagged.value in {None, 0.0}:
            raise StatePanelError("Eligible year-over-year period lost its lagged value.")
        inputs.append(lagged)
        assert lagged.value is not None
        value = 100.0 * (latest.value / lagged.value - 1.0)
    else:
        value = latest.value
    first_usable = max(item.first_usable_timestamp for item in inputs)
    assert_point_in_time(
        [
            TimedObservation(
                series_id=feature_id,
                observation_timestamp=datetime.combine(
                    _period_end(latest_period), time.min, tzinfo=FRANKFURT
                ),
                first_usable_timestamp=first_usable,
                decision_timestamp=event.state_cutoff_timestamp,
                vintage=_joined_metadata(inputs, "vintage_id"),
            )
        ]
    )
    age_days = (event.event_date - _period_end(latest_period)).days
    if age_days > maximum_age_days:
        return _missing_row(
            event, feature_id, family, unit, transformation_id, fallback_source_url, fallback_hash
        )
    vintage_age = (
        event.state_cutoff_timestamp - first_usable.astimezone(FRANKFURT)
    ).total_seconds() / 86400.0
    return StateFeatureRow(
        event_id=event.event_id,
        event_timestamp=event.event_timestamp.isoformat(),
        state_cutoff_timestamp=event.state_cutoff_timestamp.isoformat(),
        feature_id=feature_id,
        feature_family=family,
        observation_period=latest_period.strftime("%Y-%m"),
        value=value,
        unit=unit,
        first_usable_timestamp=first_usable.isoformat(),
        vintage_id=_joined_metadata(inputs, "vintage_id"),
        source_series_id=_joined_metadata(inputs, "source_series_id"),
        source_url=_joined_metadata(inputs, "source_url"),
        source_artifact_sha256=_joined_metadata(inputs, "source_artifact_sha256"),
        transformation_id=transformation_id,
        age_at_cutoff_days=age_days,
        vintage_age_at_cutoff_days=vintage_age,
        missing=False,
    )


def _missing_row(
    event: EventCutoff,
    feature_id: str,
    family: str,
    unit: str,
    transformation_id: str,
    source_url: str,
    source_hash: str,
) -> StateFeatureRow:
    return StateFeatureRow(
        event_id=event.event_id,
        event_timestamp=event.event_timestamp.isoformat(),
        state_cutoff_timestamp=event.state_cutoff_timestamp.isoformat(),
        feature_id=feature_id,
        feature_family=family,
        observation_period=None,
        value=None,
        unit=unit,
        first_usable_timestamp=None,
        vintage_id=None,
        source_series_id=None,
        source_url=source_url,
        source_artifact_sha256=source_hash,
        transformation_id=transformation_id,
        age_at_cutoff_days=None,
        vintage_age_at_cutoff_days=None,
        missing=True,
    )


def load_daily_series(path: Path) -> Mapping[date, float]:
    values: dict[date, float] = {}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            value = _parse_number(row.get("OBS_VALUE", ""))
            if value is not None:
                period = date.fromisoformat(row["TIME_PERIOD"])
                if period in values:
                    raise StatePanelError(f"Duplicate daily observation: {period}")
                values[period] = value
    return values


def _next_business_day(period: date) -> date:
    candidate = period + timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate


def daily_level_feature(
    event: EventCutoff,
    feature_id: str,
    family: str,
    unit: str,
    series_id: str,
    values: Mapping[date, float],
    source_url: str,
    source_hash: str,
    publication_rule: str,
) -> StateFeatureRow:
    candidates: list[tuple[date, datetime]] = []
    for period in values:
        if publication_rule == "effective_date_midnight":
            usable_at = datetime.combine(period, time.min, tzinfo=FRANKFURT)
        elif publication_rule == "next_business_day_noon":
            usable_at = datetime.combine(_next_business_day(period), time(12), tzinfo=FRANKFURT)
        else:
            raise StatePanelError(f"Unknown publication rule: {publication_rule}")
        if period < event.event_date and usable_at < event.state_cutoff_timestamp:
            candidates.append((period, usable_at))
    if not candidates:
        return _missing_row(
            event, feature_id, family, unit, publication_rule, source_url, source_hash
        )
    period, usable_at = max(candidates, key=lambda item: item[0])
    assert_point_in_time(
        [
            TimedObservation(
                series_id=series_id,
                observation_timestamp=datetime.combine(period, time.min, tzinfo=FRANKFURT),
                first_usable_timestamp=usable_at,
                decision_timestamp=event.state_cutoff_timestamp,
                vintage=f"observation-{period.isoformat()}",
            )
        ]
    )
    return StateFeatureRow(
        event_id=event.event_id,
        event_timestamp=event.event_timestamp.isoformat(),
        state_cutoff_timestamp=event.state_cutoff_timestamp.isoformat(),
        feature_id=feature_id,
        feature_family=family,
        observation_period=period.isoformat(),
        value=values[period],
        unit=unit,
        first_usable_timestamp=usable_at.isoformat(),
        vintage_id=f"observation-{period.isoformat()}",
        source_series_id=series_id,
        source_url=source_url,
        source_artifact_sha256=source_hash,
        transformation_id=publication_rule,
        age_at_cutoff_days=(event.event_date - period).days,
        vintage_age_at_cutoff_days=(event.state_cutoff_timestamp - usable_at).total_seconds()
        / 86400.0,
        missing=False,
    )


def curve_slope_feature(
    event: EventCutoff,
    two_year: Mapping[date, float],
    ten_year: Mapping[date, float],
    source_urls: tuple[str, str],
    source_hashes: tuple[str, str],
) -> StateFeatureRow:
    common = {
        period: ten_year[period] - two_year[period] for period in two_year.keys() & ten_year.keys()
    }
    row = daily_level_feature(
        event=event,
        feature_id="yield_curve_10y_minus_2y",
        family="policy_and_curve",
        unit="percentage_points",
        series_id="YC:SR_10Y-minus-SR_2Y",
        values=common,
        source_url=";".join(source_urls),
        source_hash=";".join(source_hashes),
        publication_rule="next_business_day_noon",
    )
    return StateFeatureRow(
        **{
            **asdict(row),
            "transformation_id": (
                "yc_10y_minus_2y__previous_base_day__published_next_business_day_noon"
            ),
            "admission_status": "CONDITIONAL_CHALLENGER",
        }
    )


def build_candidate_state_panel(
    sources: Mapping[str, SourceRecord],
) -> tuple[StateFeatureRow, ...]:
    """Build five prespecified features without loading any event outcome."""
    events = load_factor_event_cutoffs(sources["event_dates"].path)
    archive = load_rtd_archive_snapshots(sources["rtd_archive"].path, sources["rtd_archive"].url)
    raw_histories = {
        "hicp_yoy": load_rtd_api_history(sources["rtd_hicp"].path, sources["rtd_hicp"].url),
        "unemployment_rate": load_rtd_api_history(
            sources["rtd_unemployment"].path, sources["rtd_unemployment"].url
        ),
        "industrial_production_yoy": load_rtd_api_history(
            sources["rtd_ip"].path, sources["rtd_ip"].url
        ),
    }
    api_start = datetime(2015, 1, 1, tzinfo=FRANKFURT)
    histories = {
        feature_id: tuple(item for item in history if item.first_usable_timestamp >= api_start)
        for feature_id, history in raw_histories.items()
    }
    deposit_rate = load_daily_series(sources["dfr"].path)
    two_year = load_daily_series(sources["yc_2y"].path)
    ten_year = load_daily_series(sources["yc_10y"].path)
    rows: list[StateFeatureRow] = []
    macro_definitions = (
        (
            "hicp_yoy",
            "inflation",
            "percent",
            "rtd_hicp_index_yoy",
            True,
            "rtd_hicp",
            90,
        ),
        (
            "industrial_production_yoy",
            "activity",
            "percent",
            "rtd_ip_index_yoy",
            True,
            "rtd_ip",
            120,
        ),
        (
            "unemployment_rate",
            "activity",
            "percent",
            "rtd_unemployment_rate_level",
            False,
            "rtd_unemployment",
            120,
        ),
    )
    for event in events:
        for (
            feature_id,
            family,
            unit,
            transformation,
            yoy,
            source_key,
            maximum_age,
        ) in macro_definitions:
            available = as_of_macro_values(
                archive[feature_id], histories[feature_id], event.state_cutoff_timestamp
            )
            source = sources[source_key]
            rows.append(
                macro_feature(
                    feature_id=feature_id,
                    family=family,
                    unit=unit,
                    transformation_id=transformation,
                    event=event,
                    available=available,
                    year_over_year=yoy,
                    fallback_source_url=(f"{sources['rtd_archive'].url};{source.url}"),
                    fallback_hash=(f"{sources['rtd_archive'].sha256};{source.sha256}"),
                    maximum_age_days=maximum_age,
                )
            )
        rows.append(
            daily_level_feature(
                event=event,
                feature_id="deposit_facility_rate",
                family="policy_and_curve",
                unit="percent_per_annum",
                series_id="FM.D.U2.EUR.4F.KR.DFR.LEV",
                values=deposit_rate,
                source_url=sources["dfr"].url,
                source_hash=sources["dfr"].sha256,
                publication_rule="effective_date_midnight",
            )
        )
        rows.append(
            curve_slope_feature(
                event=event,
                two_year=two_year,
                ten_year=ten_year,
                source_urls=(sources["yc_2y"].url, sources["yc_10y"].url),
                source_hashes=(sources["yc_2y"].sha256, sources["yc_10y"].sha256),
            )
        )
    audit = audit_panel(rows)
    if audit.point_in_time_violations or audit.duplicate_event_feature_keys:
        raise StatePanelError(f"Candidate panel failed integrity audit: {audit}")
    return tuple(rows)


def audit_panel(rows: Iterable[StateFeatureRow]) -> PanelAudit:
    materialized = tuple(rows)
    keys = [(row.event_id, row.feature_id) for row in materialized]
    duplicates = len(keys) - len(set(keys))
    events = len({row.event_id for row in materialized})
    features = len({row.feature_id for row in materialized})
    missing = {
        feature_id: sum(row.missing for row in materialized if row.feature_id == feature_id)
        for feature_id in sorted({row.feature_id for row in materialized})
    }
    violations = sum(
        row.first_usable_timestamp is not None
        and datetime.fromisoformat(row.first_usable_timestamp)
        >= datetime.fromisoformat(row.state_cutoff_timestamp)
        for row in materialized
    )
    return PanelAudit(
        events=events,
        features=features,
        rows=len(materialized),
        missing_by_feature=missing,
        coverage_by_feature={
            key: (events - value) / events if events else 0.0 for key, value in missing.items()
        },
        point_in_time_violations=violations,
        duplicate_event_feature_keys=duplicates,
    )


def write_panel_csv(rows: Iterable[StateFeatureRow], path: Path) -> None:
    materialized = tuple(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    fieldnames = list(StateFeatureRow.__dataclass_fields__)
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(row) for row in materialized)
    temporary.replace(path)
