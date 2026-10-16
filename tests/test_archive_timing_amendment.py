from __future__ import annotations

import copy
import csv
import hashlib
import json
import tempfile
import unittest
from datetime import date, datetime, time
from pathlib import Path

import yaml

from shockbridge_state_risk.data import full_panel_build as run023
from shockbridge_state_risk.data.archive_timing_amendment import (
    _build_variant,
    _calendar_text,
    _compare_rows,
    _coverage_delta,
    _fully_observed,
    _load_protocol,
    _usable_dates,
    build_run024_archive_timing_amendment,
    parse_archive_identifier_dates,
)
from shockbridge_state_risk.data.full_panel_build import (
    FRANKFURT,
    FullPanelBuildError,
    VersionedValue,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = (
    ROOT / "research/methodology/run_024_archive_identifier_and_timing_sensitivity_protocol_v1.yaml"
)


def _protocol(*, mir_support: int = 1, bsi_support: int = 1) -> dict[str, object]:
    payload = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
    payload = copy.deepcopy(payload)
    payload["release_mapping_contract"]["minimum_cross_validation_support"] = {
        "MIR": mir_support,
        "BSI": bsi_support,
    }
    return payload


def _entry(release_date: str, visible: str, href: str, title: str) -> str:
    return (
        f'<dt isoDate="{release_date}"><div class="date">{visible}</div></dt>'
        f'<dd><div class="title"><a href="{href}">{title}</a></div></dd>'
    )


def _version(period: str, value: float) -> VersionedValue:
    return VersionedValue(
        period,
        value,
        datetime(2026, 1, 1, tzinfo=FRANKFURT),
        "Replace",
    )


class ArchiveTimingAmendmentTests(unittest.TestCase):
    def test_mir_parser_adds_only_validated_legacy_identifiers(self) -> None:
        payload = (
            _entry(
                "2004-07-13",
                "13 July 2004",
                "/press/pdf/mfi/mir0405.pdf?hash",
                "MFI interest rate statistics: May 2004",
            )
            + _entry(
                "2004-05-14",
                "14 May 2004",
                "/press/pdf/mfi/mir0403.pdf",
                "MFI interest rate statistics",
            )
            + _entry(
                "2025-02-04",
                "4 February 2025",
                "/press/stats/mfi/html/ecb.mir2502~abc.en.html",
                "Euro area bank interest rate statistics: December 2024",
            )
            + _entry(
                "2025-03-05",
                "5 March 2025",
                "/press/pdf/mfi/ecb.mir2503.pdf",
                "MFI interest rate statistics",
            )
        ).encode()
        mappings, sources, audit = parse_archive_identifier_dates(payload, "MIR", _protocol())
        self.assertEqual(set(mappings), {"2004-03", "2004-05", "2024-12"})
        self.assertEqual(sources["2004-03"], "legacy_pdf_identifier")
        self.assertEqual(sources["2004-05"], "explicit_title")
        self.assertEqual(audit.explicit_identifier_cross_validations, 1)
        self.assertEqual(audit.eligible_generic_identifier_additions, 1)
        self.assertEqual(audit.explicit_identifier_disagreements, 0)

    def test_archive_parser_ignores_page_chrome_and_requires_entry_local_title(self) -> None:
        chrome = (
            '<nav><div class="title">Research</div></nav>'
            + _entry(
                "2004-05-14",
                "14 May 2004",
                "/press/pdf/mfi/mir0403.pdf",
                "MFI interest rate statistics: March 2004",
            )
            + '<footer><div class="title">Are you happy with this page?</div></footer>'
        ).encode()
        mappings, _, _ = parse_archive_identifier_dates(chrome, "MIR", _protocol())
        self.assertEqual(mappings, {"2004-03": date(2004, 5, 14)})

        missing_title = (
            b'<dt isoDate="2004-05-14"><div class="date">14 May 2004</div></dt>'
            b'<dt isoDate="2004-06-16"><div class="date">16 June 2004</div></dt>'
        )
        with self.assertRaisesRegex(FullPanelBuildError, "lacks its own title"):
            parse_archive_identifier_dates(missing_title, "MIR", _protocol())

    def test_bsi_parser_resolves_prior_year_and_rejects_annex_semantics(self) -> None:
        payload = (
            _entry(
                "2017-05-29",
                "29 May 2017",
                "/press/pdf/md/ecb.md1704.pdf",
                "Monetary developments in the euro area: April 2017",
            )
            + _entry(
                "2003-01-28",
                "28 January 2003",
                "/press/pdf/md/md0212.pdf",
                "Monetary developments in the euro area",
            )
            + _entry(
                "2026-02-26",
                "26 February 2026",
                "/press/pdf/md/ecb.md2601_annex.en.pdf",
                "Tables",
            )
            + _entry(
                "2002-10-28",
                "28 October 2002",
                "/press/pdf/md/md0210.pdf",
                "Monetary developments in the euro area",
            )
        ).encode()
        mappings, sources, audit = parse_archive_identifier_dates(payload, "BSI", _protocol())
        self.assertEqual(mappings["2002-12"], date(2003, 1, 28))
        self.assertEqual(sources["2002-12"], "legacy_pdf_identifier")
        self.assertNotIn("2026-01", mappings)
        self.assertNotIn("2002-10", mappings)
        self.assertEqual(audit.explicit_identifier_cross_validations, 1)
        self.assertEqual(audit.identifier_candidates_rejected_by_temporal_validation, 1)

    def test_archive_parser_fails_closed_on_semantic_and_date_conflicts(self) -> None:
        mismatch = _entry(
            "2004-07-13",
            "13 July 2004",
            "/press/pdf/mfi/mir0405.pdf",
            "MFI interest rate statistics: April 2004",
        ).encode()
        with self.assertRaisesRegex(FullPanelBuildError, "disagrees"):
            parse_archive_identifier_dates(mismatch, "MIR", _protocol())

        visible_mismatch = _entry(
            "2004-07-13",
            "12 July 2004",
            "/press/pdf/mfi/mir0405.pdf",
            "MFI interest rate statistics: May 2004",
        ).encode()
        with self.assertRaisesRegex(FullPanelBuildError, "visible release date"):
            parse_archive_identifier_dates(visible_mismatch, "MIR", _protocol())

        conflicting = (
            _entry(
                "2004-07-13",
                "13 July 2004",
                "/press/pdf/mfi/mir0405.pdf",
                "MFI interest rate statistics: May 2004",
            )
            + _entry(
                "2004-07-14",
                "14 July 2004",
                "/press/stats/mfi/other.html",
                "MFI interest rate statistics: May 2004",
            )
        ).encode()
        with self.assertRaisesRegex(FullPanelBuildError, "conflicting"):
            parse_archive_identifier_dates(conflicting, "MIR", _protocol())

        with self.assertRaisesRegex(FullPanelBuildError, "MIR or BSI"):
            parse_archive_identifier_dates(b"", "OTHER", _protocol())
        with self.assertRaisesRegex(FullPanelBuildError, "not UTF-8"):
            parse_archive_identifier_dates(b"\xff", "MIR", _protocol())

    def test_timing_variants_are_calendar_explicit_and_dst_safe(self) -> None:
        releases = {"2025-02": date(2025, 4, 1), "2025-09": date(2025, 10, 26)}
        registered = _usable_dates(releases, "registered_clock")
        next_day = _usable_dates(releases, "next_day_clock")
        self.assertEqual(registered["2025-02"].timetz().replace(tzinfo=None), time(10, 0, 1))
        self.assertEqual(next_day["2025-02"].date(), date(2025, 4, 2))
        self.assertEqual(next_day["2025-09"].date(), date(2025, 10, 27))
        self.assertEqual(next_day["2025-09"].utcoffset().total_seconds(), 3600)
        with self.assertRaisesRegex(FullPanelBuildError, "unknown"):
            _usable_dates(releases, "same_day_midnight")

    def test_panel_variants_and_comparisons_separate_timestamp_from_selection(self) -> None:
        manifest = {
            "calendar": {"panel_start": "2004-04", "panel_end": "2004-07"},
            "series": [
                {"series_id": "MIR_NFC_COST_OF_BORROWING", "sign": 1},
                {"series_id": "BSI_NFC_ADJUSTED_LOANS", "sign": 1},
                {"series_id": "BSI_MONETARY_AGGREGATE_M3", "sign": 1},
            ],
            "panels": [
                {
                    "panel_id": "P0_CORE_REPLAY_AND_FAST",
                    "series_ids": ["MIR_NFC_COST_OF_BORROWING"],
                },
                {
                    "panel_id": "P1_AUGMENTED_BANK_CREDIT",
                    "series_ids": [
                        "MIR_NFC_COST_OF_BORROWING",
                        "BSI_NFC_ADJUSTED_LOANS",
                        "BSI_MONETARY_AGGREGATE_M3",
                    ],
                },
            ],
        }
        versions = {
            "MIR_NFC_COST_OF_BORROWING": [_version("2004-03", 4.0)],
            "BSI_NFC_ADJUSTED_LOANS": [_version("2004-04", 100.0)],
            "BSI_MONETARY_AGGREGATE_M3": [_version("2004-04", 200.0)],
        }
        hashes = {series_id: "0" * 64 for series_id in versions}
        registered_dates = {
            "MIR": {"2004-03": datetime(2004, 5, 14, 10, 0, 1, tzinfo=FRANKFURT)},
            "BSI": {"2004-04": datetime(2004, 6, 1, 10, 0, 1, tzinfo=FRANKFURT)},
        }
        next_day_dates = {
            "MIR": {"2004-03": datetime(2004, 5, 15, 0, 0, tzinfo=FRANKFURT)},
            "BSI": {"2004-04": datetime(2004, 6, 2, 0, 0, tzinfo=FRANKFURT)},
        }
        registered = _build_variant(
            manifest, versions, hashes, registered_dates, "registered_clock"
        )
        next_day = _build_variant(manifest, versions, hashes, next_day_dates, "next_day_clock")
        comparison = _compare_rows(registered.rows, next_day.rows)
        self.assertGreater(comparison["changed_panel_key_count"], 0)
        self.assertEqual(comparison["missingness_status_change_count"], 2)
        self.assertEqual(comparison["exact_changed_origin_months"], ["2004-06"])
        self.assertEqual(
            next_day.audit.fully_observed_origins["P1_AUGMENTED_BANK_CREDIT"],
            registered.audit.fully_observed_origins["P1_AUGMENTED_BANK_CREDIT"] - 1,
        )
        deltas = _coverage_delta(registered.rows, next_day.rows)
        self.assertEqual(deltas["P1_AUGMENTED_BANK_CREDIT:BSI_NFC_ADJUSTED_LOANS"], -1)
        self.assertEqual(_fully_observed(registered.rows["P0_CORE_REPLAY_AND_FAST"]), 2)

        calendar_text = _calendar_text(
            {"MIR": {"2004-03": date(2004, 5, 14)}, "BSI": {}},
            {"MIR": {"2004-03": "legacy_pdf_identifier"}, "BSI": {}},
            "registered_clock",
        )
        self.assertIn("legacy_pdf_identifier", calendar_text)
        self.assertIn("2004-05-14T10:00:01", calendar_text)

    def test_protocol_loader_verifies_every_bound_byte(self) -> None:
        declared = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
        self.assertEqual(len(declared["bound_inputs"]), 9)
        bound_paths = [ROOT / spec["path"] for spec in declared["bound_inputs"].values()]
        if all(path.is_file() for path in bound_paths):
            root, protocol = _load_protocol(PROTOCOL)
            self.assertEqual(root, ROOT)
            self.assertEqual(len(protocol["bound_inputs"]), 9)
        else:
            # Public source-only clones retain exact declarations but
            # intentionally omit protected response and processed-panel bytes.
            self.assertTrue(any(not path.is_file() for path in bound_paths))
            for spec in declared["bound_inputs"].values():
                self.assertGreater(spec["bytes"], 0)
                self.assertRegex(spec["sha256"], r"^[0-9a-f]{64}$")

        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            mutated = Path(directory) / "protocol.yaml"
            payload = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
            first = payload["bound_inputs"]["run_023_protocol"]
            first["sha256"] = hashlib.sha256(b"changed").hexdigest()
            mutated.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(FullPanelBuildError, "hash mismatch"):
                _load_protocol(mutated)

    def test_complete_fixture_build_is_immutable_and_outcome_blind(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            fixture_root = Path(directory)
            (fixture_root / "pyproject.toml").write_text("[project]\nname='fixture'\n")
            manifest = yaml.safe_load(
                (ROOT / "research/data/run_021_full_panel_manifest_v1.yaml").read_text()
            )
            manifest_path = fixture_root / "research/data/run_021_full_panel_manifest_v1.yaml"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))

            run023_protocol = {
                "status": "APPROVED_AND_FROZEN_BEFORE_NETWORK_RETRIEVAL",
                "scientific_boundary": {
                    "real_official_data_only": True,
                    "zero_cost_sources_only": True,
                    "synthetic_empirical_observations_allowed": False,
                    "transmission_outcomes_access_allowed": False,
                    "reliability_engine_import_allowed": False,
                    "empirical_state_estimation_allowed": False,
                    "scenario_generation_allowed": False,
                },
                "bound_inputs": [],
                "retrieval_contract": {
                    "source_registry": "research/data/run_021_full_panel_manifest_v1.yaml",
                    "maximum_response_bytes_per_series": 50000000,
                },
            }
            run023_protocol_path = (
                fixture_root
                / "research/methodology"
                / "run_023_full_history_retrieval_and_panel_build_protocol_v1.yaml"
            )
            run023_protocol_path.parent.mkdir(parents=True)
            run023_protocol_path.write_text(yaml.safe_dump(run023_protocol, sort_keys=False))

            raw_root = fixture_root / "data/raw/run023_full_panel_v1"
            series_root = raw_root / "series"
            evidence_root = raw_root / "release_evidence"
            series_root.mkdir(parents=True)
            evidence_root.mkdir(parents=True)
            records: list[dict[str, object]] = []
            versions: dict[str, list[VersionedValue]] = {}
            source_hashes: dict[str, str] = {}
            for spec in manifest["series"]:
                path = series_root / spec["filename"]
                period = "2003-01-02" if spec["frequency"] in {"D", "B"} else "2003-01"
                valid_from = (
                    "2003-01-03T10:00:00+01:00"
                    if spec["timing_class"] == "A_REPLAY_ELIGIBLE"
                    else ""
                )
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
                    writer.writerow(
                        [
                            spec["full_series_key"],
                            spec["frequency"],
                            period,
                            "100",
                            spec["unit"],
                            "Replace",
                            valid_from,
                            "",
                        ]
                    )
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                source_hashes[spec["series_id"]] = digest
                versions[spec["series_id"]] = run023.load_versioned_values(spec, path)
                records.append(
                    {
                        "item_id": spec["series_id"],
                        "relative_path": path.relative_to(fixture_root).as_posix(),
                        "response_bytes": path.stat().st_size,
                        "sha256": digest,
                    }
                )

            mir_payload = _entry(
                "2003-03-03",
                "3 March 2003",
                "/press/pdf/mfi/mir0301.pdf",
                "MFI interest rate statistics: January 2003",
            ) + _entry(
                "2003-02-13",
                "13 February 2003",
                "/press/pdf/mfi/mir0212.pdf",
                "MFI interest rate statistics",
            )
            bsi_payload = _entry(
                "2003-02-27",
                "27 February 2003",
                "/press/pdf/md/md0301.pdf",
                "Monetary developments in the euro area: January 2003",
            ) + _entry(
                "2003-01-28",
                "28 January 2003",
                "/press/pdf/md/md0212.pdf",
                "Monetary developments in the euro area",
            )
            evidence = {
                "mir_archive": mir_payload,
                "bsi_historical_release_index_run_023_addition": bsi_payload,
                "rtd_information": "official fixture",
                "fx_methodology": "official fixture",
                "mir_calendar": "official fixture",
                "bsi_calendar": "official fixture",
                "bsi_information": "official fixture",
            }
            for item_id, body in evidence.items():
                path = evidence_root / f"{item_id}.html"
                path.write_text(body, encoding="utf-8")
                records.append(
                    {
                        "item_id": item_id,
                        "relative_path": path.relative_to(fixture_root).as_posix(),
                        "response_bytes": path.stat().st_size,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                )
            retrieval_path = fixture_root / "data/manifests/run_023_full_history_sources_v1.yaml"
            retrieval_path.parent.mkdir(parents=True)
            retrieval_path.write_text(yaml.safe_dump({"responses": records}, sort_keys=False))

            explicit_release_dates = {
                "MIR": {"2003-01": datetime(2003, 3, 3, 10, 0, 1, tzinfo=FRANKFURT)},
                "BSI": {"2003-01": datetime(2003, 2, 27, 10, 0, 1, tzinfo=FRANKFURT)},
            }
            baseline = _build_variant(
                manifest,
                versions,
                source_hashes,
                explicit_release_dates,
                "registered_clock",
            )
            baseline_root = fixture_root / "data/processed/run023_full_panel_v1"
            baseline_root.mkdir(parents=True)
            baseline_paths = {
                "P0_CORE_REPLAY_AND_FAST": baseline_root / "p0_core_replay_and_fast.csv",
                "P1_AUGMENTED_BANK_CREDIT": baseline_root / "p1_augmented_bank_credit.csv",
            }
            for panel_id, path in baseline_paths.items():
                run023._write_panel(path, baseline.rows[panel_id])
            calendar_path = baseline_root / "verified_release_calendar.csv"
            calendar_path.write_text("release_kind,reference_period,usable_timestamp\n")
            build_audit_path = fixture_root / "reports/methodology/run_023.audit.json"
            build_audit_path.parent.mkdir(parents=True)
            build_audit_path.write_text(json.dumps({"passed": True}) + "\n")

            run024_protocol = _protocol(mir_support=1, bsi_support=1)
            bound_paths = {
                "run_023_protocol": run023_protocol_path,
                "source_registry": manifest_path,
                "retrieval_manifest": retrieval_path,
                "mir_archive": evidence_root / "mir_archive.html",
                "bsi_archive": (
                    evidence_root / "bsi_historical_release_index_run_023_addition.html"
                ),
                "run_023_p0": baseline_paths["P0_CORE_REPLAY_AND_FAST"],
                "run_023_p1": baseline_paths["P1_AUGMENTED_BANK_CREDIT"],
                "run_023_release_calendar": calendar_path,
                "run_023_build_audit": build_audit_path,
            }
            run024_protocol["bound_inputs"] = {
                label: {
                    "path": path.relative_to(fixture_root).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                for label, path in bound_paths.items()
            }
            run024_protocol["rebuild_contract"]["raw_directory"] = raw_root.relative_to(
                fixture_root
            ).as_posix()
            run024_protocol_path = (
                fixture_root / "research/methodology/run_024_fixture_protocol.yaml"
            )
            run024_protocol_path.write_text(
                yaml.safe_dump(run024_protocol, sort_keys=False), encoding="utf-8"
            )
            output = fixture_root / "data/processed/run024"
            audit_path = fixture_root / "reports/methodology/run024.audit.json"
            audit = build_run024_archive_timing_amendment(run024_protocol_path, output, audit_path)
            self.assertTrue(audit.passed)
            self.assertEqual(audit.preserved_response_count_verified, 17)
            self.assertTrue((output / "registered_clock/p1_augmented_bank_credit.csv").is_file())
            self.assertTrue((output / "next_day_clock/release_calendar.csv").is_file())
            self.assertFalse(audit.state_estimation_performed)
            self.assertFalse(audit.transmission_outcomes_accessed)
            with self.assertRaisesRegex(FullPanelBuildError, "overwrite"):
                build_run024_archive_timing_amendment(
                    run024_protocol_path, output, fixture_root / "second.audit.json"
                )


if __name__ == "__main__":
    unittest.main()
