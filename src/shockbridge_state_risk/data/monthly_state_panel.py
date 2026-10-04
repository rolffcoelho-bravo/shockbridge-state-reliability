"""Regular-calendar point-in-time state panel built without outcome access."""

from __future__ import annotations

import calendar
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path

import yaml

from shockbridge_state_risk.data.download import sha256_file
from shockbridge_state_risk.data.state_panel import (
    FRANKFURT,
    EventCutoff,
    SourceRecord,
    StateFeatureRow,
    as_of_macro_values,
    audit_panel,
    daily_level_feature,
    load_daily_series,
    load_rtd_api_history,
    load_rtd_archive_snapshots,
    macro_feature,
)

MONTHLY_FEATURES = (
    "hicp_yoy",
    "industrial_production_yoy",
    "unemployment_rate",
    "deposit_facility_rate",
)


@dataclass(frozen=True)
class MonthlyPanelConfig:
    source_registry: Path
    source_registry_sha256: str
    start: date
    end: date
    cutoff_rule: str


def load_monthly_panel_config(path: Path) -> MonthlyPanelConfig:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Monthly panel config must be a mapping.")
    required = {
        "source_registry",
        "source_registry_sha256",
        "start_month",
        "end_month",
        "features",
        "cutoff_rule",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"Monthly panel config is missing: {missing}")
    features = payload["features"]
    if not isinstance(features, list) or tuple(features) != MONTHLY_FEATURES:
        raise ValueError("Monthly panel features must equal the four admitted features.")
    cutoff_rule = str(payload["cutoff_rule"])
    if cutoff_rule not in {
        "month_end_23_59_59_europe_berlin",
        "month_start_23_59_59_europe_berlin",
    }:
        raise ValueError("Unknown monthly cutoff rule.")
    registry = Path(str(payload["source_registry"]))
    if not registry.is_file():
        raise ValueError(f"Monthly source registry is missing: {registry}")
    expected_hash = str(payload["source_registry_sha256"])
    observed_hash = sha256_file(registry)
    if observed_hash != expected_hash:
        raise ValueError(
            f"Monthly source registry hash mismatch: expected {expected_hash}, "
            f"observed {observed_hash}"
        )
    return MonthlyPanelConfig(
        source_registry=registry,
        source_registry_sha256=expected_hash,
        start=parse_month(str(payload["start_month"])),
        end=parse_month(str(payload["end_month"])),
        cutoff_rule=cutoff_rule,
    )


def parse_month(value: str) -> date:
    """Parse an inclusive YYYY-MM calendar boundary."""
    try:
        parsed = datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise ValueError(f"Invalid calendar month: {value!r}") from exc
    return date(parsed.year, parsed.month, 1)


def _next_month(period: date) -> date:
    return date(
        period.year + (period.month == 12), 1 if period.month == 12 else period.month + 1, 1
    )


def monthly_cutoffs(
    start: date,
    end: date,
    cutoff_rule: str = "month_end_23_59_59_europe_berlin",
) -> tuple[EventCutoff, ...]:
    """Return inclusive month-end cutoffs on a strictly regular calendar."""
    if start.day != 1 or end.day != 1:
        raise ValueError("Monthly boundaries must be first-of-month dates.")
    if start > end:
        raise ValueError("Monthly start must not follow monthly end.")
    cutoffs: list[EventCutoff] = []
    period = start
    while period <= end:
        if cutoff_rule == "month_end_23_59_59_europe_berlin":
            last_day = calendar.monthrange(period.year, period.month)[1]
            cutoff_date = date(period.year, period.month, last_day)
        elif cutoff_rule == "month_start_23_59_59_europe_berlin":
            cutoff_date = period
        else:
            raise ValueError(f"Unknown monthly cutoff rule: {cutoff_rule}")
        cutoff = datetime.combine(cutoff_date, time(23, 59, 59), tzinfo=FRANKFURT)
        cutoffs.append(
            EventCutoff(
                event_id=f"month-{period.year:04d}-{period.month:02d}",
                event_date=cutoff_date,
                event_timestamp=cutoff,
                state_cutoff_timestamp=cutoff,
            )
        )
        period = _next_month(period)
    return tuple(cutoffs)


def build_monthly_state_panel(
    sources: Mapping[str, SourceRecord],
    start: date,
    end: date,
    cutoff_rule: str = "month_end_23_59_59_europe_berlin",
) -> tuple[StateFeatureRow, ...]:
    """Build four admitted features at conservative month-end cutoffs."""
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
    macro_definitions: tuple[tuple[str, str, str, str, bool, str, int], ...] = (
        ("hicp_yoy", "inflation", "percent", "rtd_hicp_index_yoy", True, "rtd_hicp", 90),
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
    rows: list[StateFeatureRow] = []
    for cutoff in monthly_cutoffs(start, end, cutoff_rule):
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
                archive[feature_id], histories[feature_id], cutoff.state_cutoff_timestamp
            )
            source = sources[source_key]
            rows.append(
                macro_feature(
                    feature_id=feature_id,
                    family=family,
                    unit=unit,
                    transformation_id=transformation,
                    event=cutoff,
                    available=available,
                    year_over_year=yoy,
                    fallback_source_url=f"{sources['rtd_archive'].url};{source.url}",
                    fallback_hash=f"{sources['rtd_archive'].sha256};{source.sha256}",
                    maximum_age_days=maximum_age,
                )
            )
        rows.append(
            daily_level_feature(
                event=cutoff,
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
    audit = audit_panel(rows)
    if audit.point_in_time_violations or audit.duplicate_event_feature_keys:
        raise ValueError(f"Monthly panel failed integrity audit: {audit}")
    return tuple(rows)
