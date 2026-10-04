import tempfile
import unittest
from pathlib import Path

import yaml

from shockbridge_state_risk.data.download import sha256_file
from shockbridge_state_risk.data.inventory import InventoryError, verify_inventory


class InventoryTests(unittest.TestCase):
    def test_verified_inventory_and_corruption_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "data" / "value.bin"
            artifact.parent.mkdir()
            artifact.write_bytes(b"research-evidence")
            manifest = root / "inventory.yaml"
            payload = {
                "inventory_id": "test",
                "canonical_root": str(root),
                "artifacts": [
                    {
                        "path": "data/value.bin",
                        "bytes": artifact.stat().st_size,
                        "sha256": sha256_file(artifact),
                    }
                ],
            }
            manifest.write_text(yaml.safe_dump(payload), encoding="utf-8")
            self.assertTrue(verify_inventory(manifest).passed)
            artifact.write_bytes(b"corrupt")
            audit = verify_inventory(manifest)
            self.assertFalse(audit.passed)
            self.assertEqual(audit.verified_artifacts, 0)

    def test_path_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "inventory.yaml"
            manifest.write_text(
                yaml.safe_dump(
                    {
                        "inventory_id": "escape",
                        "canonical_root": str(root),
                        "artifacts": [{"path": "../outside", "bytes": 1, "sha256": "0" * 64}],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(InventoryError):
                verify_inventory(manifest)

    def test_relative_root_is_resolved_from_inventory_location(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_directory = root / "data/manifests"
            manifest_directory.mkdir(parents=True)
            artifact = root / "artifact.txt"
            artifact.write_text("portable\n", encoding="utf-8")
            manifest = manifest_directory / "inventory.yaml"
            manifest.write_text(
                yaml.safe_dump(
                    {
                        "inventory_id": "portable",
                        "canonical_root": "../..",
                        "artifacts": [
                            {
                                "path": "artifact.txt",
                                "bytes": artifact.stat().st_size,
                                "sha256": sha256_file(artifact),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            audit = verify_inventory(manifest)
            self.assertTrue(audit.passed)
            self.assertEqual(Path(audit.canonical_root), root.resolve())


if __name__ == "__main__":
    unittest.main()
