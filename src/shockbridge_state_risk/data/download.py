"""HTTPS-only, hash-recorded artifact retrieval."""

from __future__ import annotations

import hashlib
import os
import ssl
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import certifi


class DownloadError(RuntimeError):
    """Raised when an external artifact cannot pass retrieval controls."""


@dataclass(frozen=True)
class DownloadManifest:
    source_url: str
    final_url: str
    retrieved_at_utc: str
    sha256: str
    bytes: int
    destination: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_https(
    url: str,
    destination: Path,
    expected_sha256: Optional[str] = None,
    timeout_seconds: float = 60.0,
) -> DownloadManifest:
    """Download atomically and optionally reject an unexpected content hash."""
    if urlparse(url).scheme != "https":
        raise DownloadError("Only HTTPS sources are permitted.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Optional[Path] = None
    try:
        request = Request(url, headers={"User-Agent": "shockbridge-state-risk/0.1"})
        context = ssl.create_default_context(cafile=certifi.where())
        with urlopen(request, timeout=timeout_seconds, context=context) as response:
            final_url = response.geturl()
            if urlparse(final_url).scheme != "https":
                raise DownloadError("The source redirected away from HTTPS.")
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=destination.parent, delete=False
            ) as stream:
                temporary_path = Path(stream.name)
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    stream.write(chunk)
                stream.flush()
                os.fsync(stream.fileno())

        observed_hash = sha256_file(temporary_path)
        if expected_sha256 and observed_hash.lower() != expected_sha256.lower():
            raise DownloadError(
                f"SHA-256 mismatch: expected {expected_sha256}, observed {observed_hash}"
            )
        size = temporary_path.stat().st_size
        temporary_path.replace(destination)
        temporary_path = None
        return DownloadManifest(
            source_url=url,
            final_url=final_url,
            retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
            sha256=observed_hash,
            bytes=size,
            destination=str(destination),
        )
    except (OSError, URLError) as exc:
        raise DownloadError(str(exc)) from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
