from __future__ import annotations

import copy
import csv
import hashlib
import json
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

import yaml

from shockbridge_state_risk.data import dfr_effective_date as run025
from shockbridge_state_risk.data import full_panel_build as run023
from shockbridge_state_risk.data.dfr_effective_date import (
    _active_api_values,
    _load_protocol,
    build_run025_dfr_effective_date_amendment,
    cross_validate_effective_rates,
    parse_effective_rate_table,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/methodology/run_025_dfr_effective_date_source_audit_protocol_v1.yaml"
SOURCE_MANIFEST = ROOT / "data/manifests/run_025_dfr_effective_date_source_v1.yaml"
SOURCE_HTML = ROOT / "data/raw/run025_dfr_effective_dates_v1/ecb_key_interest_rates.html"
EVIDENCE_SKIP_REASON = "requires local hash-registered evidence"


def _protocol(*, minimum_events: int = 1, minimum_days: int = 2) -> dict[str, object]:
    payload = copy.deepcopy(yaml.safe_load(PROTOCOL.read_text(encoding="utf-8")))
    payload["cross_validation_contract"]["acceptance_requirements"].update(
        minimum_official_events_in_window=minimum_events,
        minimum_compared_api_days=minimum_days,
    )
    payload["parser_contract"]["target_event_window"] = {
        "first_required_baseline_date": "2002-12-06",
        "last_admissible_effective_date": "2003-12-31",
    }
    payload["cross_validation_contract"]["comparison_window"] = {
        "start": "2002-12-06",
        "end": "2002-12-07",
    }
    return payload


def _html(*rows: str, duplicate_table: bool = False, unit: bool = True) -> bytes:
    table = (
        "<table><thead><tr><th colspan='2'>Date (with effect from)</th>"
        "<th>Deposit facility</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )
    return (
        "<html><body><h1>Key ECB interest rates</h1>"
        + table
        + (table if duplicate_table else "")
        + ("<p>interest rate levels in percentages per annum</p>" if unit else "")
        + "</body></html>"
    ).encode()


def _row(year: str, day: str, value: str) -> str:
    return f"<tr><td>{year}</td><td>{day}</td><td>{value}</td></tr>"


class DfrEffectiveDateTests(unittest.TestCase):
    def test_low_level_source_contracts_fail_closed(self) -> None:
        protocol = _protocol(minimum_events=2)
        with self.assertRaisesRegex(run023.FullPanelBuildError, "not UTF-8"):
            parse_effective_rate_table(b"\xff", protocol)
        with self.assertRaisesRegex(run023.FullPanelBuildError, "precedes a valid year"):
            parse_effective_rate_table(_html(_row("", "6 Dec.", "1.75")), protocol)
        with self.assertRaisesRegex(run023.FullPanelBuildError, "invalid date"):
            parse_effective_rate_table(_html(_row("2002", "31 Feb.", "1.75")), protocol)
        with self.assertRaisesRegex(run023.FullPanelBuildError, "too few"):
            parse_effective_rate_table(_html(_row("2002", "6 Dec.", "1.75")), protocol)
        for value, message in (("", "missing"), ("abc", "not a decimal"), ("NaN", "nonfinite")):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(run023.FullPanelBuildError, message),
            ):
                parse_effective_rate_table(_html(_row("2002", "6 Dec.", value)), _protocol())

        self.assertEqual(run025._protocol_date(date(2002, 12, 6), "day"), date(2002, 12, 6))
        self.assertEqual(run025._protocol_date("2002-12-06", "day"), date(2002, 12, 6))
        for value, message in (
            (run025.datetime(2002, 12, 6), "without time"),
            ("not-a-date", "not an ISO date"),
            (1, "must be an ISO date"),
        ):
            with (
                self.subTest(protocol_date=value),
                self.assertRaisesRegex(run023.FullPanelBuildError, message),
            ):
                run025._protocol_date(value, "day")

    def test_html_state_machine_rejects_malformed_nesting(self) -> None:
        parser = run025._TableParser()
        parser.handle_starttag("table", [])
        with self.assertRaisesRegex(run023.FullPanelBuildError, "nested official-rate tables"):
            parser.handle_starttag("table", [])

        parser = run025._TableParser()
        parser.handle_starttag("table", [])
        parser.handle_starttag("tr", [])
        with self.assertRaisesRegex(run023.FullPanelBuildError, "nested official-rate rows"):
            parser.handle_starttag("tr", [])
        parser.handle_starttag("td", [])
        with self.assertRaisesRegex(run023.FullPanelBuildError, "nested official-rate cells"):
            parser.handle_starttag("th", [])
        with self.assertRaisesRegex(run023.FullPanelBuildError, "incomplete"):
            parser.handle_endtag("table")

        parser = run025._TableParser()
        with self.assertRaisesRegex(run023.FullPanelBuildError, "unbalanced"):
            parser.handle_endtag("sup")
        parser.handle_starttag("sup", [])
        with self.assertRaisesRegex(run023.FullPanelBuildError, "unterminated.*footnote"):
            parser.close()

    def test_retained_api_contract_rejects_hostile_rows(self) -> None:
        fields = [
            "KEY",
            "TIME_PERIOD",
            "OBS_VALUE",
            "ACTION",
            "VALID_FROM",
            "VALID_TO",
            "TITLE",
            "UNIT",
        ]
        base = {
            "KEY": "FM.D.U2.EUR.4F.KR.DFR.LEV",
            "TIME_PERIOD": "2018-06-06",
            "OBS_VALUE": "-0.40",
            "ACTION": "Replace",
            "VALID_FROM": "2018-06-07T02:57:07+02:00",
            "VALID_TO": "",
            "TITLE": "Deposit facility - date of changes (raw data) - Level",
            "UNIT": "PCPA",
        }

        def write(rows: list[dict[str, str]], path: Path) -> None:
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)

        cases = [
            ([], "empty"),
            ([base | {"KEY": "wrong"}], "unexpected series"),
            ([base | {"TIME_PERIOD": "not-a-date"}], "invalid period"),
            ([base | {"VALID_FROM": ""}], "lacks a database timestamp"),
            ([base | {"TITLE": "wrong"}], "lacks frozen semantics"),
            ([base | {"UNIT": "PC"}], "not percent per annum"),
            ([base | {"OBS_VALUE": "infinite"}], "not a decimal"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dfr.csv"
            for rows, message in cases:
                with self.subTest(message=message):
                    write(rows, path)
                    with self.assertRaisesRegex(run023.FullPanelBuildError, message):
                        _active_api_values(path)
            conflict = base | {"OBS_VALUE": "-0.39"}
            write([base, conflict], path)
            with self.assertRaisesRegex(run023.FullPanelBuildError, "conflict"):
                _active_api_values(path)

    def test_comparison_and_output_guards_cover_negative_paths(self) -> None:
        events = [run025.EffectiveRateEvent(date(2002, 12, 6), Decimal("1.75"))]
        protocol = _protocol()
        protocol["cross_validation_contract"]["comparison_window"] = {
            "start": "2002-12-01",
            "end": "2002-12-07",
        }
        audit = cross_validate_effective_rates(
            events,
            {date(2002, 12, 1): Decimal("1.75"), date(2002, 12, 6): Decimal("1.75")},
            protocol,
        )
        self.assertFalse(audit["passed"])
        self.assertEqual(audit["unmatched_api_days"], 1)

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            malformed = temporary / "panel.csv"
            malformed.write_text("wrong,header\n1,2\n", encoding="utf-8")
            with self.assertRaisesRegex(run023.FullPanelBuildError, "unexpected panel schema"):
                run025._read_panel(malformed)

            destination = temporary / "audit.json"
            destination.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(run023.FullPanelBuildError, "overwrite"):
                run025._atomic_json({"passed": True}, destination)

        row = {
            "panel_id": "P0_CORE_REPLAY_AND_FAST",
            "origin_month": "2002-12",
            "origin_timestamp": "2002-12-01T23:59:59+01:00",
            "series_id": run025.DFR_SERIES_ID,
            "observation_period": "",
            "usable_timestamp": "",
            "transformed_value": "",
            "is_missing": "1",
            "missing_reason": "old",
            "source_response_sha256": "old",
        }
        rebuilt, panel_audit = run025._rebuild_panel([row, row], events, "new-hash", next_day=False)
        self.assertEqual(panel_audit["duplicate_keys"], 1)
        self.assertTrue(all(item["is_missing"] == "1" for item in rebuilt))

    def test_parser_admits_optional_month_dot_footnote_and_inherited_year(self) -> None:
        payload = _html(
            _row("2003", "7 Mar.<sup>1</sup>", "1.50"),
            _row("", "6 Dec", "\N{MINUS SIGN}0.10"),
            _row("2002", "6 Dec.", "1.75"),
        )
        events = parse_effective_rate_table(payload, _protocol())
        self.assertEqual(
            events,
            [
                # Source order is irrelevant; output is strictly increasing.
                type(events[0])(date(2002, 12, 6), Decimal("1.75")),
                type(events[0])(date(2003, 3, 7), Decimal("1.50")),
                type(events[0])(date(2003, 12, 6), Decimal("-0.10")),
            ],
        )

    def test_parser_fails_closed_on_semantic_or_table_ambiguity(self) -> None:
        row = _row("2002", "6 Dec.", "1.75")
        with self.assertRaisesRegex(run023.FullPanelBuildError, "required semantics"):
            parse_effective_rate_table(_html(row, unit=False), _protocol())
        with self.assertRaisesRegex(run023.FullPanelBuildError, "exactly one"):
            parse_effective_rate_table(_html(row, duplicate_table=True), _protocol())

    def test_parser_rejects_conflicting_duplicate_and_missing_baseline(self) -> None:
        with self.assertRaisesRegex(run023.FullPanelBuildError, "conflicts"):
            parse_effective_rate_table(
                _html(
                    _row("2002", "6 Dec.", "1.75"),
                    _row("2002", "6 Dec.", "1.50"),
                ),
                _protocol(),
            )
        with self.assertRaisesRegex(run023.FullPanelBuildError, "baseline"):
            parse_effective_rate_table(_html(_row("2003", "7 Mar.", "1.50")), _protocol())

    def test_cross_validation_requires_exact_decimal_equality(self) -> None:
        events = parse_effective_rate_table(_html(_row("2002", "6 Dec.", "1.75")), _protocol())
        exact = {
            date(2002, 12, 6): Decimal("1.7500000"),
            date(2002, 12, 7): Decimal("1.75"),
        }
        accepted = cross_validate_effective_rates(events, exact, _protocol())
        self.assertTrue(accepted["passed"])
        self.assertEqual(accepted["exact_agreement_percent"], 100.0)

        changed = dict(exact)
        changed[date(2002, 12, 7)] = Decimal("1.76")
        rejected = cross_validate_effective_rates(events, changed, _protocol())
        self.assertFalse(rejected["passed"])
        self.assertEqual(rejected["conflicting_days"], 1)

    def test_active_api_values_applies_database_actions_without_using_them_as_clock(self) -> None:
        fields = [
            "KEY",
            "TIME_PERIOD",
            "OBS_VALUE",
            "ACTION",
            "VALID_FROM",
            "VALID_TO",
            "TITLE",
            "UNIT",
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dfr.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "KEY": "FM.D.U2.EUR.4F.KR.DFR.LEV",
                            "TIME_PERIOD": "2018-06-06",
                            "OBS_VALUE": "",
                            "ACTION": "Delete",
                            "VALID_FROM": "",
                            "VALID_TO": "2018-06-06T04:50:32+02:00",
                            "TITLE": "",
                            "UNIT": "",
                        },
                        {
                            "KEY": "FM.D.U2.EUR.4F.KR.DFR.LEV",
                            "TIME_PERIOD": "2018-06-06",
                            "OBS_VALUE": "-0.40",
                            "ACTION": "Replace",
                            "VALID_FROM": "2018-06-07T02:57:07+02:00",
                            "VALID_TO": "",
                            "TITLE": "Deposit facility - date of changes (raw data) - Level",
                            "UNIT": "PCPA",
                        },
                    ]
                )
            self.assertEqual(_active_api_values(path), {date(2018, 6, 6): Decimal("-0.40")})

    @unittest.skipUnless(SOURCE_HTML.is_file(), EVIDENCE_SKIP_REASON)
    def test_authentic_protocol_verifies_all_bound_inputs(self) -> None:
        root, protocol = _load_protocol(PROTOCOL)
        self.assertEqual(root, ROOT)
        self.assertEqual(len(protocol["bound_inputs"]), 8)

    @unittest.skipUnless(SOURCE_HTML.is_file(), EVIDENCE_SKIP_REASON)
    def test_canonical_source_matches_every_retained_api_day(self) -> None:
        protocol = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
        events = parse_effective_rate_table(SOURCE_HTML.read_bytes(), protocol)
        values = _active_api_values(
            ROOT / protocol["bound_inputs"]["retained_ecb_dfr_api_response"]["path"]
        )
        audit = cross_validate_effective_rates(events, values, protocol)
        self.assertEqual(len(events), 51)
        self.assertEqual(audit["compared_api_days"], 8366)
        self.assertEqual(audit["exact_agreements"], 8366)
        self.assertTrue(audit["passed"])

    def test_full_amendment_is_immutable_and_preserves_claim_firewall(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            (temporary / "pyproject.toml").write_text(
                "[project]\nname='fixture'\n", encoding="utf-8"
            )
            protocol = _protocol()
            protocol["parser_contract"]["target_event_window"]["last_admissible_effective_date"] = (
                "2002-12-31"
            )
            protocol["cross_validation_contract"]["comparison_window"] = {
                "start": "2002-12-06",
                "end": "2002-12-07",
            }
            protocol["cross_validation_contract"]["acceptance_requirements"].update(
                minimum_official_events_in_window=1,
                minimum_compared_api_days=2,
            )

            fields = [
                "KEY",
                "TIME_PERIOD",
                "OBS_VALUE",
                "ACTION",
                "VALID_FROM",
                "VALID_TO",
                "TITLE",
                "UNIT",
            ]
            api_path = temporary / "bound/retained.csv"
            api_path.parent.mkdir(parents=True)
            with api_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for day in ("2002-12-06", "2002-12-07"):
                    writer.writerow(
                        {
                            "KEY": "FM.D.U2.EUR.4F.KR.DFR.LEV",
                            "TIME_PERIOD": day,
                            "OBS_VALUE": "1.75",
                            "ACTION": "Replace",
                            "VALID_FROM": day + "T01:00:00+01:00",
                            "VALID_TO": "",
                            "TITLE": "Deposit facility - date of changes (raw data) - Level",
                            "UNIT": "PCPA",
                        }
                    )

            def panel(path: Path, panel_id: str) -> None:
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=run025.PANEL_FIELDS)
                    writer.writeheader()
                    writer.writerows(
                        [
                            {
                                "panel_id": panel_id,
                                "origin_month": "2003-01",
                                "origin_timestamp": "2003-01-01T23:59:59+01:00",
                                "series_id": run025.DFR_SERIES_ID,
                                "observation_period": "",
                                "usable_timestamp": "",
                                "transformed_value": "",
                                "is_missing": "1",
                                "missing_reason": "old",
                                "source_response_sha256": "old",
                            },
                            {
                                "panel_id": panel_id,
                                "origin_month": "2003-01",
                                "origin_timestamp": "2003-01-01T23:59:59+01:00",
                                "series_id": "OTHER_OFFICIAL_SERIES",
                                "observation_period": "2002-12",
                                "usable_timestamp": "2002-12-20T00:00:00+01:00",
                                "transformed_value": "2",
                                "is_missing": "0",
                                "missing_reason": "",
                                "source_response_sha256": "other-hash",
                            },
                        ]
                    )

            panel_specs = {
                "run_024_registered_p0": ("bound/registered_p0.csv", "P0_CORE_REPLAY_AND_FAST"),
                "run_024_registered_p1": ("bound/registered_p1.csv", "P1_AUGMENTED_BANK_CREDIT"),
                "run_024_next_day_p0": ("bound/next_p0.csv", "P0_CORE_REPLAY_AND_FAST"),
                "run_024_next_day_p1": ("bound/next_p1.csv", "P1_AUGMENTED_BANK_CREDIT"),
            }
            for label, (relative, panel_id) in panel_specs.items():
                panel(temporary / relative, panel_id)
                protocol["bound_inputs"][label]["path"] = relative
            protocol["bound_inputs"]["retained_ecb_dfr_api_response"]["path"] = "bound/retained.csv"
            for label in ("run_024_protocol", "run_024_audit", "source_registry"):
                relative = f"bound/{label}.txt"
                target = temporary / relative
                target.write_text(label, encoding="utf-8")
                protocol["bound_inputs"][label]["path"] = relative
            for spec in protocol["bound_inputs"].values():
                bound_path = temporary / spec["path"]
                payload = bound_path.read_bytes()
                spec["bytes"] = len(payload)
                spec["sha256"] = hashlib.sha256(payload).hexdigest()

            protocol["conditional_panel_rebuild"]["source_panels"] = {
                "registered_mir_bsi_clock": [
                    panel_specs["run_024_registered_p0"][0],
                    panel_specs["run_024_registered_p1"][0],
                ],
                "next_day_mir_bsi_clock": [
                    panel_specs["run_024_next_day_p0"][0],
                    panel_specs["run_024_next_day_p1"][0],
                ],
            }
            protocol_path = temporary / "research/protocol.yaml"
            protocol_path.parent.mkdir(parents=True)
            protocol_path.write_text(yaml.safe_dump(protocol, sort_keys=False), encoding="utf-8")

            source_payload = _html(_row("2002", "6 Dec.", "1.75"))
            source_path = temporary / "data/raw/effective.html"
            source_path.parent.mkdir(parents=True)
            source_path.write_bytes(source_payload)
            source_manifest = {
                "manifest_id": "run-025-dfr-effective-date-source-v1",
                "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
                "retrieval": {
                    "relative_path": "data/raw/effective.html",
                    "response_bytes": len(source_payload),
                    "sha256": hashlib.sha256(source_payload).hexdigest(),
                    "content_type": "text/html",
                    "final_url": protocol["canonical_source_contract"]["url"],
                    "registered_source_url": protocol["canonical_source_contract"]["url"],
                    "retrieved_at_utc": "2026-10-16T00:00:00+00:00",
                },
            }
            source_manifest_path = temporary / "data/manifests/source.yaml"
            source_manifest_path.parent.mkdir(parents=True)
            source_manifest_path.write_text(
                yaml.safe_dump(source_manifest, sort_keys=False), encoding="utf-8"
            )

            output = temporary / "data/processed/run025"
            audit_path = temporary / "reports/audit.json"
            audit = build_run025_dfr_effective_date_amendment(
                protocol_path, source_manifest_path, output, audit_path
            )
            self.assertTrue(audit.passed)
            self.assertEqual(audit.integrity["scenario_count"], 4)
            self.assertEqual(audit.integrity["panel_file_count"], 8)
            self.assertEqual(audit.integrity["duplicate_keys"], 0)
            self.assertEqual(audit.integrity["non_DFR_rows_changed"], 0)
            comparison = audit.scenario_comparisons["registered_mir_bsi"]["P0_CORE_REPLAY_AND_FAST"]
            self.assertEqual(comparison["effective_vs_next_day_timestamp_changes"], 1)
            self.assertEqual(comparison["effective_vs_next_day_observation_period_changes"], 0)
            self.assertEqual(comparison["effective_vs_next_day_value_or_missingness_changes"], 0)
            self.assertFalse(audit.reliability_engine_imported)
            self.assertFalse(audit.transmission_outcomes_accessed)
            self.assertFalse(audit.synthetic_empirical_observations_used)
            self.assertTrue((output / "dfr_effective_date_events.csv").is_file())
            self.assertEqual(json.loads(audit_path.read_text(encoding="utf-8"))["passed"], True)
            with self.assertRaisesRegex(run023.FullPanelBuildError, "overwrite"):
                build_run025_dfr_effective_date_amendment(
                    protocol_path,
                    source_manifest_path,
                    output,
                    temporary / "second-audit.json",
                )


if __name__ == "__main__":
    unittest.main()
