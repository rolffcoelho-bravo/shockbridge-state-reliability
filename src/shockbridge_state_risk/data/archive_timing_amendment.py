"""Run 024 legacy-archive identifier amendment and timing sensitivity."""

from __future__ import annotations

import calendar as month_calendar
import csv
import html
import io
import json
import math
import re
import shutil
import tempfile
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import yaml

from shockbridge_state_risk.data import full_panel_build as run023
from shockbridge_state_risk.data.download import sha256_file


@dataclass(frozen=True)
class ArchiveEntry:
    """One entry-local release date, title, and href from an ECB archive index."""

    release_date: date
    href: str
    title: str


@dataclass(frozen=True)
class ArchiveMappingAudit:
    """Fail-closed evidence for one archive's period-mapping rules."""

    release_kind: str
    archive_entries: int
    explicit_title_mappings: int
    identifier_candidates_rejected_by_temporal_validation: int
    eligible_identifier_entries: int
    eligible_generic_identifier_additions: int
    explicit_identifier_cross_validations: int
    explicit_identifier_disagreements: int
    merged_mapping_count: int
    in_sample_mapping_count: int


@dataclass(frozen=True)
class VariantAudit:
    """Integrity and coverage record for one availability-clock variant."""

    timing_variant: str
    panel_rows: dict[str, int]
    series_coverage: dict[str, dict[str, float | int | str]]
    fully_observed_origins: dict[str, int]
    missing_reasons: dict[str, int]
    duplicate_keys: int
    nonfinite_values: int
    point_in_time_violations: int


@dataclass(frozen=True)
class Run024Audit:
    """Outcome-blind audit for the approved archive and timing amendment."""

    audit_id: str
    protocol_sha256: str
    bound_inputs_verified: int
    preserved_response_count_verified: int
    parser_audits: dict[str, dict[str, int | str]]
    release_mapping_counts: dict[str, int]
    registered_clock: dict[str, Any]
    next_day_clock: dict[str, Any]
    registered_clock_vs_run023: dict[str, Any]
    next_day_vs_registered_clock: dict[str, Any]
    reliability_engine_imported: bool
    state_estimation_performed: bool
    scenario_evaluation_performed: bool
    transmission_outcomes_accessed: bool
    synthetic_empirical_observations_used: bool
    passed: bool


@dataclass
class _VariantResult:
    audit: VariantAudit
    rows: dict[str, list[run023.PanelRow]]


class _ArchiveIndexParser(HTMLParser):
    """Collect only an entry's ISO date and its own title anchor."""

    def __init__(self) -> None:
        super().__init__()
        self.entries: list[ArchiveEntry] = []
        self._release_date: date | None = None
        self._in_date = False
        self._date_text: list[str] = []
        self._in_title = False
        self._in_title_anchor = False
        self._title_href: str | None = None
        self._title_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "dt":
            if self._release_date is not None:
                raise run023.FullPanelBuildError("archive dated entry lacks its own title anchor")
            raw = attributes.get("isodate") or attributes.get("isoDate")
            if raw is None:
                raise run023.FullPanelBuildError("archive dt entry lacks an ISO release date")
            try:
                self._release_date = date.fromisoformat(raw)
            except ValueError as error:
                raise run023.FullPanelBuildError(
                    "archive dt entry has an invalid ISO date"
                ) from error
            self._in_date = True
            self._date_text = []
        elif tag == "div" and "title" in classes:
            if self._release_date is None:
                # ECB page chrome and feedback widgets also use class="title".
                # They are outside a pending dated archive entry and therefore
                # cannot contribute release evidence.
                return
            self._in_title = True
            self._title_href = None
            self._title_text = []
        elif tag == "a" and self._in_title:
            if self._in_title_anchor or self._title_href is not None:
                raise run023.FullPanelBuildError("archive title contains multiple anchors")
            href = attributes.get("href")
            if href is None:
                raise run023.FullPanelBuildError("archive title anchor lacks an href")
            self._in_title_anchor = True
            self._title_href = href

    def handle_data(self, data: str) -> None:
        value = " ".join(html.unescape(data).split())
        if not value:
            return
        if self._in_date:
            self._date_text.append(value)
        if self._in_title_anchor:
            self._title_text.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag == "dt" and self._in_date:
            assert self._release_date is not None
            visible = " ".join(self._date_text)
            try:
                visible_date = datetime.strptime(visible, "%d %B %Y").date()
            except ValueError as error:
                raise run023.FullPanelBuildError(
                    "archive visible release date is missing or invalid"
                ) from error
            if visible_date != self._release_date:
                raise run023.FullPanelBuildError(
                    "archive visible release date disagrees with ISO date"
                )
            self._in_date = False
        elif tag == "a" and self._in_title_anchor:
            self._in_title_anchor = False
        elif tag == "div" and self._in_title:
            if self._title_href is None or not self._title_text:
                raise run023.FullPanelBuildError("archive title entry is incomplete")
            assert self._release_date is not None
            self.entries.append(
                ArchiveEntry(
                    self._release_date,
                    self._title_href.partition("?")[0],
                    " ".join(self._title_text),
                )
            )
            self._in_title = False
            self._title_href = None
            self._title_text = []
            self._release_date = None


