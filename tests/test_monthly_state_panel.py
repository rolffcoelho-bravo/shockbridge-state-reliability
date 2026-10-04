import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

import yaml

from shockbridge_state_risk.data.download import sha256_file
from shockbridge_state_risk.data.monthly_state_panel import (
    MONTHLY_FEATURES,
    build_monthly_state_panel,
    load_monthly_panel_config,
    monthly_cutoffs,
    parse_month,
)
from shockbridge_state_risk.data.state_panel import (
    FRANKFURT,
    ArchiveSnapshot,
    SourceRecord,
    audit_panel,
)


class MonthlyStatePanelTests(unittest.TestCase):
    def test_regular_calendar_includes_leap_month_and_boundaries(self) -> None:
        cutoffs = monthly_cutoffs(date(2024, 1, 1), date(2024, 3, 1))
        self.assertEqual(
            [item.event_id for item in cutoffs],
            ["month-2024-01", "month-2024-02", "month-2024-03"],
        )
        self.assertEqual(cutoffs[1].event_date, date(2024, 2, 29))
        self.assertEqual(cutoffs[1].state_cutoff_timestamp.hour, 23)
        start_cutoffs = monthly_cutoffs(
            date(2024, 1, 1),
            date(2024, 2, 1),
            "month_start_23_59_59_europe_berlin",
        )
        self.assertEqual(start_cutoffs[1].event_date, date(2024, 2, 1))

    def test_invalid_calendar_boundaries_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            parse_month("2024/01")
        with self.assertRaises(ValueError):
            monthly_cutoffs(date(2024, 1, 2), date(2024, 2, 1))
        with self.assertRaises(ValueError):
            monthly_cutoffs(date(2024, 3, 1), date(2024, 2, 1))
        with self.assertRaises(ValueError):
            monthly_cutoffs(date(2024, 1, 1), date(2024, 2, 1), "unsupported-rule")

    def test_config_verifies_registry_hash_and_feature_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "sources.yaml"
            registry.write_text("sources: {}\n", encoding="utf-8")
            config = root / "config.yaml"
            payload = {
                "source_registry": str(registry),
                "source_registry_sha256": sha256_file(registry),
                "start_month": "2002-01",
                "end_month": "2002-02",
                "features": list(MONTHLY_FEATURES),
                "cutoff_rule": "month_end_23_59_59_europe_berlin",
            }
            config.write_text(yaml.safe_dump(payload), encoding="utf-8")
            loaded = load_monthly_panel_config(config)
            self.assertEqual(loaded.start, date(2002, 1, 1))
            self.assertEqual(loaded.cutoff_rule, "month_end_23_59_59_europe_berlin")
            payload["features"] = ["hicp_yoy"]
            config.write_text(yaml.safe_dump(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_monthly_panel_config(config)

    @patch("shockbridge_state_risk.data.monthly_state_panel.load_daily_series")
    @patch("shockbridge_state_risk.data.monthly_state_panel.load_rtd_api_history")
    @patch("shockbridge_state_risk.data.monthly_state_panel.load_rtd_archive_snapshots")
    def test_builder_produces_complete_four_feature_month(
        self, load_archive, load_history, load_daily
    ) -> None:
        usable = datetime(2020, 1, 1, tzinfo=FRANKFURT)

        def snapshot(series: str, values: dict[date, float]) -> ArchiveSnapshot:
            return ArchiveSnapshot(
                first_usable_timestamp=usable,
                vintage_id="archive-2019-12",
                source_series_id=series,
                source_url="https://example.test/archive",
                source_artifact_sha256="a" * 64,
                values=values,
            )

        load_archive.return_value = {
            "hicp_yoy": (
                snapshot(
                    "hicp",
                    {date(2018, 12, 1): 100.0, date(2019, 12, 1): 102.0},
                ),
            ),
            "industrial_production_yoy": (
                snapshot(
                    "ip",
                    {date(2018, 12, 1): 100.0, date(2019, 12, 1): 101.0},
                ),
            ),
            "unemployment_rate": (snapshot("unemployment", {date(2019, 12, 1): 7.0}),),
        }
        load_history.return_value = ()
        load_daily.return_value = {date(2020, 1, 31): -0.5}
        records = {
            key: SourceRecord(Path(f"{key}.csv"), f"https://example.test/{key}", key)
            for key in (
                "rtd_archive",
                "rtd_hicp",
                "rtd_unemployment",
                "rtd_ip",
                "dfr",
            )
        }
        rows = build_monthly_state_panel(
            records,
            date(2020, 2, 1),
            date(2020, 2, 1),
            "month_start_23_59_59_europe_berlin",
        )
        panel_audit = audit_panel(rows)
        self.assertEqual(len(rows), 4)
        self.assertEqual(panel_audit.missing_by_feature, dict.fromkeys(MONTHLY_FEATURES, 0))
        self.assertEqual(panel_audit.point_in_time_violations, 0)


if __name__ == "__main__":
    unittest.main()
