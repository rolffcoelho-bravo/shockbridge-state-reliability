from __future__ import annotations

import csv
import hashlib
import io
import math
import socket
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

import yaml

from shockbridge_state_risk.data.full_panel_build import (
    FRANKFURT,
    FullPanelBuildError,
    VersionedValue,
    _current_monthly_values,
    _download_with_retry,
    _end_month_log_change,
    _format_value,
    _latest_spread,
    _latest_yoy_log,
    _official_url,
    _signal_for,
    _snapshot,
    build_run023_panels,
    load_run023_contract,
    load_versioned_values,
    parse_explicit_release_dates,
    retrieve_run023_inputs,
    secure_download,
    validate_series_csv,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = (
    ROOT / "research/methodology/run_023_full_history_retrieval_and_panel_build_protocol_v1.yaml"
)
SOURCE_MANIFEST = ROOT / "research/data/run_021_full_panel_manifest_v1.yaml"


class _Response(io.BytesIO):
    def __init__(self, payload: bytes, final_url: str, content_type: str = "text/csv") -> None:
        super().__init__(payload)
        self._final_url = final_url
        self.headers = {"Content-Type": content_type}

    def geturl(self) -> str:
        return self._final_url

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def _version(
    period: str, value: float | None, timestamp: str, action: str = "Replace"
) -> VersionedValue:
    return VersionedValue(
        period,
        value,
        datetime.fromisoformat(timestamp).replace(tzinfo=FRANKFURT),
        action,
    )


class FullPanelBuildTests(unittest.TestCase):
    def test_registered_contract_is_frozen_and_outcome_blind(self) -> None:
        protocol, manifest = load_run023_contract(PROTOCOL)
        self.assertEqual(len(manifest["series"]), 10)
        self.assertEqual(len(manifest["panels"]), 2)
        self.assertFalse(protocol["scientific_boundary"]["reliability_engine_import_allowed"])
        self.assertFalse(protocol["scientific_boundary"]["transmission_outcomes_access_allowed"])
        self.assertFalse(
            protocol["scientific_boundary"]["synthetic_empirical_observations_allowed"]
        )

    def test_secure_download_enforces_same_host_byte_ceiling_and_immutability(self) -> None:
        url = "https://www.ecb.europa.eu/official.csv"
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "response.csv"

            def opener(*_args: object, **_kwargs: object) -> _Response:
                return _Response(b"abc", url)

            record = secure_download(
                item_id="fixture",
                item_type="series_csv",
                url=url,
                destination=destination,
                maximum_bytes=3,
                relative_path="response.csv",
                opener=opener,
            )
            self.assertEqual(record.sha256, hashlib.sha256(b"abc").hexdigest())
            self.assertEqual(destination.read_bytes(), b"abc")
            with self.assertRaisesRegex(FullPanelBuildError, "overwrite"):
                secure_download(
                    item_id="fixture",
                    item_type="series_csv",
                    url=url,
                    destination=destination,
                    maximum_bytes=3,
                    relative_path="response.csv",
                    opener=opener,
                )

        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "redirect.csv"

            def redirected(*_args: object, **_kwargs: object) -> _Response:
                return _Response(b"abc", "https://data.ecb.europa.eu/redirect.csv")

            with self.assertRaisesRegex(FullPanelBuildError, "redirected"):
                secure_download(
                    item_id="fixture",
                    item_type="series_csv",
                    url=url,
                    destination=destination,
                    maximum_bytes=3,
                    relative_path="redirect.csv",
                    opener=redirected,
                )
            self.assertFalse(destination.exists())

            def oversized(*_args: object, **_kwargs: object) -> _Response:
                return _Response(b"abcd", url)

            with self.assertRaisesRegex(FullPanelBuildError, "byte ceiling"):
                secure_download(
                    item_id="fixture",
                    item_type="series_csv",
                    url=url,
                    destination=destination,
                    maximum_bytes=3,
                    relative_path="redirect.csv",
                    opener=oversized,
                )
            self.assertFalse(destination.exists())

    def test_csv_validator_enforces_identity_unit_and_aware_replay_time(self) -> None:
        spec = {
            "series_id": "S",
            "full_series_key": "X.M.ONE",
            "frequency": "M",
            "unit": "IX",
            "timing_class": "A_REPLAY_ELIGIBLE",
            "query_url": (
                "https://data-api.ecb.europa.eu/service/data/X/M.ONE"
                "?startPeriod=2003-01&endPeriod=2003-12"
            ),
        }
        header = "KEY,FREQ,TIME_PERIOD,OBS_VALUE,UNIT,ACTION,VALID_FROM,VALID_TO\n"
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "series.csv"
            path.write_text(
                header + "X.M.ONE,M,2003-01,100,IX,Replace,2003-02-01T10:00:00+01:00,\n",
                encoding="utf-8",
            )
            self.assertEqual(validate_series_csv(spec, path, 10000), 1)
            path.write_text(
                header + "WRONG,M,2003-01,100,IX,Replace,2003-02-01T10:00:00+01:00,\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FullPanelBuildError, "wrong series key"):
                validate_series_csv(spec, path, 10000)
            path.write_text(
                header + "X.M.ONE,M,2003-01,100,IX,Replace,2003-02-01T10:00:00,\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FullPanelBuildError, "timezone-aware"):
                validate_series_csv(spec, path, 10000)

    def test_csv_validator_rejects_malformed_numeric_and_temporal_rows(self) -> None:
        spec = {
            "series_id": "S",
            "full_series_key": "X.M.ONE",
            "frequency": "M",
            "unit": "IX",
            "timing_class": "A_REPLAY_ELIGIBLE",
            "query_url": (
                "https://data-api.ecb.europa.eu/service/data/X/M.ONE"
                "?startPeriod=2003-01&endPeriod=2003-12"
            ),
        }
        header = "KEY,FREQ,TIME_PERIOD,OBS_VALUE,UNIT,ACTION,VALID_FROM,VALID_TO\n"
        cases = [
            (
                "no rows",
                header,
                "returned no rows",
            ),
            (
                "wrong frequency",
                header + "X.M.ONE,D,2003-01,1,IX,Replace,2003-02-01T10:00:00+01:00,\n",
                "wrong frequency",
            ),
            (
                "wrong unit",
                header + "X.M.ONE,M,2003-01,1,PC,Replace,2003-02-01T10:00:00+01:00,\n",
                "wrong unit",
            ),
            (
                "outside sample",
                header + "X.M.ONE,M,2004-01,1,IX,Replace,2004-02-01T10:00:00+01:00,\n",
                "outside the frozen sample",
            ),
            (
                "nonnumeric",
                header + "X.M.ONE,M,2003-01,nope,IX,Replace,2003-02-01T10:00:00+01:00,\n",
                "nonnumeric",
            ),
            (
                "nonfinite",
                header + "X.M.ONE,M,2003-01,nan,IX,Replace,2003-02-01T10:00:00+01:00,\n",
                "nonfinite",
            ),
            (
                "duplicate",
                header
                + "X.M.ONE,M,2003-01,1,IX,Replace,2003-02-01T10:00:00+01:00,\n"
                + "X.M.ONE,M,2003-01,1,IX,Replace,2003-02-01T10:00:00+01:00,\n",
                "duplicate version",
            ),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "series.csv"
            for label, payload, message in cases:
                with self.subTest(label=label):
                    path.write_text(payload, encoding="utf-8")
                    with self.assertRaisesRegex(FullPanelBuildError, message):
                        validate_series_csv(spec, path, 10000)

            path.write_text(
                "KEY,FREQ,TIME_PERIOD,OBS_VALUE,UNIT\nX.M.ONE,M,2003-01,1,IX\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FullPanelBuildError, "replay columns"):
                validate_series_csv(spec, path, 10000)

            malformed_query = dict(spec, query_url="https://data-api.ecb.europa.eu/x")
            path.write_text(
                header + "X.M.ONE,M,2003-01,1,IX,Replace,2003-02-01T10:00:00+01:00,\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FullPanelBuildError, "query boundaries"):
                validate_series_csv(malformed_query, path, 10000)

    def test_rtd_delete_and_missing_rows_use_action_timestamps_without_values(self) -> None:
        spec = {
            "series_id": "S",
            "full_series_key": "X.M.ONE",
            "frequency": "M",
            "unit": "IX",
            "timing_class": "A_REPLAY_ELIGIBLE",
            "query_url": (
                "https://data-api.ecb.europa.eu/service/data/X/M.ONE"
                "?startPeriod=2003-01&endPeriod=2003-12"
            ),
        }
        payload = (
            "KEY,FREQ,TIME_PERIOD,OBS_VALUE,UNIT,ACTION,VALID_FROM,VALID_TO\n"
            "X.M.ONE,M,2003-01,,IX,Replace,2003-02-01T10:00:00+01:00,\n"
            "X.M.ONE,M,2003-02,,,Delete,,2003-03-01T10:00:00+01:00\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "series.csv"
            path.write_text(payload, encoding="utf-8")
            self.assertEqual(validate_series_csv(spec, path, 10000), 2)
            versions = load_versioned_values(spec, path)
            self.assertEqual([item.value for item in versions], [None, None])
            self.assertEqual(
                versions[1].usable_at,
                datetime.fromisoformat("2003-03-01T10:00:00+01:00"),
            )

            path.write_text(
                payload.replace("M,2003-02,,,Delete", "M,2003-02,,PC,Delete"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FullPanelBuildError, "wrong unit"):
                validate_series_csv(spec, path, 10000)

    def test_release_parser_accepts_only_explicit_reference_periods(self) -> None:
        payload = b"""
        <html><body>
        <p>4 February 2025</p><a>Euro area bank interest rate statistics: January 2025</a>
        <p>15 January 2004</p><a>MFI interest rate statistics</a>
        <p>27 February 2003</p><a>Monetary developments in the euro area: January 2003</a>
        </body></html>
        """
        mir = parse_explicit_release_dates(payload, "MIR")
        bsi = parse_explicit_release_dates(payload, "BSI")
        self.assertEqual(set(mir), {"2025-01"})
        self.assertEqual(set(bsi), {"2003-01"})
        self.assertEqual(mir["2025-01"].hour, 10)
        self.assertEqual(mir["2025-01"].second, 1)
        with self.assertRaisesRegex(FullPanelBuildError, "MIR or BSI"):
            parse_explicit_release_dates(payload, "OTHER")

        conflict = b"""
        <p>4 February 2025</p><a>Euro area bank interest rate statistics: January 2025</a>
        <p>5 February 2025</p><a>Euro area bank interest rate statistics: January 2025</a>
        """
        with self.assertRaisesRegex(FullPanelBuildError, "conflicting"):
            parse_explicit_release_dates(conflict, "MIR")
        with self.assertRaisesRegex(FullPanelBuildError, "not UTF-8"):
            parse_explicit_release_dates(b"\xff", "BSI")

    def test_vintage_transformations_are_strict_and_revision_aware(self) -> None:
        origin = datetime(2004, 2, 1, 23, 59, 59, tzinfo=FRANKFURT)
        vintages = [
            _version("2002-12", 100.0, "2003-01-01T10:00:00"),
            _version("2003-12", 110.0, "2004-01-15T10:00:00"),
            _version("2003-12", 120.0, "2004-02-01T23:59:59"),
        ]
        yoy = _latest_yoy_log(vintages, origin)
        self.assertIsNotNone(yoy)
        assert yoy is not None
        self.assertAlmostEqual(yoy.value, 100.0 * math.log(1.1))

        short = [_version("2004-01-30", 2.0, "2004-01-31T10:00:00")]
        long = [_version("2004-01-30", 3.5, "2004-01-31T10:00:00")]
        spread = _latest_spread(long, short, origin)
        self.assertIsNotNone(spread)
        assert spread is not None
        self.assertEqual(spread.value, 1.5)

        fx = [
            _version("2003-12-31", 1.0, "2003-12-31T17:00:00"),
            _version("2004-01-30", 1.1, "2004-01-30T17:00:00"),
        ]
        self.assertIsNotNone(_end_month_log_change(fx, origin))

        revisions = [
            _version("2004-01", 3.0, "2004-03-01T10:00:00"),
            _version("2004-01", 3.2, "2004-04-01T10:00:00"),
        ]
        release = {"2004-01": datetime(2004, 2, 3, 10, 0, 1, tzinfo=FRANKFURT)}
        shifted = _current_monthly_values(revisions, release)
        self.assertEqual(
            [(item.value, item.usable_at) for item in shifted], [(3.2, release["2004-01"])]
        )
        contradictory = [*revisions, _version("2004-01", 9.9, "2004-04-01T10:00:00")]
        with self.assertRaisesRegex(FullPanelBuildError, "ambiguous current-history"):
            _current_monthly_values(contradictory, release)

        deleted = [
            *vintages,
            _version("2003-12", None, "2004-01-20T10:00:00", action="Delete"),
        ]
        self.assertIsNone(_latest_yoy_log(deleted, origin))
        equality_origin = datetime(2004, 2, 1, 23, 59, 59, tzinfo=FRANKFURT)
        only_equal = [_version("2004-01", 1.0, "2004-02-01T23:59:59")]
        self.assertIsNone(_latest_yoy_log(only_equal, equality_origin))

    def test_complete_mocked_retrieval_promotes_only_valid_bundle(self) -> None:
        manifest = yaml.safe_load(SOURCE_MANIFEST.read_text(encoding="utf-8"))
        protocol = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
        payloads: dict[str, bytes] = {}
        for spec in manifest["series"]:
            query = parse_qs(urlparse(spec["query_url"]).query)
            period = query["startPeriod"][0]
            valid_from = (
                "2003-02-01T10:00:00+01:00"
                if spec["series_id"] != "ECB_USD_EUR_REFERENCE_RATE"
                else ""
            )
            text = (
                "KEY,FREQ,TIME_PERIOD,OBS_VALUE,UNIT,ACTION,VALID_FROM,VALID_TO\n"
                f"{spec['full_series_key']},{spec['frequency']},{period},1,"
                f"{spec['unit']},Replace,{valid_from},\n"
            )
            payloads[spec["query_url"]] = text.encode()
        evidence_urls = {
            str(value) for key, value in manifest["release_sources"].items() if key != "rule"
        }
        evidence_urls.add(
            protocol["release_evidence_contract"]["bsi_historical_release_index_run_023_addition"]
        )
        for url in evidence_urls:
            payloads[url] = b"<html><body>Official release evidence</body></html>"

        def opener(request: object, **_kwargs: object) -> _Response:
            url = str(request.full_url)  # type: ignore[attr-defined]
            return _Response(
                payloads[url], url, "text/html" if url in evidence_urls else "text/csv"
            )

        with tempfile.TemporaryDirectory(dir=ROOT / "data/raw") as directory:
            raw = Path(directory) / "bundle"
            retrieval_manifest = Path(directory) / "retrieval.yaml"
            records = retrieve_run023_inputs(
                PROTOCOL,
                raw,
                retrieval_manifest,
                opener=opener,
            )
            self.assertEqual(len(records), 17)
            self.assertEqual(len(list((raw / "series").glob("*.csv"))), 10)
            self.assertEqual(len(list((raw / "release_evidence").glob("*.html"))), 7)
            registered = yaml.safe_load(retrieval_manifest.read_text(encoding="utf-8"))
            self.assertEqual(len(registered["responses"]), 17)
            with self.assertRaisesRegex(FullPanelBuildError, "overwrite raw bundle"):
                retrieve_run023_inputs(
                    PROTOCOL,
                    raw,
                    Path(directory) / "second.yaml",
                    opener=opener,
                )

        first_url = manifest["series"][0]["query_url"]
        valid_payload = payloads[first_url]
        payloads[first_url] = valid_payload.replace(
            str(manifest["series"][0]["full_series_key"]).encode(), b"WRONG.KEY"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "data/raw") as directory:
            raw = Path(directory) / "invalid-bundle"
            with self.assertRaisesRegex(FullPanelBuildError, "wrong series key"):
                retrieve_run023_inputs(
                    PROTOCOL,
                    raw,
                    Path(directory) / "failed.yaml",
                    opener=opener,
                )
            self.assertFalse(raw.exists())
            self.assertEqual(list(Path(directory).glob(".invalid-bundle.*")), [])
        payloads[first_url] = valid_payload

    def test_secure_download_rejects_invalid_contract_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "x"
            for url in ("http://www.ecb.europa.eu/x", "https://example.com/x"):
                with (
                    self.subTest(url=url),
                    self.assertRaisesRegex(FullPanelBuildError, "official HTTPS host"),
                ):
                    secure_download(
                        item_id="x",
                        item_type="evidence",
                        url=url,
                        destination=destination,
                        maximum_bytes=1,
                        relative_path="x",
                    )
            with self.assertRaisesRegex(FullPanelBuildError, "positive integer"):
                secure_download(
                    item_id="x",
                    item_type="evidence",
                    url="https://www.ecb.europa.eu/x",
                    destination=destination,
                    maximum_bytes=False,
                    relative_path="x",
                )
            with self.assertRaisesRegex(FullPanelBuildError, "timeout seconds"):
                secure_download(
                    item_id="x",
                    item_type="evidence",
                    url="https://www.ecb.europa.eu/x",
                    destination=destination,
                    maximum_bytes=1,
                    relative_path="x",
                    timeout_seconds=math.inf,
                )

            def failed(*_args: object, **_kwargs: object) -> _Response:
                raise OSError("network fixture failure")

            with self.assertRaisesRegex(FullPanelBuildError, "official retrieval failed"):
                secure_download(
                    item_id="x",
                    item_type="evidence",
                    url="https://www.ecb.europa.eu/x",
                    destination=destination,
                    maximum_bytes=1,
                    relative_path="x",
                    opener=failed,
                )

    def test_transport_retry_is_bounded_and_provenance_recorded(self) -> None:
        url = "https://www.ecb.europa.eu/official.csv"
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "response.csv"
            attempts = 0

            def transient(*_args: object, **_kwargs: object) -> _Response:
                nonlocal attempts
                attempts += 1
                if attempts == 1:
                    raise socket.timeout("fixture timeout")
                return _Response(b"ok", url)

            record = _download_with_retry(
                maximum_attempts=3,
                item_id="fixture",
                item_type="series_csv",
                url=url,
                destination=destination,
                maximum_bytes=10,
                relative_path="response.csv",
                opener=transient,
            )
            self.assertEqual(record.attempt_count, 2)
            self.assertEqual(record.prior_attempt_error_classes, ["timeout"])
            self.assertEqual(destination.read_bytes(), b"ok")

            wrapped_attempts = 0

            def wrapped_transient(*_args: object, **_kwargs: object) -> _Response:
                nonlocal wrapped_attempts
                wrapped_attempts += 1
                if wrapped_attempts == 1:
                    raise URLError(TimeoutError("wrapped fixture timeout"))
                return _Response(b"wrapped", url)

            wrapped_record = _download_with_retry(
                maximum_attempts=3,
                item_id="wrapped-fixture",
                item_type="series_csv",
                url=url,
                destination=Path(directory) / "wrapped.csv",
                maximum_bytes=10,
                relative_path="wrapped.csv",
                opener=wrapped_transient,
            )
            self.assertEqual(wrapped_record.attempt_count, 2)
            self.assertEqual(wrapped_record.prior_attempt_error_classes, ["timeout"])
            self.assertEqual((Path(directory) / "wrapped.csv").read_bytes(), b"wrapped")

            with self.assertRaisesRegex(FullPanelBuildError, "maximum attempts"):
                _download_with_retry(maximum_attempts=False)

            def nonretryable(*_args: object, **_kwargs: object) -> _Response:
                return _Response(b"x", "https://data.ecb.europa.eu/x")

            with self.assertRaisesRegex(FullPanelBuildError, "redirected"):
                _download_with_retry(
                    maximum_attempts=3,
                    item_id="fixture",
                    item_type="series_csv",
                    url=url,
                    destination=Path(directory) / "redirect.csv",
                    maximum_bytes=10,
                    relative_path="redirect.csv",
                    opener=nonretryable,
                )

    def test_internal_fail_closed_edges(self) -> None:
        with self.assertRaisesRegex(FullPanelBuildError, "must use www"):
            _official_url("https://data.ecb.europa.eu/x", expected_host="www.ecb.europa.eu")
        with self.assertRaisesRegex(FullPanelBuildError, "non-root path"):
            _official_url("https://www.ecb.europa.eu/")
        with self.assertRaisesRegex(FullPanelBuildError, "nonfinite signal"):
            _format_value(math.nan)
        with self.assertRaisesRegex(FullPanelBuildError, "unregistered series"):
            _signal_for("UNKNOWN", datetime.now(FRANKFURT), {}, {})
        origin = datetime(2004, 1, 1, tzinfo=FRANKFURT)
        contradictory = [
            _version("2003-12", 1.0, "2003-12-01T10:00:00"),
            _version("2003-12", 2.0, "2003-12-01T10:00:00"),
        ]
        with self.assertRaisesRegex(FullPanelBuildError, "ambiguous same-time"):
            _snapshot(contradictory, origin)

    def test_build_rejects_manifest_provenance_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            retrieval = Path(directory) / "retrieval.yaml"
            retrieval.write_text(
                yaml.safe_dump(
                    {
                        "protocol": {"sha256": "0" * 64},
                        "source_registry": {
                            "sha256": hashlib.sha256(SOURCE_MANIFEST.read_bytes()).hexdigest()
                        },
                        "responses": [],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FullPanelBuildError, "ten series"):
                build_run023_panels(
                    PROTOCOL,
                    Path(directory) / "raw",
                    retrieval,
                    Path(directory) / "processed",
                    Path(directory) / "audit.json",
                )

    def test_end_to_end_fixture_builds_exact_grids_without_estimation(self) -> None:
        manifest = yaml.safe_load(SOURCE_MANIFEST.read_text(encoding="utf-8"))
        protocol_hash = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
        registry_hash = hashlib.sha256(SOURCE_MANIFEST.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            base = Path(directory)
            raw = base / "raw"
            series_dir = raw / "series"
            evidence_dir = raw / "release_evidence"
            series_dir.mkdir(parents=True)
            evidence_dir.mkdir(parents=True)
            records: list[dict[str, object]] = []
            rows_by_id = {
                "RTD_HICP": [("2002-01", 100.0), ("2003-01", 105.0)],
                "RTD_INDUSTRIAL_PRODUCTION": [("2002-01", 100.0), ("2003-01", 102.0)],
                "RTD_UNEMPLOYMENT": [("2002-12", 7.0)],
                "ECB_DEPOSIT_FACILITY_RATE": [("2002-12-31", 2.0)],
                "ECB_YIELD_CURVE_2Y": [("2002-12-31", 2.5)],
                "ECB_YIELD_CURVE_10Y": [("2002-12-31", 4.0)],
                "ECB_USD_EUR_REFERENCE_RATE": [
                    ("2002-11-29", 1.0),
                    ("2002-12-31", 1.1),
                ],
                "MIR_NFC_COST_OF_BORROWING": [("2003-01", 4.0)],
                "BSI_NFC_ADJUSTED_LOANS": [("2003-01", 2.0)],
                "BSI_MONETARY_AGGREGATE_M3": [("2003-01", 3.0)],
            }
            for spec in manifest["series"]:
                path = series_dir / spec["filename"]
                with path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle, lineterminator="\n")
                    writer.writerow(
                        [
                            "KEY",
                            "FREQ",
                            "TIME_PERIOD",
                            "OBS_VALUE",
                            "UNIT",
                            "ACTION",
                            "VALID_FROM",
                            "VALID_TO",
                        ]
                    )
                    for index, (period, value) in enumerate(rows_by_id[spec["series_id"]]):
                        if spec["series_id"] == "ECB_USD_EUR_REFERENCE_RATE":
                            valid_from = ""
                        else:
                            valid_from = f"2003-02-{index + 1:02d}T10:00:00+01:00"
                        writer.writerow(
                            [
                                spec["full_series_key"],
                                spec["frequency"],
                                period,
                                value,
                                spec["unit"],
                                "Replace",
                                valid_from,
                                "",
                            ]
                        )
                records.append(
                    self._record(spec["series_id"], "series_csv", spec["query_url"], path)
                )

            evidence_urls = {
                key: value for key, value in manifest["release_sources"].items() if key != "rule"
            }
            protocol = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
            evidence_urls["bsi_historical_release_index_run_023_addition"] = protocol[
                "release_evidence_contract"
            ]["bsi_historical_release_index_run_023_addition"]
            for item_id, url in evidence_urls.items():
                if item_id == "mir_archive":
                    body = (
                        "<p>3 February 2003</p>"
                        "<a>Euro area bank interest rate statistics: January 2003</a>"
                    )
                elif item_id == "bsi_historical_release_index_run_023_addition":
                    body = (
                        "<p>27 February 2003</p>"
                        "<a>Monetary developments in the euro area: January 2003</a>"
                    )
                else:
                    body = "<html><body>Official fixture evidence</body></html>"
                path = evidence_dir / f"{item_id}.html"
                path.write_text(body, encoding="utf-8")
                records.append(self._record(item_id, "release_evidence_html", url, path))

            retrieval_path = base / "retrieval.yaml"
            retrieval_path.write_text(
                yaml.safe_dump(
                    {
                        "protocol": {"sha256": protocol_hash},
                        "source_registry": {"sha256": registry_hash},
                        "responses": records,
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            processed = base / "processed"
            audit_path = base / "audit.json"
            audit = build_run023_panels(PROTOCOL, raw, retrieval_path, processed, audit_path)
            self.assertTrue(audit.passed)
            self.assertEqual(audit.panel_months, 274)
            self.assertEqual(audit.panel_rows["P0_CORE_REPLAY_AND_FAST"], 274 * 7)
            self.assertEqual(audit.panel_rows["P1_AUGMENTED_BANK_CREDIT"], 274 * 10)
            self.assertEqual(audit.point_in_time_violations, 0)
            self.assertFalse(audit.state_estimation_performed)
            self.assertFalse(audit.transmission_outcomes_accessed)
            self.assertTrue((processed / "verified_release_calendar.csv").is_file())

            mutated = records[0].copy()
            mutated["sha256"] = "0" * 64
            records[0] = mutated
            retrieval_path.write_text(
                yaml.safe_dump(
                    {
                        "protocol": {"sha256": protocol_hash},
                        "source_registry": {"sha256": registry_hash},
                        "responses": records,
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FullPanelBuildError, "hash mismatch"):
                build_run023_panels(
                    PROTOCOL,
                    raw,
                    retrieval_path,
                    base / "second-processed",
                    base / "second-audit.json",
                )

    @staticmethod
    def _record(item_id: str, item_type: str, url: str, path: Path) -> dict[str, object]:
        return {
            "item_id": item_id,
            "item_type": item_type,
            "registered_source_url": url,
            "final_url": url,
            "retrieved_at_utc": "2026-10-15T12:00:00+00:00",
            "response_bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "content_type": "text/plain",
            "relative_path": path.resolve().relative_to(ROOT).as_posix()
            if path.resolve().is_relative_to(ROOT)
            else path.name,
        }

    def test_protocol_hash_mutation_fails_before_build(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            protocol = Path(directory) / "protocol.yaml"
            protocol.write_bytes(PROTOCOL.read_bytes())
            with patch(
                "shockbridge_state_risk.data.full_panel_build._project_root",
                return_value=ROOT,
            ):
                payload = yaml.safe_load(protocol.read_text(encoding="utf-8"))
                payload["bound_inputs"][0]["sha256"] = "0" * 64
                protocol.write_text(yaml.safe_dump(payload), encoding="utf-8")
                with self.assertRaisesRegex(FullPanelBuildError, "hash mismatch"):
                    load_run023_contract(protocol)


if __name__ == "__main__":
    unittest.main()