def _load_protocol(protocol_path: Path) -> tuple[Path, dict[str, Any]]:
    root = run023._project_root(protocol_path)
    protocol = run023._mapping(
        yaml.safe_load(protocol_path.read_text(encoding="utf-8")), "Run 024 protocol"
    )
    if protocol.get("status") != "FROZEN_BEFORE_RUN024_IMPLEMENTATION_OR_REBUILD":
        raise run023.FullPanelBuildError("Run 024 protocol is not prospectively frozen")
    boundary = run023._mapping(protocol.get("scientific_boundary"), "scientific_boundary")
    required = {
        "real_official_data_only": True,
        "new_network_retrieval_allowed": False,
        "preserved_response_bytes_only": True,
        "synthetic_empirical_observations_allowed": False,
        "reliability_engine_import_allowed": False,
        "empirical_state_estimation_allowed": False,
        "scenario_evaluation_allowed": False,
        "transmission_outcomes_access_allowed": False,
    }
    for key, expected in required.items():
        if boundary.get(key) is not expected:
            raise run023.FullPanelBuildError(f"Run 024 boundary changed: {key}")
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


def _decode_identifier_period(match: re.Match[str], release_date: date) -> str | None:
    month = int(match.group("mm"))
    two_digit_year = int(match.group("yy"))
    candidates = [
        year for year in (release_date.year, release_date.year - 1) if year % 100 == two_digit_year
    ]
    if len(candidates) != 1:
        return None
    year = candidates[0]
    month_end = date(year, month, month_calendar.monthrange(year, month)[1])
    if not month_end < release_date:
        return None
    return f"{year:04d}-{month:02d}"


def _explicit_reference_period(title: str, prefixes: Sequence[str]) -> str | None:
    for prefix in prefixes:
        if not title.startswith(prefix):
            continue
        suffix = title[len(prefix) :].strip()
        match = re.fullmatch(
            r"(?P<month>" + "|".join(run023.MONTH_NAMES) + r")\s+(?P<year>20\d{2})",
            suffix,
            flags=re.IGNORECASE,
        )
        if match is None:
            raise run023.FullPanelBuildError("recognized archive title has malformed period")
        month = run023.MONTH_NAMES[match.group("month").title()]
        return f"{int(match.group('year')):04d}-{month:02d}"
    return None


