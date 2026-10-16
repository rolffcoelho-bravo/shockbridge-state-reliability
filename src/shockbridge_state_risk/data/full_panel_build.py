"""Run 023 official-history retrieval and outcome-blind point-in-time panel build."""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import math
import os
import re
import shutil
import socket
import ssl
import tempfile
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, time, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, BinaryIO, Callable
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import certifi
import yaml

from shockbridge_state_risk.data.download import sha256_file


class FullPanelBuildError(RuntimeError):
    """Raised when a Run 023 retrieval or panel build fails closed."""


FRANKFURT = ZoneInfo("Europe/Berlin")
UTC = timezone.utc
SERIES_HOST = "data-api.ecb.europa.eu"
OFFICIAL_HOSTS = {SERIES_HOST, "data.ecb.europa.eu", "www.ecb.europa.eu"}
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
MONTH_NAMES = {
    name: index
    for index, name in enumerate(
        (
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ),
        start=1,
    )
}
DATE_PATTERN = re.compile(
    r"\b(?P<day>[0-3]?\d)\s+(?P<month>" + "|".join(MONTH_NAMES) + r")\s+(?P<year>20\d{2})\b"
)
REFERENCE_PATTERN = re.compile(
    r"(?:Euro area bank interest rate statistics|MFI interest rate statistics|"
    r"Monetary developments in the euro area)\s*:\s*"
    r"(?P<month>" + "|".join(MONTH_NAMES) + r")\s+(?P<year>20\d{2})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RetrievalRecord:
    """Immutable provenance for one official response."""

    item_id: str
    item_type: str
    registered_source_url: str
    final_url: str
    retrieved_at_utc: str
    response_bytes: int
    sha256: str
    content_type: str
    relative_path: str
    attempt_count: int
    prior_attempt_error_classes: list[str]


@dataclass(frozen=True)
class VersionedValue:
    """One value version and the earliest timestamp at which it is usable."""

    period: str
    value: float | None
    usable_at: datetime
    action: str


@dataclass(frozen=True)
class SignalValue:
    """One transformed series signal at a monthly origin."""

    observation_period: str
    usable_at: datetime
    value: float


@dataclass(frozen=True)
class PanelRow:
    """Serialized point-in-time row for one panel-origin-series key."""

    panel_id: str
    origin_month: str
    origin_timestamp: str
    series_id: str
    observation_period: str
    usable_timestamp: str
    transformed_value: str
    is_missing: str
    missing_reason: str
    source_response_sha256: str


@dataclass(frozen=True)
class PanelBuildAudit:
    """Outcome-blind audit of the complete Run 023 build."""

    audit_id: str
    protocol_sha256: str
    source_registry_sha256: str
    retrieval_manifest_sha256: str
    raw_source_count: int
    release_evidence_count: int
    release_mapping_counts: dict[str, int]
    panel_months: int
    panel_rows: dict[str, int]
    series_coverage: dict[str, dict[str, float | int]]
    missing_reasons: dict[str, int]
    point_in_time_violations: int
    duplicate_keys: int
    nonfinite_values: int
    reliability_engine_imported: bool
    state_estimation_performed: bool
    transmission_outcomes_accessed: bool
    synthetic_empirical_observations_used: bool
    passed: bool


class _TextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tokens: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(html.unescape(data).split())
        if value:
            self.tokens.append(value)


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FullPanelBuildError(f"{label} must be a mapping")
    return value


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FullPanelBuildError(f"{label} must be a nonempty string")
    return value.strip()


def _project_root(path: Path) -> Path:
    for candidate in (path.resolve().parent, *path.resolve().parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise FullPanelBuildError("cannot locate the project root")


def _inside(root: Path, relative: str, label: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise FullPanelBuildError(f"{label} escapes the project root") from error
    return candidate


def load_run023_contract(protocol_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load the committed Run 023 protocol and verify every bound input."""

    root = _project_root(protocol_path)
    protocol = _mapping(yaml.safe_load(protocol_path.read_text(encoding="utf-8")), "protocol")
    if protocol.get("status") != "APPROVED_AND_FROZEN_BEFORE_NETWORK_RETRIEVAL":
        raise FullPanelBuildError("Run 023 protocol is not frozen before retrieval")
    boundary = _mapping(protocol.get("scientific_boundary"), "scientific_boundary")
    exact_boundaries = {
        "real_official_data_only": True,
        "zero_cost_sources_only": True,
        "synthetic_empirical_observations_allowed": False,
        "transmission_outcomes_access_allowed": False,
        "reliability_engine_import_allowed": False,
        "empirical_state_estimation_allowed": False,
        "scenario_generation_allowed": False,
    }
    for name, expected in exact_boundaries.items():
        if boundary.get(name) is not expected:
            raise FullPanelBuildError(f"Run 023 boundary changed: {name}")
    for raw in protocol.get("bound_inputs", []):
        item = _mapping(raw, "bound input")
        relative = _nonempty(item.get("path"), "bound input path")
        expected_hash = _nonempty(item.get("sha256"), f"{relative} hash")
        source = _inside(root, relative, f"bound input {relative}")
        if not source.is_file() or sha256_file(source) != expected_hash:
            raise FullPanelBuildError(f"bound input hash mismatch: {relative}")
    manifest_relative = _nonempty(
        _mapping(protocol.get("retrieval_contract"), "retrieval_contract").get("source_registry"),
        "source_registry",
    )
    manifest_path = _inside(root, manifest_relative, "source_registry")
    manifest = _mapping(yaml.safe_load(manifest_path.read_text(encoding="utf-8")), "manifest")
    if manifest.get("status") != "FROZEN_BEFORE_FULL_RETRIEVAL":
        raise FullPanelBuildError("source manifest is not frozen before retrieval")
    if len(manifest.get("series", [])) != 10 or len(manifest.get("panels", [])) != 2:
        raise FullPanelBuildError("source manifest no longer contains ten series and two panels")
    return protocol, manifest


def _official_url(url: str, *, expected_host: str | None = None) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in OFFICIAL_HOSTS:
        raise FullPanelBuildError("retrieval URL must use an approved official HTTPS host")
    if expected_host is not None and parsed.hostname != expected_host:
        raise FullPanelBuildError(f"retrieval URL must use {expected_host}")
    if not parsed.path or parsed.path == "/":
        raise FullPanelBuildError("retrieval URL must contain a non-root path")
    return parsed.hostname


def _stream_response(
    response: BinaryIO,
    destination: Path,
    maximum_bytes: int,
) -> tuple[int, str]:
    """Stream one response with a hard byte ceiling and durable atomic write."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent, prefix=f".{destination.name}.", suffix=".part"
    )
    temporary = Path(temporary_name)
    digest = hashlib.sha256()
    size = 0
    try:
        with os.fdopen(descriptor, "wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > maximum_bytes:
                    raise FullPanelBuildError("official response exceeds the frozen byte ceiling")
                digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return size, digest.hexdigest()


def secure_download(
    *,
    item_id: str,
    item_type: str,
    url: str,
    destination: Path,
    maximum_bytes: int,
    relative_path: str,
    timeout_seconds: float = 180.0,
    opener: Callable[..., Any] = urlopen,
) -> RetrievalRecord:
    """Retrieve one official artifact with exact-host redirects and create-only writes."""

    if destination.exists():
        raise FullPanelBuildError(f"refusing to overwrite existing response: {destination}")
    if type(maximum_bytes) is not int or maximum_bytes <= 0:
        raise FullPanelBuildError("maximum response bytes must be a positive integer")
    if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool):
        raise FullPanelBuildError("timeout seconds must be a positive finite number")
    if not math.isfinite(float(timeout_seconds)) or timeout_seconds <= 0:
        raise FullPanelBuildError("timeout seconds must be a positive finite number")
    registered_host = _official_url(url)
    request = Request(url, headers={"User-Agent": "shockbridge-state-risk/0.1"})
    context = ssl.create_default_context(cafile=certifi.where())
    try:
        response_context = opener(request, timeout=float(timeout_seconds), context=context)
        with response_context as response:
            final_url = str(response.geturl())
            final_host = _official_url(final_url)
            if final_host != registered_host:
                raise FullPanelBuildError(
                    f"official response redirected from {registered_host} to {final_host}"
                )
            content_type = str(response.headers.get("Content-Type", "")).split(";", 1)[0]
            size, digest = _stream_response(response, destination, maximum_bytes)
    except FullPanelBuildError:
        raise
    except (OSError, ValueError) as error:
        raise FullPanelBuildError(f"official retrieval failed for {item_id}: {error}") from error
    return RetrievalRecord(
        item_id=item_id,
        item_type=item_type,
        registered_source_url=url,
        final_url=final_url,
        retrieved_at_utc=datetime.now(UTC).isoformat(),
        response_bytes=size,
        sha256=digest,
        content_type=content_type,
        relative_path=relative_path,
        attempt_count=1,
        prior_attempt_error_classes=[],
    )


def _transport_error_class(error: FullPanelBuildError) -> str | None:
    """Return a stable provenance label for an eligible transport timeout."""
    pending: list[BaseException] = []
    if error.__cause__ is not None:
        pending.append(error.__cause__)
    visited: set[int] = set()
    while pending:
        cause = pending.pop()
        if id(cause) in visited:
            continue
        visited.add(id(cause))
        if isinstance(cause, (TimeoutError, socket.timeout)):
            return "timeout"
        nested_cause = cause.__cause__
        if nested_cause is not None:
            pending.append(nested_cause)
        reason = getattr(cause, "reason", None)
        if isinstance(reason, BaseException):
            pending.append(reason)
    return None


def _download_with_retry(
    *,
    maximum_attempts: int,
    **kwargs: Any,
) -> RetrievalRecord:
    if type(maximum_attempts) is not int or maximum_attempts <= 0:
        raise FullPanelBuildError("maximum attempts must be a positive integer")
    prior_errors: list[str] = []
    for attempt in range(1, maximum_attempts + 1):
        try:
            record = secure_download(**kwargs)
            return replace(
                record,
                attempt_count=attempt,
                prior_attempt_error_classes=prior_errors,
            )
        except FullPanelBuildError as error:
            error_class = _transport_error_class(error)
            if error_class is None or attempt == maximum_attempts:
                raise
            prior_errors.append(error_class)
    raise AssertionError("unreachable retrieval retry state")


def _parse_period_date(value: str) -> date:
    try:
        return date.fromisoformat(value if len(value) == 10 else f"{value}-01")
    except ValueError as error:
        raise FullPanelBuildError(f"unsupported observation period: {value}") from error


def _parse_timestamp(value: str, label: str) -> datetime:
    if not value:
        raise FullPanelBuildError(f"{label} requires a timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise FullPanelBuildError(f"invalid timestamp for {label}: {value}") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise FullPanelBuildError(f"timestamp for {label} must be timezone-aware")
    return parsed


def validate_series_csv(spec: Mapping[str, Any], path: Path, maximum_bytes: int) -> int:
    """Validate series identity and schema without computing a research signal."""

    if path.stat().st_size > maximum_bytes:
        raise FullPanelBuildError(f"{spec['series_id']} exceeds the response byte ceiling")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        required = {"KEY", "FREQ", "TIME_PERIOD", "OBS_VALUE", "UNIT"}
        if not required.issubset(fields):
            raise FullPanelBuildError(
                f"{spec['series_id']} lacks columns: {sorted(required - fields)}"
            )
        rows = list(reader)
    if not rows:
        raise FullPanelBuildError(f"{spec['series_id']} returned no rows")
    if {row["KEY"] for row in rows} != {str(spec["full_series_key"])}:
        raise FullPanelBuildError(f"{spec['series_id']} returned the wrong series key")
    if {row["FREQ"] for row in rows} != {str(spec["frequency"])}:
        raise FullPanelBuildError(f"{spec['series_id']} returned the wrong frequency")
    query = parse_qs(urlparse(str(spec["query_url"])).query)
    start_values = query.get("startPeriod", [])
    end_values = query.get("endPeriod", [])
    if len(start_values) != 1 or len(end_values) != 1:
        raise FullPanelBuildError(f"{spec['series_id']} lacks frozen query boundaries")
    sample_start = _parse_period_date(start_values[0])
    sample_end = _parse_period_date(end_values[0])
    seen: set[tuple[str, str, str]] = set()
    for row_number, row in enumerate(rows, start=2):
        period = row["TIME_PERIOD"].strip()
        period_date = _parse_period_date(period)
        if not sample_start <= period_date <= sample_end:
            raise FullPanelBuildError(
                f"{spec['series_id']} returned a row outside the frozen sample"
            )
        action = row.get("ACTION", "").strip() or "Replace"
        action_lower = action.lower()
        valid_from = row.get("VALID_FROM", "").strip()
        valid_to = row.get("VALID_TO", "").strip()
        effective_timestamp = valid_from or valid_to
        identity = (period, effective_timestamp, action_lower)
        if identity in seen:
            raise FullPanelBuildError(f"{spec['series_id']} has a duplicate version row")
        seen.add(identity)
        unit = row["UNIT"].strip()
        if action_lower == "delete":
            if unit not in {"", str(spec["unit"])}:
                raise FullPanelBuildError(f"{spec['series_id']} returned the wrong unit")
        elif unit != str(spec["unit"]):
            raise FullPanelBuildError(f"{spec['series_id']} returned the wrong unit")
        raw_value = row["OBS_VALUE"].strip()
        if raw_value:
            try:
                value = float(raw_value)
            except ValueError as error:
                raise FullPanelBuildError(
                    f"{spec['series_id']} has a nonnumeric value at row {row_number}"
                ) from error
            if not math.isfinite(value):
                raise FullPanelBuildError(f"{spec['series_id']} has a nonfinite value")
        if str(spec["timing_class"]) == "A_REPLAY_ELIGIBLE":
            if not {"ACTION", "VALID_FROM", "VALID_TO"}.issubset(fields):
                raise FullPanelBuildError(f"{spec['series_id']} lacks replay columns")
            _parse_timestamp(effective_timestamp, str(spec["series_id"]))
    return len(rows)


def _atomic_text(path: Path, text: str) -> None:
    if path.exists():
        raise FullPanelBuildError(f"refusing to overwrite output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".part", text=True
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write_retrieval_manifest(
    *,
    protocol_path: Path,
    source_manifest_path: Path,
    records: Sequence[RetrievalRecord],
    output: Path,
) -> None:
    payload = {
        "schema_version": 1,
        "manifest_id": "run-023-full-history-sources-v1",
        "created_on": date.today().isoformat(),
        "status": "RETRIEVED_OFFICIAL_BYTES_NOT_ESTIMATED",
        "protocol": {
            "path": protocol_path.as_posix(),
            "sha256": sha256_file(protocol_path),
        },
        "source_registry": {
            "path": source_manifest_path.as_posix(),
            "sha256": sha256_file(source_manifest_path),
        },
        "responses": [asdict(record) for record in records],
        "scientific_boundary": {
            "real_official_data_only": True,
            "synthetic_empirical_observations_used": False,
            "state_estimation_performed": False,
            "transmission_outcomes_accessed": False,
        },
    }
    _atomic_text(output, yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))


def retrieve_run023_inputs(
    protocol_path: Path,
    raw_directory: Path,
    retrieval_manifest_output: Path,
    *,
    opener: Callable[..., Any] = urlopen,
) -> list[RetrievalRecord]:
    """Retrieve the complete registered bundle and promote it only after validation."""

    protocol, manifest = load_run023_contract(protocol_path)
    if raw_directory.exists():
        raise FullPanelBuildError(f"refusing to overwrite raw bundle: {raw_directory}")
    if retrieval_manifest_output.exists():
        raise FullPanelBuildError(
            f"refusing to overwrite retrieval manifest: {retrieval_manifest_output}"
        )
    root = _project_root(protocol_path)
    maximum_series = int(
        _mapping(protocol["retrieval_contract"], "retrieval_contract")[
            "maximum_response_bytes_per_series"
        ]
    )
    maximum_evidence = int(
        _mapping(protocol["retrieval_contract"], "retrieval_contract")[
            "maximum_response_bytes_per_release_evidence_item"
        ]
    )
    maximum_attempts = int(
        _mapping(protocol["retrieval_contract"], "retrieval_contract")["maximum_attempts_per_item"]
    )
    staging = Path(tempfile.mkdtemp(prefix=f".{raw_directory.name}.", dir=raw_directory.parent))
    records: list[RetrievalRecord] = []
    try:
        for raw in manifest["series"]:
            spec = _mapping(raw, "series")
            filename = _nonempty(spec.get("filename"), "series filename")
            destination = staging / "series" / filename
            relative = f"data/raw/{raw_directory.name}/series/{filename}"
            record = _download_with_retry(
                maximum_attempts=maximum_attempts,
                item_id=str(spec["series_id"]),
                item_type="series_csv",
                url=str(spec["query_url"]),
                destination=destination,
                maximum_bytes=maximum_series,
                relative_path=relative,
                opener=opener,
            )
            validate_series_csv(spec, destination, maximum_series)
            records.append(record)

        evidence_urls = {
            key: value
            for key, value in _mapping(manifest["release_sources"], "release_sources").items()
            if key != "rule"
        }
        evidence_urls["bsi_historical_release_index_run_023_addition"] = _nonempty(
            _mapping(protocol["release_evidence_contract"], "release_evidence_contract").get(
                "bsi_historical_release_index_run_023_addition"
            ),
            "BSI historical release index",
        )
        for item_id, url in evidence_urls.items():
            filename = f"{item_id}.html"
            destination = staging / "release_evidence" / filename
            relative = f"data/raw/{raw_directory.name}/release_evidence/{filename}"
            records.append(
                _download_with_retry(
                    maximum_attempts=maximum_attempts,
                    item_id=item_id,
                    item_type="release_evidence_html",
                    url=str(url),
                    destination=destination,
                    maximum_bytes=maximum_evidence,
                    relative_path=relative,
                    opener=opener,
                )
            )
        raw_directory.parent.mkdir(parents=True, exist_ok=True)
        staging.replace(raw_directory)
        staging = Path()
    finally:
        if staging != Path() and staging.exists():
            shutil.rmtree(staging)
    source_manifest = root / "research/data/run_021_full_panel_manifest_v1.yaml"
    write_retrieval_manifest(
        protocol_path=protocol_path.resolve().relative_to(root),
        source_manifest_path=source_manifest.relative_to(root),
        records=records,
        output=retrieval_manifest_output,
    )
    return records


def parse_explicit_release_dates(payload: bytes, release_kind: str) -> dict[str, datetime]:
    """Parse only explicit reference-month/date pairs from an official release index."""

    if release_kind not in {"MIR", "BSI"}:
        raise FullPanelBuildError("release kind must be MIR or BSI")
    parser = _TextCollector()
    try:
        parser.feed(payload.decode("utf-8-sig"))
    except UnicodeDecodeError as error:
        raise FullPanelBuildError(f"{release_kind} release evidence is not UTF-8") from error
    mappings: dict[str, datetime] = {}
    for index, token in enumerate(parser.tokens):
        reference = REFERENCE_PATTERN.search(token)
        if reference is None:
            continue
        title = reference.group(0).lower()
        if release_kind == "MIR" and "interest rate" not in title:
            continue
        if release_kind == "BSI" and "monetary developments" not in title:
            continue
        release_match = None
        for previous in reversed(parser.tokens[max(0, index - 24) : index]):
            release_match = DATE_PATTERN.search(previous)
            if release_match is not None:
                break
        if release_match is None:
            continue
        reference_month = MONTH_NAMES[reference.group("month").title()]
        reference_period = f"{int(reference.group('year')):04d}-{reference_month:02d}"
        release_day = date(
            int(release_match.group("year")),
            MONTH_NAMES[release_match.group("month")],
            int(release_match.group("day")),
        )
        usable = datetime.combine(release_day, time(10, 0, 1), tzinfo=FRANKFURT)
        existing = mappings.get(reference_period)
        if existing is not None and existing != usable:
            raise FullPanelBuildError(
                f"conflicting {release_kind} release dates for {reference_period}"
            )
        mappings[reference_period] = usable
    return mappings


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_versioned_values(spec: Mapping[str, Any], path: Path) -> list[VersionedValue]:
    """Load validated rows and attach their frozen usable timestamps."""

    timing = str(spec["timing_class"])
    series_id = str(spec["series_id"])
    versions: list[VersionedValue] = []
    for row in _read_csv(path):
        action = row.get("ACTION", "").strip() or "Replace"
        raw_value = row["OBS_VALUE"].strip()
        value = float(raw_value) if raw_value else None
        if timing == "A_REPLAY_ELIGIBLE":
            usable = _parse_timestamp(
                row.get("VALID_FROM", "").strip() or row.get("VALID_TO", "").strip(),
                series_id,
            )
        elif series_id == "ECB_USD_EUR_REFERENCE_RATE":
            observation_day = _parse_period_date(row["TIME_PERIOD"])
            usable = datetime.combine(observation_day, time(17, 0), tzinfo=FRANKFURT)
        else:
            raw_valid_from = row.get("VALID_FROM", "").strip()
            usable = (
                _parse_timestamp(raw_valid_from, series_id)
                if raw_valid_from
                else datetime.min.replace(tzinfo=UTC)
            )
        versions.append(
            VersionedValue(
                period=row["TIME_PERIOD"].strip(),
                value=value,
                usable_at=usable,
                action=action,
            )
        )
    return versions


def _month_add(period: str, delta: int) -> str:
    parsed = _parse_period_date(period)
    index = parsed.year * 12 + parsed.month - 1 + delta
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def _origins(start: str, end: str) -> list[tuple[str, datetime]]:
    values: list[tuple[str, datetime]] = []
    current = start
    while current <= end:
        day = _parse_period_date(current)
        values.append((current, datetime.combine(day, time(23, 59, 59), tzinfo=FRANKFURT)))
        current = _month_add(current, 1)
    return values


def _snapshot(versions: Iterable[VersionedValue], origin: datetime) -> dict[str, VersionedValue]:
    selected: dict[str, VersionedValue] = {}
    for item in versions:
        if not item.usable_at < origin:
            continue
        prior = selected.get(item.period)
        if prior is None or item.usable_at > prior.usable_at:
            selected[item.period] = item
        elif item.usable_at == prior.usable_at and item != prior:
            raise FullPanelBuildError(f"ambiguous same-time versions for {item.period}")
    return {key: item for key, item in selected.items() if item.action.lower() != "delete"}


def _latest_level(versions: Sequence[VersionedValue], origin: datetime) -> SignalValue | None:
    snapshot = _snapshot(versions, origin)
    for period in sorted(snapshot, key=_parse_period_date, reverse=True):
        item = snapshot[period]
        if item.value is not None:
            return SignalValue(period, item.usable_at, item.value)
    return None


def _latest_yoy_log(versions: Sequence[VersionedValue], origin: datetime) -> SignalValue | None:
    snapshot = _snapshot(versions, origin)
    for period in sorted(snapshot, key=_parse_period_date, reverse=True):
        lag = _month_add(period, -12)
        current = snapshot[period]
        prior = snapshot.get(lag)
        if (
            current.value is not None
            and prior is not None
            and prior.value is not None
            and current.value > 0
            and prior.value > 0
        ):
            return SignalValue(
                period,
                max(current.usable_at, prior.usable_at),
                100.0 * math.log(current.value / prior.value),
            )
    return None


def _latest_spread(
    long_versions: Sequence[VersionedValue],
    short_versions: Sequence[VersionedValue],
    origin: datetime,
) -> SignalValue | None:
    long_snapshot = _snapshot(long_versions, origin)
    short_snapshot = _snapshot(short_versions, origin)
    common = sorted(set(long_snapshot) & set(short_snapshot), key=_parse_period_date, reverse=True)
    for period in common:
        long = long_snapshot[period]
        short = short_snapshot[period]
        if long.value is not None and short.value is not None:
            return SignalValue(
                period,
                max(long.usable_at, short.usable_at),
                long.value - short.value,
            )
    return None


def _end_month_log_change(
    versions: Sequence[VersionedValue], origin: datetime
) -> SignalValue | None:
    eligible = [item for item in versions if item.usable_at < origin and item.value is not None]
    by_month: dict[str, VersionedValue] = {}
    for item in eligible:
        month = item.period[:7]
        prior = by_month.get(month)
        if prior is None or _parse_period_date(item.period) > _parse_period_date(prior.period):
            by_month[month] = item
    latest_month = _month_add(origin.strftime("%Y-%m"), -1)
    prior_month = _month_add(latest_month, -1)
    current = by_month.get(latest_month)
    prior = by_month.get(prior_month)
    if (
        current is None
        or prior is None
        or current.value is None
        or prior.value is None
        or current.value <= 0
        or prior.value <= 0
    ):
        return None
    return SignalValue(
        current.period,
        max(current.usable_at, prior.usable_at),
        100.0 * math.log(current.value / prior.value),
    )


def _current_monthly_values(
    versions: Sequence[VersionedValue], release_dates: Mapping[str, datetime]
) -> list[VersionedValue]:
    by_period: dict[str, VersionedValue] = {}
    for item in versions:
        prior = by_period.get(item.period)
        if prior is None or item.usable_at > prior.usable_at:
            by_period[item.period] = item
        elif item.usable_at == prior.usable_at and item != prior:
            raise FullPanelBuildError(f"ambiguous current-history rows for {item.period}")
    shifted: list[VersionedValue] = []
    for period, item in by_period.items():
        release = release_dates.get(period)
        if release is None or item.value is None or item.action.lower() == "delete":
            continue
        shifted.append(VersionedValue(period, item.value, release, "Replace"))
    return shifted


def _signal_for(
    series_id: str,
    origin: datetime,
    versions: Mapping[str, Sequence[VersionedValue]],
    release_dates: Mapping[str, Mapping[str, datetime]],
) -> SignalValue | None:
    if series_id in {"RTD_HICP", "RTD_INDUSTRIAL_PRODUCTION"}:
        return _latest_yoy_log(versions[series_id], origin)
    if series_id in {
        "RTD_UNEMPLOYMENT",
        "ECB_DEPOSIT_FACILITY_RATE",
        "ECB_YIELD_CURVE_2Y",
    }:
        return _latest_level(versions[series_id], origin)
    if series_id == "ECB_YIELD_CURVE_10Y":
        return _latest_spread(versions[series_id], versions["ECB_YIELD_CURVE_2Y"], origin)
    if series_id == "ECB_USD_EUR_REFERENCE_RATE":
        return _end_month_log_change(versions[series_id], origin)
    if series_id == "MIR_NFC_COST_OF_BORROWING":
        shifted = _current_monthly_values(versions[series_id], release_dates["MIR"])
        return _latest_level(shifted, origin)
    if series_id in {"BSI_NFC_ADJUSTED_LOANS", "BSI_MONETARY_AGGREGATE_M3"}:
        shifted = _current_monthly_values(versions[series_id], release_dates["BSI"])
        return _latest_level(shifted, origin)
    raise FullPanelBuildError(f"unregistered series in signal builder: {series_id}")


def _format_value(value: float) -> str:
    if not math.isfinite(value):
        raise FullPanelBuildError("attempted to serialize a nonfinite signal")
    return format(value, ".12g")


def _write_panel(path: Path, rows: Sequence[PanelRow]) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=PANEL_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(asdict(row) for row in rows)
    _atomic_text(path, buffer.getvalue())


def _write_audit(path: Path, audit: PanelBuildAudit) -> None:
    _atomic_text(path, json.dumps(asdict(audit), indent=2, sort_keys=True) + "\n")


def build_run023_panels(
    protocol_path: Path,
    raw_directory: Path,
    retrieval_manifest_path: Path,
    processed_directory: Path,
    audit_output: Path,
) -> PanelBuildAudit:
    """Construct only the two frozen point-in-time panels; perform no estimation."""

    protocol, manifest = load_run023_contract(protocol_path)
    if processed_directory.exists():
        raise FullPanelBuildError(f"refusing to overwrite processed bundle: {processed_directory}")
    if audit_output.exists():
        raise FullPanelBuildError(f"refusing to overwrite build audit: {audit_output}")
    retrieval = _mapping(
        yaml.safe_load(retrieval_manifest_path.read_text(encoding="utf-8")),
        "retrieval manifest",
    )
    records = {
        str(item["item_id"]): _mapping(item, "retrieval record")
        for item in retrieval.get("responses", [])
    }
    if len(records) != 17:
        raise FullPanelBuildError(
            "retrieval manifest must contain ten series and seven evidence items"
        )
    root = _project_root(protocol_path)
    manifest_path = root / "research/data/run_021_full_panel_manifest_v1.yaml"
    if retrieval.get("protocol", {}).get("sha256") != sha256_file(protocol_path):
        raise FullPanelBuildError("retrieval manifest protocol hash mismatch")
    if retrieval.get("source_registry", {}).get("sha256") != sha256_file(manifest_path):
        raise FullPanelBuildError("retrieval manifest source-registry hash mismatch")

    expected_urls = {str(item["series_id"]): str(item["query_url"]) for item in manifest["series"]}
    expected_urls.update(
        {
            key: str(value)
            for key, value in _mapping(manifest["release_sources"], "release_sources").items()
            if key != "rule"
        }
    )
    expected_urls["bsi_historical_release_index_run_023_addition"] = str(
        protocol["release_evidence_contract"]["bsi_historical_release_index_run_023_addition"]
    )
    if set(records) != set(expected_urls):
        raise FullPanelBuildError("retrieval record IDs differ from the frozen source set")
    filenames = {str(item["series_id"]): str(item["filename"]) for item in manifest["series"]}
    for item_id, registered_url in expected_urls.items():
        record = records[item_id]
        if record.get("registered_source_url") != registered_url:
            raise FullPanelBuildError(f"registered URL mismatch for {item_id}")
        if urlparse(str(record.get("final_url"))).hostname != urlparse(registered_url).hostname:
            raise FullPanelBuildError(f"final host mismatch for {item_id}")
        if item_id in filenames:
            response_path = raw_directory / "series" / filenames[item_id]
        else:
            response_path = raw_directory / "release_evidence" / f"{item_id}.html"
        if not response_path.is_file() or sha256_file(response_path) != record.get("sha256"):
            raise FullPanelBuildError(f"retrieval hash mismatch for {item_id}")
        if response_path.stat().st_size != record.get("response_bytes"):
            raise FullPanelBuildError(f"retrieval byte-count mismatch for {item_id}")
        expected_relative = response_path.resolve().relative_to(root).as_posix()
        if record.get("relative_path") != expected_relative:
            raise FullPanelBuildError(f"retrieval path mismatch for {item_id}")

    source_hashes: dict[str, str] = {}
    versions: dict[str, list[VersionedValue]] = {}
    maximum = int(protocol["retrieval_contract"]["maximum_response_bytes_per_series"])
    for raw in manifest["series"]:
        spec = _mapping(raw, "series")
        series_id = str(spec["series_id"])
        series_record = records[series_id]
        path = raw_directory / "series" / str(spec["filename"])
        if not path.is_file() or sha256_file(path) != series_record.get("sha256"):
            raise FullPanelBuildError(f"retrieval hash mismatch for {series_id}")
        validate_series_csv(spec, path, maximum)
        source_hashes[series_id] = str(series_record["sha256"])
        versions[series_id] = load_versioned_values(spec, path)

    mir_path = raw_directory / "release_evidence/mir_archive.html"
    bsi_path = raw_directory / "release_evidence/bsi_historical_release_index_run_023_addition.html"
    for item_id, path in (
        ("mir_archive", mir_path),
        ("bsi_historical_release_index_run_023_addition", bsi_path),
    ):
        if not path.is_file() or sha256_file(path) != records[item_id].get("sha256"):
            raise FullPanelBuildError(f"release-evidence hash mismatch: {item_id}")
    release_dates = {
        "MIR": parse_explicit_release_dates(mir_path.read_bytes(), "MIR"),
        "BSI": parse_explicit_release_dates(bsi_path.read_bytes(), "BSI"),
    }

    calendar = _mapping(manifest["calendar"], "calendar")
    origins = _origins(str(calendar["panel_start"]), str(calendar["panel_end"]))
    signs = {str(item["series_id"]): int(item["sign"]) for item in manifest["series"]}
    panel_rows: dict[str, list[PanelRow]] = {}
    missing_reasons: Counter[str] = Counter()
    coverage: dict[str, dict[str, float | int]] = {}
    temporal_violations = 0
    nonfinite = 0
    all_keys: list[tuple[str, str, str]] = []
    for raw_panel in manifest["panels"]:
        panel = _mapping(raw_panel, "panel")
        panel_id = str(panel["panel_id"])
        members = [str(value) for value in panel["series_ids"]]
        rows: list[PanelRow] = []
        observed_counts: Counter[str] = Counter()
        for origin_month, origin in origins:
            for series_id in members:
                signal = _signal_for(series_id, origin, versions, release_dates)
                all_keys.append((panel_id, origin_month, series_id))
                if signal is None:
                    if series_id.startswith(("MIR_", "BSI_")):
                        reason = "no_explicit_release_mapped_observation"
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
                        PanelRow(
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
                rows.append(
                    PanelRow(
                        panel_id,
                        origin_month,
                        origin.isoformat(),
                        series_id,
                        signal.observation_period,
                        signal.usable_at.isoformat(),
                        _format_value(value),
                        "0",
                        "",
                        source_hashes[series_id],
                    )
                )
        panel_rows[panel_id] = rows
        for series_id in members:
            observed = observed_counts[series_id]
            coverage[f"{panel_id}:{series_id}"] = {
                "observed_origins": observed,
                "total_origins": len(origins),
                "coverage_percent": round(100.0 * observed / len(origins), 6),
            }

    duplicate_keys = len(all_keys) - len(set(all_keys))
    expected_rows = {
        str(panel["panel_id"]): len(origins) * len(panel["series_ids"])
        for panel in manifest["panels"]
    }
    observed_rows = {key: len(value) for key, value in panel_rows.items()}
    passed = (
        duplicate_keys == 0
        and temporal_violations == 0
        and nonfinite == 0
        and observed_rows == expected_rows
        and bool(release_dates["MIR"])
        and bool(release_dates["BSI"])
    )
    if not passed:
        raise FullPanelBuildError(
            "panel integrity failed before publication: "
            f"duplicates={duplicate_keys}, temporal={temporal_violations}, "
            f"nonfinite={nonfinite}, rows={observed_rows}"
        )

    staging = Path(
        tempfile.mkdtemp(prefix=f".{processed_directory.name}.", dir=processed_directory.parent)
    )
    try:
        output_names = {
            "P0_CORE_REPLAY_AND_FAST": "p0_core_replay_and_fast.csv",
            "P1_AUGMENTED_BANK_CREDIT": "p1_augmented_bank_credit.csv",
        }
        for panel_id, rows in panel_rows.items():
            _write_panel(staging / output_names[panel_id], rows)
        calendar_buffer = io.StringIO(newline="")
        writer = csv.writer(calendar_buffer, lineterminator="\n")
        writer.writerow(["release_kind", "reference_period", "usable_timestamp"])
        for release_kind in ("MIR", "BSI"):
            for period, usable in sorted(release_dates[release_kind].items()):
                writer.writerow([release_kind, period, usable.isoformat()])
        _atomic_text(staging / "verified_release_calendar.csv", calendar_buffer.getvalue())
        processed_directory.parent.mkdir(parents=True, exist_ok=True)
        staging.replace(processed_directory)
        staging = Path()
    finally:
        if staging != Path() and staging.exists():
            shutil.rmtree(staging)

    audit = PanelBuildAudit(
        audit_id="run-023-full-panel-build-v1",
        protocol_sha256=sha256_file(protocol_path),
        source_registry_sha256=sha256_file(manifest_path),
        retrieval_manifest_sha256=sha256_file(retrieval_manifest_path),
        raw_source_count=10,
        release_evidence_count=7,
        release_mapping_counts={key: len(value) for key, value in release_dates.items()},
        panel_months=len(origins),
        panel_rows=observed_rows,
        series_coverage=dict(sorted(coverage.items())),
        missing_reasons=dict(sorted(missing_reasons.items())),
        point_in_time_violations=temporal_violations,
        duplicate_keys=duplicate_keys,
        nonfinite_values=nonfinite,
        reliability_engine_imported=False,
        state_estimation_performed=False,
        transmission_outcomes_accessed=False,
        synthetic_empirical_observations_used=False,
        passed=True,
    )
    _write_audit(audit_output, audit)
    return audit
