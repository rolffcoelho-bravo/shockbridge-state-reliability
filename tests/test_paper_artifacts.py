import csv
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from scripts.build_run011_paper_artifacts import (
    AUDIT_PATH,
    EPISODE_PATH,
    INPUT_HASHES,
    PaperArtifactError,
    build,
)


class PaperArtifactTests(unittest.TestCase):
    @unittest.skipUnless(EPISODE_PATH.is_file(), "requires local hash-registered evidence")
    def test_bundle_is_deterministic_valid_and_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as directory_text:
            parent = Path(directory_text)
            first = parent / "first"
            second = parent / "second"
            first_metadata = build(first)
            second_metadata = build(second)

            self.assertEqual(first_metadata, second_metadata)
            expected_files = {
                "run010_table_geometry_v1.csv",
                "run010_table_value_differences_v1.csv",
                "run010_table_bootstrap_primary_v1.csv",
                "run010_figure_geometry_v1.svg",
                "run010_figure_episodes_v1.svg",
                "run010_paper_artifacts_v1.json",
            }
            self.assertEqual({path.name for path in first.iterdir()}, expected_files)
            for filename in expected_files:
                self.assertEqual((first / filename).read_bytes(), (second / filename).read_bytes())

            ET.parse(first / "run010_figure_geometry_v1.svg")
            ET.parse(first / "run010_figure_episodes_v1.svg")
            with (first / "run010_table_geometry_v1.csv").open(
                newline="", encoding="utf-8"
            ) as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 6)
            with (first / "run010_table_value_differences_v1.csv").open(
                newline="", encoding="utf-8"
            ) as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 3)
            with (first / "run010_table_bootstrap_primary_v1.csv").open(
                newline="", encoding="utf-8"
            ) as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 9)

            metadata = json.loads(
                (first / "run010_paper_artifacts_v1.json").read_text(encoding="utf-8")
            )
            self.assertFalse(metadata["boundaries"]["transmission_outcomes_accessed"])
            self.assertTrue(
                all(
                    Path(record["path"]).name == record["path"]
                    for record in metadata["outputs"].values()
                )
            )
            with self.assertRaisesRegex(PaperArtifactError, "immutable"):
                build(first)

    def test_changed_registered_input_is_rejected_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory_text:
            output = Path(directory_text) / "bundle"
            with patch.dict(INPUT_HASHES, {AUDIT_PATH: "0" * 64}):
                with self.assertRaisesRegex(PaperArtifactError, "missing or changed"):
                    build(output)
            self.assertFalse(output.exists())

    @unittest.skipUnless(EPISODE_PATH.is_file(), "requires local hash-registered evidence")
    def test_failed_build_removes_staging_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory_text:
            output = Path(directory_text) / "bundle"
            with patch(
                "scripts.build_run011_paper_artifacts._episode_svg",
                side_effect=PaperArtifactError("injected failure"),
            ):
                with self.assertRaisesRegex(PaperArtifactError, "injected failure"):
                    build(output)
            self.assertFalse(output.exists())
            self.assertFalse(output.with_name("bundle.part").exists())


if __name__ == "__main__":
    unittest.main()