def parse_archive_identifier_dates(
    payload: bytes,
    release_kind: str,
    protocol: Mapping[str, Any],
) -> tuple[dict[str, date], dict[str, str], ArchiveMappingAudit]:
    """Parse entry-local explicit titles plus narrowly eligible legacy identifiers."""

    grammars = run023._mapping(protocol.get("identifier_grammars"), "identifier_grammars")
    if release_kind not in {"MIR", "BSI"}:
        raise run023.FullPanelBuildError("release kind must be MIR or BSI")
    grammar = run023._mapping(grammars.get(release_kind), f"{release_kind} grammar")
    try:
        decoded = payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise run023.FullPanelBuildError(f"{release_kind} archive is not UTF-8") from error
    parser = _ArchiveIndexParser()
    parser.feed(decoded)
    parser.close()
    if parser._release_date is not None:
        raise run023.FullPanelBuildError("archive dated entry lacks its own title anchor")
    identifier_pattern = re.compile(
        run023._nonempty(grammar.get("exact_path_regex"), "exact path regex")
    )
    generic_title = run023._nonempty(grammar.get("generic_title_exact"), "generic title")
    raw_prefixes = grammar.get("explicit_title_prefixes")
    if not isinstance(raw_prefixes, list) or not raw_prefixes:
        raise run023.FullPanelBuildError("explicit title prefixes must be nonempty")
    prefixes = [run023._nonempty(value, "explicit title prefix") for value in raw_prefixes]

    mappings: dict[str, date] = {}
    sources: dict[str, str] = {}
    explicit_count = 0
    temporal_rejections = 0
    eligible_count = 0
    additions = 0
    cross_validations = 0
    disagreements = 0
    for entry in parser.entries:
        identifier = identifier_pattern.fullmatch(entry.href)
        identifier_period = None
        if identifier is not None:
            identifier_period = _decode_identifier_period(identifier, entry.release_date)
            if identifier_period is None:
                temporal_rejections += 1
            else:
                eligible_count += 1
        explicit_period = _explicit_reference_period(entry.title, prefixes)
        if explicit_period is not None:
            explicit_count += 1
            if identifier_period is not None:
                cross_validations += 1
                if identifier_period != explicit_period:
                    disagreements += 1
                    raise run023.FullPanelBuildError(
                        f"{release_kind} explicit title disagrees with identifier"
                    )
            period = explicit_period
            source = "explicit_title"
        elif entry.title == generic_title and identifier_period is not None:
            period = identifier_period
            source = "legacy_pdf_identifier"
            additions += 1
        else:
            continue
        prior = mappings.get(period)
        if prior is not None and prior != entry.release_date:
            raise run023.FullPanelBuildError(
                f"conflicting {release_kind} release dates for {period}"
            )
        mappings[period] = entry.release_date
        prior_source = sources.get(period)
        if prior_source is None or source == "explicit_title":
            sources[period] = source

    minimums = run023._mapping(
        run023._mapping(protocol.get("release_mapping_contract"), "release_mapping_contract").get(
            "minimum_cross_validation_support"
        ),
        "minimum_cross_validation_support",
    )
    minimum = minimums.get(release_kind)
    if type(minimum) is not int or cross_validations < minimum:
        raise run023.FullPanelBuildError(
            f"{release_kind} identifier cross-validation support is insufficient"
        )
    run023_explicit = {
        period: usable.date()
        for period, usable in run023.parse_explicit_release_dates(payload, release_kind).items()
    }
    explicit_only = {
        period: release_date
        for period, release_date in mappings.items()
        if sources[period] == "explicit_title"
    }
    if explicit_only != run023_explicit:
        raise run023.FullPanelBuildError(
            f"{release_kind} entry-local explicit mappings differ from Run 023"
        )
    start = str(protocol["release_mapping_contract"]["sample_reference_period_start"])
    end = str(protocol["release_mapping_contract"]["sample_reference_period_end"])
    in_sample = sum(start <= period <= end for period in mappings)
    audit = ArchiveMappingAudit(
        release_kind=release_kind,
        archive_entries=len(parser.entries),
        explicit_title_mappings=len(explicit_only),
        identifier_candidates_rejected_by_temporal_validation=temporal_rejections,
        eligible_identifier_entries=eligible_count,
        eligible_generic_identifier_additions=additions,
        explicit_identifier_cross_validations=cross_validations,
        explicit_identifier_disagreements=disagreements,
        merged_mapping_count=len(mappings),
        in_sample_mapping_count=in_sample,
    )
    return mappings, sources, audit


