import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from scripts.audit_public_export import audit, is_high_entropy_candidate, shannon_entropy
from scripts.build_public_export import _safe_member
from scripts.run_public_tests import _prepare_import_path
from scripts.safe_tar import UnsafeTarError, extract_tar_safely
from scripts.verify_public_export import _last_json_object


class PublicExportTests(unittest.TestCase):
    def test_audit_script_can_be_invoked_directly(self) -> None:
        root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, "scripts/audit_public_export.py", "--help"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_entropy_scan_flags_mixed_random_candidate_without_retaining_value(self) -> None:
        candidate = b"".join((b"A9z_Q2mK7vN4pR8t", b"Y3wL6cD1fH5jS0xB"))
        self.assertGreaterEqual(shannon_entropy(candidate), 4.5)
        self.assertTrue(is_high_entropy_candidate(candidate))

    def test_entropy_scan_excludes_registered_hex_hash(self) -> None:
        self.assertFalse(is_high_entropy_candidate(b"ab12" * 16))

    def test_entropy_scan_excludes_paths_and_source_assignments(self) -> None:
        self.assertFalse(
            is_high_entropy_candidate(
                b"reports/methodology/run_007_execution_preflight_audit_2026-10-03"
            )
        )
        self.assertFalse(
            is_high_entropy_candidate(b"approved_design_sha256=APPROVED_DESIGN_SHA256")
        )

    def test_archive_member_rejects_traversal_and_links(self) -> None:
        import tarfile

        self.assertTrue(_safe_member(tarfile.TarInfo("docs/readme.md")))
        self.assertFalse(_safe_member(tarfile.TarInfo("../outside")))
        link = tarfile.TarInfo("linked")
        link.type = tarfile.SYMTYPE
        self.assertFalse(_safe_member(link))
        fifo = tarfile.TarInfo("pipe")
        fifo.type = tarfile.FIFOTYPE
        self.assertFalse(_safe_member(fifo))

    def test_safe_tar_extraction_is_fail_closed_and_preserves_executable_mode(self) -> None:
        import tarfile

        valid_bytes = BytesIO()
        content = b"#!/bin/sh\nexit 0\n"
        with tarfile.open(fileobj=valid_bytes, mode="w") as archive:
            directory = tarfile.TarInfo("bin")
            directory.type = tarfile.DIRTYPE
            directory.mode = 0o755
            archive.addfile(directory)
            executable = tarfile.TarInfo("bin/tool")
            executable.size = len(content)
            executable.mode = 0o755
            archive.addfile(executable, BytesIO(content))
        valid_bytes.seek(0)

        with tempfile.TemporaryDirectory() as directory_text:
            destination = Path(directory_text) / "valid"
            destination.mkdir()
            with tarfile.open(fileobj=valid_bytes, mode="r:") as archive:
                self.assertEqual(extract_tar_safely(archive, destination), 1)
            output = destination / "bin/tool"
            self.assertEqual(output.read_bytes(), content)
            self.assertEqual(output.stat().st_mode & 0o111, 0o111)

        hostile_bytes = BytesIO()
        with tarfile.open(fileobj=hostile_bytes, mode="w") as archive:
            safe = tarfile.TarInfo("inside.txt")
            safe.size = 4
            archive.addfile(safe, BytesIO(b"safe"))
            escape = tarfile.TarInfo("../escaped.txt")
            escape.size = 6
            archive.addfile(escape, BytesIO(b"escape"))
        hostile_bytes.seek(0)

        with tempfile.TemporaryDirectory() as directory_text:
            destination = Path(directory_text) / "hostile"
            destination.mkdir()
            with tarfile.open(fileobj=hostile_bytes, mode="r:") as archive:
                with self.assertRaisesRegex(UnsafeTarError, "Unsafe tar member"):
                    extract_tar_safely(archive, destination)
            self.assertEqual(list(destination.iterdir()), [])
            self.assertFalse((destination.parent / "escaped.txt").exists())

    def test_required_license_files_are_plain_text(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for relative in ("LICENSE", "LICENSE-DOCS.md", "NOTICE", "CITATION.cff"):
            with self.subTest(relative=relative):
                content = (root / relative).read_text(encoding="utf-8")
                self.assertTrue(content.strip())

    def test_readme_matches_current_license_and_release_boundary(self) -> None:
        root = Path(__file__).resolve().parents[1]
        readme = (root / "README.md").read_text(encoding="utf-8")
        boundary = (root / "docs/governance/public_private_boundary.md").read_text(encoding="utf-8")
        self.assertIn("Apache-2.0", readme)
        self.assertIn("rolffcoelho-bravo/shockbridge-state-reliability", readme)
        self.assertIn("parentless root commit", readme)
        self.assertIn("158 tests", readme)
        self.assertIn("Reviewer paths", readme)
        self.assertIn("Repository map", readme)
        self.assertNotIn("No GitHub remote exists", readme)
        self.assertNotIn("currently has no open-source license", readme)
        self.assertIn("Apache-2.0", boundary)
        self.assertIn("two independent repositories", boundary)
        self.assertNotIn("No open-source license is selected", boundary)

    def test_public_security_and_runner_contract_is_explicit(self) -> None:
        root = Path(__file__).resolve().parents[1]
        ci = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        codeql = (root / ".github/workflows/codeql.yml").read_text(encoding="utf-8")
        dependabot = (root / ".github/dependabot.yml").read_text(encoding="utf-8")
        security = (root / "SECURITY.md").read_text(encoding="utf-8")

        self.assertNotIn("ubuntu-latest", ci)
        self.assertIn("runs-on: ubuntu-24.04", ci)
        self.assertIn("runs-on: ubuntu-26.04", ci)
        self.assertIn("continue-on-error: true", ci)
        self.assertIn(
            "github.repository == 'rolffcoelho-bravo/shockbridge-state-reliability'", codeql
        )
        self.assertIn("security-events: write", codeql)
        self.assertIn("queries: security-extended", codeql)
        self.assertIn("package-ecosystem: pip", dependabot)
        self.assertIn("package-ecosystem: github-actions", dependabot)
        self.assertIn("private vulnerability reporting", security)

    def test_public_contribution_templates_are_structured(self) -> None:
        import yaml

        root = Path(__file__).resolve().parents[1]
        template_root = root / ".github/ISSUE_TEMPLATE"
        for name in ("bug_report.yml", "reproducibility.yml"):
            with self.subTest(name=name):
                payload = yaml.safe_load((template_root / name).read_text(encoding="utf-8"))
                self.assertIsInstance(payload, dict)
                self.assertTrue(payload["name"])
                self.assertTrue(payload["description"])
                self.assertGreaterEqual(len(payload["body"]), 3)
        config = yaml.safe_load((template_root / "config.yml").read_text(encoding="utf-8"))
        self.assertFalse(config["blank_issues_enabled"])
        self.assertEqual(len(config["contact_links"]), 2)
        self.assertIn(
            "Research-integrity requirements",
            (root / "CONTRIBUTING.md").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "Scientific effect",
            (root / ".github/pull_request_template.md").read_text(encoding="utf-8"),
        )

    def test_failed_export_receipts_are_private_only(self) -> None:
        from scripts.audit_public_export import PRIVATE_ONLY_PATHS
        from scripts.build_public_export import EXCLUDED_PATHS

        self.assertEqual(PRIVATE_ONLY_PATHS, EXCLUDED_PATHS)

    def test_public_runner_summary_is_parsed_after_unrelated_output(self) -> None:
        summary = _last_json_object('noise {not-json}\n{"tests_run": 152, "skipped": 7}\n')
        self.assertEqual(summary, {"tests_run": 152, "skipped": 7})

    def test_public_runner_prepares_repository_import_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            original = sys.path.copy()
            try:
                sys.path[:] = [entry for entry in sys.path if entry != str(root)]
                self.assertEqual(_prepare_import_path(root), root)
                self.assertEqual(sys.path[0], str(root))
            finally:
                sys.path[:] = original

    def test_clean_single_commit_export_passes_structural_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contents = {
                "CITATION.cff": "cff-version: 1.2.0\ntitle: Example\nmessage: Cite this.\n",
                "LICENSE": "Apache License Version 2.0\n",
                "LICENSE-DOCS.md": "CC BY 4.0\n",
                "NOTICE": "Copyright 2026 Example\n",
                "README.md": "# Public export\n",
                "data/raw/.gitkeep": "",
            }
            for relative, content in contents.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            manifest = {
                "files": {
                    relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
                    for relative in contents
                }
            }
            (root / "PUBLIC_EXPORT_MANIFEST.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "add", "--all"], cwd=root, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Test Release",
                    "-c",
                    "user.email=test@localhost",
                    "commit",
                    "-m",
                    "release",
                ],
                cwd=root,
                check=True,
                capture_output=True,
            )
            result = audit(root)
            self.assertEqual(result["status"], "PUBLIC_EXPORT_READY")
            self.assertEqual(result["commit_count"], 1)
            self.assertEqual(result["blocker_counts"]["high_entropy_candidate_findings"], 0)


if __name__ == "__main__":
    unittest.main()
