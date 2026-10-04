import tempfile
import unittest
import zipfile
from datetime import date, datetime
from pathlib import Path

import yaml

from shockbridge_state_risk.data.download import sha256_file
from shockbridge_state_risk.data.state_panel import (
    FRANKFURT,
    ArchiveSnapshot,
    VintageValue,
    as_of_macro_values,
    audit_panel,
    build_candidate_state_panel,
    daily_level_feature,
    event_cutoff_for_date,
    load_factor_event_cutoffs,
    load_rtd_archive_snapshots,
    load_source_registry,
    macro_feature,
    write_panel_csv,
)


class StatePanelTests(unittest.TestCase):
    @staticmethod
    def _write_source(path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")

    def test_event_cutoff_respects_2022_timing_break(self) -> None:
        old = event_cutoff_for_date(date(2022, 6, 9))
        new = event_cutoff_for_date(date(2022, 7, 21))
        self.assertEqual((old.event_timestamp.hour, old.event_timestamp.minute), (13, 45))
        self.assertEqual((new.event_timestamp.hour, new.event_timestamp.minute), (14, 15))

    def test_factor_loader_reads_dates_without_parsing_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "factor.csv"
            path.write_text("date,target\n2020-01-01,not-a-number\n", encoding="utf-8")
            events = load_factor_event_cutoffs(path)
        self.assertEqual(events[0].event_date, date(2020, 1, 1))

    def test_archive_vintage_is_usable_only_after_month_end(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "monthly.zip"
            content = (
                " ,Industrial production,Unemployment,HICP\n"
                "Name:,STS.M.U2.Y.PROD.NS0020.4.000,"
                "STS.M.I2.S.UNEH.RTT000.4.000,ICP.M.U2.N.000000.4.INX\n"
                "Description:,,,\ncomments:,,,\n\n\n\n\n\n"
                "Jan-01,100,8,90\nJan-02,102,7,93\n"
            )
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("monthly_200202.csv", content)
            snapshots = load_rtd_archive_snapshots(path, "https://example.test/monthly.zip")
        snapshot = snapshots["hicp_yoy"][0]
        self.assertEqual(snapshot.first_usable_timestamp.month, 3)
        self.assertEqual(snapshot.first_usable_timestamp.day, 1)
        self.assertEqual(snapshot.values[date(2002, 1, 1)], 93.0)

    def test_as_of_join_rejects_equal_cutoff_vintage(self) -> None:
        cutoff = datetime(2020, 2, 1, tzinfo=FRANKFURT)
        archive = ArchiveSnapshot(
            cutoff.replace(year=2019),
            "archive",
            "old-series",
            "https://example.test/archive",
            "old-hash",
            {date(2019, 12, 1): 1.0},
        )
        equal = VintageValue(
            date(2019, 12, 1),
            2.0,
            cutoff,
            "equal",
            "new-series",
            "https://example.test/api",
            "new-hash",
        )
        selected = as_of_macro_values([archive], [equal], cutoff)
        self.assertEqual(selected[date(2019, 12, 1)].value, 1.0)

    def test_as_of_join_honours_delete_action(self) -> None:
        cutoff = datetime(2020, 2, 2, tzinfo=FRANKFURT)
        archive = ArchiveSnapshot(
            datetime(2019, 12, 1, tzinfo=FRANKFURT),
            "archive",
            "old-series",
            "https://example.test/archive",
            "old-hash",
            {date(2019, 12, 1): 1.0},
        )
        deletion = VintageValue(
            date(2019, 12, 1),
            None,
            datetime(2020, 2, 1, tzinfo=FRANKFURT),
            "delete",
            "new-series",
            "https://example.test/api",
            "new-hash",
        )
        selected = as_of_macro_values([archive], [deletion], cutoff)
        self.assertNotIn(date(2019, 12, 1), selected)

    def test_macro_yoy_uses_same_information_set(self) -> None:
        event = event_cutoff_for_date(date(2020, 2, 6))
        usable = datetime(2020, 2, 5, 15, 30, tzinfo=FRANKFURT)
        values = {
            date(2018, 12, 1): VintageValue(
                date(2018, 12, 1),
                100.0,
                usable,
                "v1",
                "series",
                "https://example.test/api",
                "hash",
            ),
            date(2019, 12, 1): VintageValue(
                date(2019, 12, 1),
                105.0,
                usable,
                "v1",
                "series",
                "https://example.test/api",
                "hash",
            ),
        }
        row = macro_feature(
            "hicp_yoy",
            "inflation",
            "percent",
            "yoy",
            event,
            values,
            True,
            "https://example.test/api",
            "hash",
            90,
        )
        self.assertAlmostEqual(row.value or 0.0, 5.0)
        self.assertFalse(row.missing)

    def test_daily_feature_never_uses_event_date(self) -> None:
        event = event_cutoff_for_date(date(2024, 6, 6))
        row = daily_level_feature(
            event,
            "deposit_facility_rate",
            "policy_and_curve",
            "percent",
            "FM.DFR",
            {date(2024, 6, 5): 4.0, date(2024, 6, 6): 3.75},
            "https://example.test",
            "hash",
            "effective_date_midnight",
        )
        self.assertEqual(row.observation_period, "2024-06-05")
        self.assertEqual(row.value, 4.0)

    def test_panel_audit_counts_missing_and_duplicate_keys(self) -> None:
        event = event_cutoff_for_date(date(2020, 2, 6))
        row = daily_level_feature(
            event,
            "rate",
            "policy",
            "percent",
            "series",
            {},
            "https://example.test",
            "hash",
            "effective_date_midnight",
        )
        audit = audit_panel([row, row])
        self.assertEqual(audit.missing_by_feature, {"rate": 2})
        self.assertEqual(audit.duplicate_event_feature_keys, 1)

    def test_miniature_registry_builds_complete_candidate_panel(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            event_path = root / "events.csv"
            self._write_source(event_path, "date,target\n2015-02-05,sealed\n")

            archive_path = root / "monthly.zip"
            archive_content = (
                " ,Industrial production,Unemployment,HICP\n"
                "Name:,STS.M.I7.Y.PROD.NS0020.4.000,"
                "STS.M.I7.S.UNEH.RTT000.4.000,ICP.M.U2.N.000000.4.INX\n"
                "Description:,,,\ncomments:,,,\n\n\n\n\n\n"
                "Jan-2014,100,8,100\nDec-2014,103,7.5,101\n"
            )
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("monthly_201412.csv", archive_content)

            api_header = "KEY,TIME_PERIOD,OBS_VALUE,ACTION,VALID_FROM\n"
            api_rows = {
                "rtd_hicp": (
                    "RTD.M.S0.N.P_C_OV.X,2014-01,100,Replace,"
                    "2015-02-04T15:30:00+01:00\n"
                    "RTD.M.S0.N.P_C_OV.X,2015-01,102,Replace,"
                    "2015-02-04T15:30:00+01:00\n"
                ),
                "rtd_unemployment": (
                    "RTD.M.S0.S.L_UNETO.F,2015-01,7.4,Replace,2015-02-04T15:30:00+01:00\n"
                ),
                "rtd_ip": (
                    "RTD.M.S0.Y.I_XCONS.X,2014-01,100,Replace,"
                    "2015-02-04T15:30:00+01:00\n"
                    "RTD.M.S0.Y.I_XCONS.X,2015-01,104,Replace,"
                    "2015-02-04T15:30:00+01:00\n"
                ),
            }
            paths = {"event_dates": event_path, "rtd_archive": archive_path}
            for key, content in api_rows.items():
                source_path = root / f"{key}.csv"
                self._write_source(source_path, api_header + content)
                paths[key] = source_path

            daily = {
                "dfr": "TIME_PERIOD,OBS_VALUE\n2015-02-04,0.05\n",
                "yc_2y": "TIME_PERIOD,OBS_VALUE\n2015-02-03,0.1\n",
                "yc_10y": "TIME_PERIOD,OBS_VALUE\n2015-02-03,1.2\n",
            }
            for key, content in daily.items():
                source_path = root / f"{key}.csv"
                self._write_source(source_path, content)
                paths[key] = source_path

            registry_path = root / "registry.yaml"
            registry_path.write_text(
                yaml.safe_dump(
                    {
                        "sources": {
                            key: {
                                "path": str(source_path),
                                "url": f"https://example.test/{key}",
                                "sha256": sha256_file(source_path),
                            }
                            for key, source_path in paths.items()
                        }
                    }
                ),
                encoding="utf-8",
            )
            rows = build_candidate_state_panel(load_source_registry(registry_path))
            output = root / "nested" / "panel.csv"
            write_panel_csv(rows, output)

            self.assertEqual(len(rows), 5)
            self.assertTrue(output.is_file())
            self.assertEqual(audit_panel(rows).point_in_time_violations, 0)
            self.assertEqual(
                {row.admission_status for row in rows},
                {"ADMITTED", "CONDITIONAL_CHALLENGER"},
            )


if __name__ == "__main__":
    unittest.main()