def _usable_dates(release_dates: Mapping[str, date], timing_variant: str) -> dict[str, datetime]:
    if timing_variant not in {"registered_clock", "next_day_clock"}:
        raise run023.FullPanelBuildError("unknown Run 024 timing variant")
    result: dict[str, datetime] = {}
    for period, release_date in release_dates.items():
        if timing_variant == "registered_clock":
            usable_date = release_date
            usable_time = time(10, 0, 1)
        else:
            usable_date = release_date + timedelta(days=1)
            usable_time = time(0, 0, 0)
        result[period] = datetime.combine(usable_date, usable_time, tzinfo=run023.FRANKFURT)
    return result


def _verify_responses_and_load_versions(
    root: Path,
    protocol: Mapping[str, Any],
) -> tuple[dict[str, list[run023.VersionedValue]], dict[str, str], dict[str, Any]]:
    bound = protocol["bound_inputs"]
    run023_protocol_path = root / str(bound["run_023_protocol"]["path"])
    run023_protocol, manifest = run023.load_run023_contract(run023_protocol_path)
    retrieval_path = root / str(bound["retrieval_manifest"]["path"])
    retrieval = run023._mapping(
        yaml.safe_load(retrieval_path.read_text(encoding="utf-8")), "retrieval manifest"
    )
    records = {
        str(raw["item_id"]): run023._mapping(raw, "retrieval response")
        for raw in retrieval.get("responses", [])
    }
    if len(records) != 17:
        raise run023.FullPanelBuildError("Run 024 requires all 17 preserved responses")
    for item_id, record in records.items():
        relative = run023._nonempty(record.get("relative_path"), f"{item_id} response path")
        path = run023._inside(root, relative, f"{item_id} response")
        expected_bytes = record.get("response_bytes")
        if type(expected_bytes) is not int or path.stat().st_size != expected_bytes:
            raise run023.FullPanelBuildError(f"preserved response byte mismatch: {item_id}")
        if sha256_file(path) != record.get("sha256"):
            raise run023.FullPanelBuildError(f"preserved response hash mismatch: {item_id}")

    maximum = int(run023_protocol["retrieval_contract"]["maximum_response_bytes_per_series"])
    raw_directory = root / str(protocol["rebuild_contract"]["raw_directory"])
    versions: dict[str, list[run023.VersionedValue]] = {}
    source_hashes: dict[str, str] = {}
    for raw_spec in manifest["series"]:
        spec = run023._mapping(raw_spec, "series")
        series_id = str(spec["series_id"])
        path = raw_directory / "series" / str(spec["filename"])
        run023.validate_series_csv(spec, path, maximum)
        versions[series_id] = run023.load_versioned_values(spec, path)
        source_hashes[series_id] = str(records[series_id]["sha256"])
    return versions, source_hashes, manifest


