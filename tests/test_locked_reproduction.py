import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.reproduce_run010_clean import ReproductionError, sha256_file
from scripts.reproduce_run010_locked import (
    EXPECTED_VERSIONS,
    LOCK_PATHS,
    ROOT,
    _hydrate_registered_artifacts,
    _lock_hashes,
)


class LockedReproductionTests(unittest.TestCase):
    def test_script_can_be_invoked_directly(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts/reproduce_run010_locked.py"), "--self-check"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.stdout.strip(), "run012-locked-reproducer-import-ok")

    def test_locks_are_present_portable_and_complete(self) -> None:
        hashes = _lock_hashes(ROOT)
        self.assertEqual(set(hashes), {"build", "runtime", "dev"})
        for path in LOCK_PATHS.values():
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("-e ", content)
            self.assertNotIn("/Users/", content)
            self.assertNotIn("/home/", content)

        combined = "\n".join(path.read_text(encoding="utf-8") for path in LOCK_PATHS.values())
        for name, version in EXPECTED_VERSIONS.items():
            self.assertIn(f"{name}=={version}", combined)

    def test_inventory_hydration_is_hash_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory_text:
            source = Path(directory_text) / "source"
            checkout = Path(directory_text) / "checkout"
            artifact = source / "reports/evidence.txt"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("evidence\n", encoding="utf-8")
            inventory = source / "data/manifests/local_artifact_inventory_2026-10-02.yaml"
            inventory.parent.mkdir(parents=True)
            payload = {
                "artifacts": [
                    {
                        "path": "reports/evidence.txt",
                        "bytes": artifact.stat().st_size,
                        "sha256": sha256_file(artifact),
                    }
                ]
            }
            inventory.write_text(yaml.safe_dump(payload), encoding="utf-8")
            self.assertEqual(_hydrate_registered_artifacts(source, checkout), 1)
            self.assertEqual(
                (checkout / "reports/evidence.txt").read_bytes(), artifact.read_bytes()
            )

            artifact.write_text("changed\n", encoding="utf-8")
            with self.assertRaisesRegex(ReproductionError, "Changed inventory"):
                _hydrate_registered_artifacts(source, checkout)


if __name__ == "__main__":
    unittest.main()
