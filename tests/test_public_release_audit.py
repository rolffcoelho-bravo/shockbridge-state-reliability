import tempfile
import unittest
from pathlib import Path

from scripts.audit_public_release import (
    PRIVACY_PATTERNS,
    SECRET_PATTERNS,
    PublicReleaseAuditError,
    _atomic_json,
    _is_allowed_data_placeholder,
    _pattern_hits,
    audit,
)


class PublicReleaseAuditTests(unittest.TestCase):
    def test_sensitive_patterns_are_detected_without_exposing_values(self) -> None:
        self.assertEqual(_pattern_hits(b"clean public text", SECRET_PATTERNS), [])
        self.assertEqual(
            _pattern_hits(b"-----BEGIN " + b"PRIVATE KEY-----", SECRET_PATTERNS),
            ["private_key"],
        )
        self.assertEqual(
            _pattern_hits(b"path=/" + b"Users/example/research", PRIVACY_PATTERNS),
            ["macos_home"],
        )
        self.assertEqual(_pattern_hits(b"binary\x00/" + b"Users/example", PRIVACY_PATTERNS), [])

    def test_data_boundary_allows_only_placeholders(self) -> None:
        self.assertTrue(_is_allowed_data_placeholder("data/raw/.gitkeep"))
        self.assertFalse(_is_allowed_data_placeholder("data/raw/source.csv"))
        self.assertFalse(_is_allowed_data_placeholder("data/processed/result.csv"))
        self.assertTrue(_is_allowed_data_placeholder("reports/paper/table.csv"))

    def test_audit_writer_is_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.json"
            _atomic_json({"passed": True}, path)
            self.assertTrue(path.is_file())
            with self.assertRaisesRegex(PublicReleaseAuditError, "immutable"):
                _atomic_json({"passed": True}, path)

    def test_author_identity_is_disclosed_but_not_a_publication_blocker(self) -> None:
        payload = audit()
        self.assertIn("public_author_identity_records", payload["disclosure_counts"])
        self.assertNotIn("public_author_identity_records", payload["blocker_counts"])


if __name__ == "__main__":
    unittest.main()