def _build_variant(
    manifest: Mapping[str, Any],
    versions: Mapping[str, Sequence[run023.VersionedValue]],
    source_hashes: Mapping[str, str],
    release_dates: Mapping[str, Mapping[str, datetime]],
    timing_variant: str,
) -> _VariantResult:
    calendar = run023._mapping(manifest["calendar"], "calendar")
    origins = run023._origins(str(calendar["panel_start"]), str(calendar["panel_end"]))
    signs = {str(item["series_id"]): int(item["sign"]) for item in manifest["series"]}
    panel_rows: dict[str, list[run023.PanelRow]] = {}
    coverage: dict[str, dict[str, float | int | str]] = {}
    missing_reasons: Counter[str] = Counter()
    keys: list[tuple[str, str, str]] = []
    temporal_violations = 0
    nonfinite = 0
    fully_observed: dict[str, int] = {}
    for raw_panel in manifest["panels"]:
        panel = run023._mapping(raw_panel, "panel")
        panel_id = str(panel["panel_id"])
        members = [str(value) for value in panel["series_ids"]]
        rows: list[run023.PanelRow] = []
        observed_counts: Counter[str] = Counter()
        observed_by_origin: Counter[str] = Counter()
        first_origin: dict[str, str] = {}
        for origin_month, origin in origins:
            for series_id in members:
                signal = run023._signal_for(series_id, origin, versions, release_dates)
                keys.append((panel_id, origin_month, series_id))
                if signal is None:
                    if series_id.startswith(("MIR_", "BSI_")):
                        reason = "no_verified_release_mapped_observation"
                    elif series_id in {
                        "RTD_HICP",
                        "RTD_INDUSTRIAL_PRODUCTION",
                        "ECB_USD_EUR_REFERENCE_RATE",
                    }:
                        reason = "insufficient_transformation_lookback"
                    else:
                        reason = "no_strictly_prior_observation"
                    missing_reasons[reason] += 1
                    rows.append(
                        run023.PanelRow(
                            panel_id,
                            origin_month,
                            origin.isoformat(),
                            series_id,
                            "",
                            "",
                            "",
                            "1",
                            reason,
                            source_hashes[series_id],
                        )
                    )
                    continue
                value = signal.value * signs[series_id]
                if not signal.usable_at < origin:
                    temporal_violations += 1
                if not math.isfinite(value):
                    nonfinite += 1
                observed_counts[series_id] += 1
                observed_by_origin[origin_month] += 1
                first_origin.setdefault(series_id, origin_month)
                rows.append(
                    run023.PanelRow(
                        panel_id,
                        origin_month,
                        origin.isoformat(),
                        series_id,
                        signal.observation_period,
                        signal.usable_at.isoformat(),
                        run023._format_value(value),
                        "0",
                        "",
                        source_hashes[series_id],
                    )
                )
        panel_rows[panel_id] = rows
        fully_observed[panel_id] = sum(
            observed_by_origin[origin_month] == len(members) for origin_month, _ in origins
        )
        for series_id in members:
            observed = observed_counts[series_id]
            coverage[f"{panel_id}:{series_id}"] = {
                "observed_origins": observed,
                "total_origins": len(origins),
                "coverage_percent": round(100.0 * observed / len(origins), 6),
                "first_usable_origin": first_origin.get(series_id, ""),
            }
    duplicate_keys = len(keys) - len(set(keys))
    expected_rows = {
        str(panel["panel_id"]): len(origins) * len(panel["series_ids"])
        for panel in manifest["panels"]
    }
    observed_rows = {panel_id: len(rows) for panel_id, rows in panel_rows.items()}
    if (
        duplicate_keys != 0
        or temporal_violations != 0
        or nonfinite != 0
        or observed_rows != expected_rows
    ):
        raise run023.FullPanelBuildError(f"Run 024 {timing_variant} integrity gate failed")
    audit = VariantAudit(
        timing_variant=timing_variant,
        panel_rows=observed_rows,
        series_coverage=dict(sorted(coverage.items())),
        fully_observed_origins=fully_observed,
        missing_reasons=dict(sorted(missing_reasons.items())),
        duplicate_keys=duplicate_keys,
        nonfinite_values=nonfinite,
        point_in_time_violations=temporal_violations,
    )
    return _VariantResult(audit, panel_rows)


def _row_key(row: run023.PanelRow) -> tuple[str, str, str]:
    return row.panel_id, row.origin_month, row.series_id


def _load_panel_rows(path: Path) -> list[run023.PanelRow]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [run023.PanelRow(**row) for row in csv.DictReader(handle)]


def _fully_observed(rows: Sequence[run023.PanelRow]) -> int:
    counts: Counter[str] = Counter()
    sizes: Counter[str] = Counter()
    for row in rows:
        sizes[row.origin_month] += 1
        if row.is_missing == "0":
            counts[row.origin_month] += 1
    return sum(counts[month] == size for month, size in sizes.items())


