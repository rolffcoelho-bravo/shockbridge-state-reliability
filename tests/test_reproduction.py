import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.reproduce_run010_clean import (
    AUDIT_PATH,
    CANONICAL_HASHES,
    CANONICAL_OUTPUTS,
    OUTPUT_HASHES,
    ROOT,
    SOURCE_COMMIT,
    ReproductionError,
    _atomic_json,
    _run,
    sha256_file,
    verify_files,
)


class ReproductionTests(unittest.TestCase):
    def test_hash_verification_and_atomic_immutable_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory_text:
            directory = Path(directory_text)
            artifact = directory / "nested/artifact.txt"
            artifact.parent.mkdir()
            artifact.write_text("evidence\n", encoding="utf-8")
            expected = {"nested/artifact.txt": sha256_file(artifact)}
            self.assertEqual(verify_files(directory, expected, "test"), expected)

            audit = directory / "audit.json"
            _atomic_json({"passed": True}, audit)
            self.assertEqual(json.loads(audit.read_text(encoding="utf-8")), {"passed": True})
            self.assertFalse(audit.with_suffix(".json.part").exists())
            with self.assertRaisesRegex(ReproductionError, "immutable"):
                _atomic_json({"passed": True}, audit)

            artifact.write_text("changed\n", encoding="utf-8")
            with self.assertRaisesRegex(ReproductionError, "Changed"):
                verify_files(directory, expected, "test")
            artifact.unlink()
            with self.assertRaisesRegex(ReproductionError, "Missing"):
                verify_files(directory, expected, "test")

    @unittest.skipUnless(
        (ROOT / CANONICAL_OUTPUTS["comparison.csv"]).is_file(),
        "requires local hash-registered evidence",
    )
    def test_frozen_constants_match_registered_run010_manifest_and_protocol(self) -> None:
        manifest = yaml.safe_load(
            (
                ROOT / "reports/methodology/state_vintage_robustness_run010_v1.manifest.yaml"
            ).read_text(encoding="utf-8")
        )
        protocol = yaml.safe_load(
            (
                ROOT / "research/methodology/run_011_reproduction_and_positioning_protocol_v1.yaml"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(SOURCE_COMMIT, protocol["frozen_reproduction_target"]["source_git_commit"])
        output_records = manifest["outputs"]
        for filename, expected_hash in OUTPUT_HASHES.items():
            key = "audit" if filename == "audit.json" else filename.removesuffix(".csv")
            self.assertEqual(expected_hash, output_records[key]["sha256"])
            canonical = ROOT / CANONICAL_OUTPUTS[filename]
            self.assertEqual(expected_hash, sha256_file(canonical))
        self.assertEqual(verify_files(ROOT, CANONICAL_HASHES, "canonical output"), CANONICAL_HASHES)
        self.assertEqual(
            AUDIT_PATH, ROOT / "reports/methodology/run_011_clean_reproduction.audit.json"
        )

    def test_failed_subprocess_preserves_diagnostics(self) -> None:
        with self.assertRaisesRegex(ReproductionError, "diagnostic-marker"):
            _run(
                [
                    sys.executable,
                    "-c",
                    "import sys; print('diagnostic-marker', file=sys.stderr); sys.exit(7)",
                ],
                ROOT,
            )


if __name__ == "__main__":
    unittest.main()
