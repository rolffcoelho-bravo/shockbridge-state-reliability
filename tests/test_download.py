import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from shockbridge_state_risk.data.download import DownloadError, download_https, sha256_file


class _Response:
    def __init__(self) -> None:
        self.chunks = iter((b"abc", b"123", b""))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def geturl(self) -> str:
        return "https://example.test/final.xlsx"

    def read(self, chunk_size: int) -> bytes:
        self.chunk_size = chunk_size
        return next(self.chunks)


class DownloadTests(unittest.TestCase):
    def test_sha256_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact"
            path.write_bytes(b"abc123")
            self.assertEqual(sha256_file(path), hashlib.sha256(b"abc123").hexdigest())

    def test_non_https_is_rejected(self) -> None:
        with self.assertRaises(DownloadError):
            download_https("http://example.test/file", Path("unused"))

    @patch("shockbridge_state_risk.data.download.urlopen")
    def test_atomic_download_and_manifest(self, urlopen: Mock) -> None:
        urlopen.return_value = _Response()
        expected = hashlib.sha256(b"abc123").hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "artifact.xlsx"
            manifest = download_https("https://example.test/source.xlsx", destination, expected)
            self.assertEqual(destination.read_bytes(), b"abc123")
        self.assertEqual(manifest.sha256, expected)
        self.assertEqual(manifest.bytes, 6)

    @patch("shockbridge_state_risk.data.download.urlopen")
    def test_hash_mismatch_removes_temporary_file(self, urlopen: Mock) -> None:
        urlopen.return_value = _Response()
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "artifact.xlsx"
            with self.assertRaises(DownloadError):
                download_https("https://example.test/source.xlsx", destination, "0" * 64)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