def _compare_rows(
    left_rows: Mapping[str, Sequence[run023.PanelRow]],
    right_rows: Mapping[str, Sequence[run023.PanelRow]],
) -> dict[str, Any]:
    left = {_row_key(row): row for rows in left_rows.values() for row in rows}
    right = {_row_key(row): row for rows in right_rows.values() for row in rows}
    if set(left) != set(right):
        raise run023.FullPanelBuildError("panel comparison keys differ")
    changed = [key for key in left if left[key] != right[key]]
    missingness = [key for key in left if left[key].is_missing != right[key].is_missing]
    values = [
        key
        for key in left
        if left[key].transformed_value != right[key].transformed_value
        and left[key].is_missing == right[key].is_missing == "0"
    ]
    selection = [
        key
        for key in left
        if (
            left[key].observation_period,
            left[key].is_missing,
            left[key].transformed_value,
        )
        != (
            right[key].observation_period,
            right[key].is_missing,
            right[key].transformed_value,
        )
    ]
    return {
        "changed_panel_key_count": len(changed),
        "selection_change_count": len(selection),
        "missingness_status_change_count": len(missingness),
        "transformed_value_change_count": len(values),
        "exact_changed_origin_months": sorted({key[1] for key in selection}),
    }


def _coverage_delta(
    baseline: Mapping[str, Sequence[run023.PanelRow]],
    amended: Mapping[str, Sequence[run023.PanelRow]],
) -> dict[str, int]:
    result: dict[str, int] = {}
    for panel_id in sorted(amended):
        baseline_counts = Counter(
            row.series_id for row in baseline[panel_id] if row.is_missing == "0"
        )
        amended_counts = Counter(
            row.series_id for row in amended[panel_id] if row.is_missing == "0"
        )
        for series_id in sorted(set(baseline_counts) | set(amended_counts)):
            result[f"{panel_id}:{series_id}"] = (
                amended_counts[series_id] - baseline_counts[series_id]
            )
    return result


def _calendar_text(
    release_dates: Mapping[str, Mapping[str, date]],
    sources: Mapping[str, Mapping[str, str]],
    timing_variant: str,
) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        ["release_kind", "reference_period", "release_date", "usable_timestamp", "mapping_source"]
    )
    for release_kind in ("MIR", "BSI"):
        usable = _usable_dates(release_dates[release_kind], timing_variant)
        for period, release_date in sorted(release_dates[release_kind].items()):
            writer.writerow(
                [
                    release_kind,
                    period,
                    release_date.isoformat(),
                    usable[period].isoformat(),
                    sources[release_kind][period],
                ]
            )
    return buffer.getvalue()


def build_run024_archive_timing_amendment(
    protocol_path: Path,
    output_directory: Path,
    audit_output: Path,
) -> Run024Audit:
    """Rebuild both panels under the approved identifier and timing rules."""

    if output_directory.exists():
        raise run023.FullPanelBuildError(
            f"refusing to overwrite Run 024 bundle: {output_directory}"
        )
    if audit_output.exists():
        raise run023.FullPanelBuildError(f"refusing to overwrite Run 024 audit: {audit_output}")
    root, protocol = _load_protocol(protocol_path)
    versions, source_hashes, manifest = _verify_responses_and_load_versions(root, protocol)
    bound = protocol["bound_inputs"]
    payloads = {
        "MIR": (root / str(bound["mir_archive"]["path"])).read_bytes(),
        "BSI": (root / str(bound["bsi_archive"]["path"])).read_bytes(),
    }
    release_dates: dict[str, dict[str, date]] = {}
    sources: dict[str, dict[str, str]] = {}
    parser_audits: dict[str, ArchiveMappingAudit] = {}
    for release_kind in ("MIR", "BSI"):
        dates, mapping_sources, parser_audit = parse_archive_identifier_dates(
            payloads[release_kind], release_kind, protocol
        )
        release_dates[release_kind] = dates
        sources[release_kind] = mapping_sources
        parser_audits[release_kind] = parser_audit

    registered_dates = {
        release_kind: _usable_dates(dates, "registered_clock")
        for release_kind, dates in release_dates.items()
    }
    next_day_dates = {
        release_kind: _usable_dates(dates, "next_day_clock")
        for release_kind, dates in release_dates.items()
    }
    registered = _build_variant(
        manifest, versions, source_hashes, registered_dates, "registered_clock"
    )
    next_day = _build_variant(manifest, versions, source_hashes, next_day_dates, "next_day_clock")

    baseline_paths = {
        "P0_CORE_REPLAY_AND_FAST": root / str(bound["run_023_p0"]["path"]),
        "P1_AUGMENTED_BANK_CREDIT": root / str(bound["run_023_p1"]["path"]),
    }
    baseline = {panel_id: _load_panel_rows(path) for panel_id, path in baseline_paths.items()}
    registered_comparison = _compare_rows(baseline, registered.rows)
    registered_comparison["observed_origin_delta_by_series"] = _coverage_delta(
        baseline, registered.rows
    )
    registered_comparison["fully_observed_origin_delta_by_panel"] = {
        panel_id: registered.audit.fully_observed_origins[panel_id]
        - _fully_observed(baseline[panel_id])
        for panel_id in sorted(baseline)
    }
    registered_comparison["release_mapping_count_delta_by_kind"] = {
        release_kind: parser_audits[release_kind].merged_mapping_count
        - parser_audits[release_kind].explicit_title_mappings
        for release_kind in ("MIR", "BSI")
    }

    timing_comparison = _compare_rows(registered.rows, next_day.rows)
    timing_comparison["changed_release_timestamp_count"] = sum(
        len(dates) for dates in release_dates.values()
    )
    origin_dates = {
        origin.date()
        for _, origin in run023._origins(
            str(manifest["calendar"]["panel_start"]), str(manifest["calendar"]["panel_end"])
        )
    }
    coincident = sorted(
        {
            release_date.isoformat()
            for dates in release_dates.values()
            for release_date in dates.values()
            if release_date in origin_dates
        }
    )
    timing_comparison["release_dates_coinciding_with_origin_date"] = coincident
    timing_comparison["fully_observed_origin_delta_by_panel"] = {
        panel_id: next_day.audit.fully_observed_origins[panel_id]
        - registered.audit.fully_observed_origins[panel_id]
        for panel_id in sorted(registered.rows)
    }

    staging = Path(
        tempfile.mkdtemp(prefix=f".{output_directory.name}.", dir=output_directory.parent)
    )
    try:
        filenames = {
            "P0_CORE_REPLAY_AND_FAST": "p0_core_replay_and_fast.csv",
            "P1_AUGMENTED_BANK_CREDIT": "p1_augmented_bank_credit.csv",
        }
        for timing_variant, result in (
            ("registered_clock", registered),
            ("next_day_clock", next_day),
        ):
            for panel_id, rows in result.rows.items():
                run023._write_panel(staging / timing_variant / filenames[panel_id], rows)
            run023._atomic_text(
                staging / timing_variant / "release_calendar.csv",
                _calendar_text(release_dates, sources, timing_variant),
            )
        output_directory.parent.mkdir(parents=True, exist_ok=True)
        staging.replace(output_directory)
        staging = Path()
    finally:
        if staging != Path() and staging.exists():
            shutil.rmtree(staging)

    audit = Run024Audit(
        audit_id="run-024-archive-identifier-and-timing-sensitivity-v1",
        protocol_sha256=sha256_file(protocol_path),
        bound_inputs_verified=len(protocol["bound_inputs"]),
        preserved_response_count_verified=17,
        parser_audits={key: asdict(value) for key, value in parser_audits.items()},
        release_mapping_counts={key: len(value) for key, value in release_dates.items()},
        registered_clock=asdict(registered.audit),
        next_day_clock=asdict(next_day.audit),
        registered_clock_vs_run023=registered_comparison,
        next_day_vs_registered_clock=timing_comparison,
        reliability_engine_imported=False,
        state_estimation_performed=False,
        scenario_evaluation_performed=False,
        transmission_outcomes_accessed=False,
        synthetic_empirical_observations_used=False,
        passed=True,
    )
    run023._atomic_text(audit_output, json.dumps(asdict(audit), indent=2, sort_keys=True) + "\n")
    return audit
