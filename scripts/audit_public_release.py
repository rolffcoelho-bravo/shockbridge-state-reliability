#!/usr/bin/env python3
"""Audit the tracked tree and Git history for public-release hazards."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "reports/methodology/run_012_public_release.audit.json"
SECRET_PATTERNS = {
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "aws_access_key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "github_token": re.compile(rb"gh[pousr]_[A-Za-z0-9]{30,}"),
    "openai_style_key": re.compile(rb"sk-[A-Za-z0-9]{20,}"),
    "slack_token": re.compile(rb"xox[baprs]-[A-Za-z0-9-]{20,}"),
    "google_api_key": re.compile(rb"AIza[0-9A-Za-z_-]{35}"),
    "credential_url": re.compile(rb"[a-zA-Z][a-zA-Z0-9+.-]*://[^/\s:@]+:[^/\s@]+@"),
}
PRIVACY_PATTERNS = {
    "macos_home": re.compile(rb"/Users/[A-Za-z0-9._-]+/"),
    "linux_home": re.compile(rb"/home/[A-Za-z0-9._-]+/"),
    "windows_home": re.compile(rb"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+\\"),
}
SUSPICIOUS_NAMES = {
    ".env",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
}


class PublicReleaseAuditError(RuntimeError):
    """Raised when the repository cannot be audited deterministically."""


def _git(arguments: list[str], *, text: bool = True) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=text,
    )


def _pattern_hits(content: bytes, patterns: dict[str, re.Pattern[bytes]]) -> list[str]:
    if b"\x00" in content:
        return []
    return [name for name, pattern in patterns.items() if pattern.search(content)]


def _tracked_paths() -> list[str]:
    output = _git(["ls-files", "-z"], text=False).stdout
    return sorted(path.decode("utf-8") for path in output.split(b"\x00") if path)


def _historical_blobs() -> dict[str, set[str]]:
    commits = _git(["rev-list", "--all"]).stdout.splitlines()
    blobs: dict[str, set[str]] = defaultdict(set)
    for commit in commits:
        output = _git(["ls-tree", "-r", "-z", commit], text=False).stdout
        for record in output.split(b"\x00"):
            if not record:
                continue
            metadata, path = record.split(b"\t", 1)
            _mode, kind, object_id = metadata.decode("ascii").split()
            if kind == "blob":
                blobs[object_id].add(path.decode("utf-8"))
    return blobs


def _finding(
    pattern: str, paths: set[str] | list[str], object_id: str | None = None
) -> dict[str, Any]:
    result: dict[str, Any] = {"pattern": pattern, "paths": sorted(paths)}
    if object_id is not None:
        result["blob"] = object_id
    return result


def _is_allowed_data_placeholder(path: str) -> bool:
    candidate = Path(path)
    protected = candidate.parts[:2] in {
        ("data", "raw"),
        ("data", "processed"),
        ("data", "interim"),
        ("data", "feature_store"),
    }
    return not protected or candidate.name == ".gitkeep"


def audit() -> dict[str, Any]:
    tracked = _tracked_paths()
    current_secrets: list[dict[str, Any]] = []
    current_privacy: list[dict[str, Any]] = []
    for relative in tracked:
        content = (ROOT / relative).read_bytes()
        current_secrets.extend(
            _finding(pattern, [relative]) for pattern in _pattern_hits(content, SECRET_PATTERNS)
        )
        current_privacy.extend(
            _finding(pattern, [relative]) for pattern in _pattern_hits(content, PRIVACY_PATTERNS)
        )

    history_secrets: list[dict[str, Any]] = []
    history_privacy: list[dict[str, Any]] = []
    blobs = _historical_blobs()
    for object_id, paths in sorted(blobs.items()):
        content = _git(["cat-file", "blob", object_id], text=False).stdout
        history_secrets.extend(
            _finding(pattern, paths, object_id)
            for pattern in _pattern_hits(content, SECRET_PATTERNS)
        )
        history_privacy.extend(
            _finding(pattern, paths, object_id)
            for pattern in _pattern_hits(content, PRIVACY_PATTERNS)
        )

    suspicious_filenames = [
        path
        for path in tracked
        if Path(path).name.lower() in SUSPICIOUS_NAMES
        or Path(path).suffix.lower() in {".key", ".pem", ".p12", ".pfx"}
    ]
    prohibited_data_paths = [path for path in tracked if not _is_allowed_data_placeholder(path)]
    authors = sorted(
        {
            tuple(record.split("\x00", 1))
            for record in _git(["log", "--all", "--format=%an%x00%ae"]).stdout.splitlines()
        }
    )
    public_author_records = [
        {"name": name, "email": email}
        for name, email in authors
        if not email.endswith("@localhost")
    ]
    blockers = {
        "current_secret_findings": len(current_secrets),
        "history_secret_findings": len(history_secrets),
        "current_privacy_findings": len(current_privacy),
        "history_privacy_findings": len(history_privacy),
        "suspicious_filenames": len(suspicious_filenames),
        "prohibited_tracked_data_paths": len(prohibited_data_paths),
        "public_author_identity_records": len(public_author_records),
    }
    return {
        "schema_version": 1,
        "audit_id": "run-012-public-release-v1",
        "git_head": _git(["rev-parse", "HEAD"]).stdout.strip(),
        "tracked_file_count": len(tracked),
        "historical_commit_count": len(_git(["rev-list", "--all"]).stdout.splitlines()),
        "unique_historical_blob_count": len(blobs),
        "credential_scan_status": (
            "PASS" if not current_secrets and not history_secrets else "FAIL"
        ),
        "current_tree_privacy_status": "PASS" if not current_privacy else "FAIL",
        "full_history_privacy_status": "PASS" if not history_privacy else "FAIL",
        "data_boundary_status": "PASS" if not prohibited_data_paths else "FAIL",
        "status": "PUBLICATION_READY" if not any(blockers.values()) else "PUBLICATION_BLOCKED",
        "blocker_counts": blockers,
        "current_secret_findings": current_secrets,
        "history_secret_findings": history_secrets,
        "current_privacy_findings": current_privacy,
        "history_privacy_findings": history_privacy,
        "suspicious_filenames": suspicious_filenames,
        "prohibited_tracked_data_paths": prohibited_data_paths,
        "public_author_identity_records": public_author_records,
        "scan_boundaries": {
            "binary_files_skipped_for_content_patterns": True,
            "home_path_usernames_limited_to_portable_account_characters": True,
            "high_entropy_generic_secret_detection_performed": False,
            "legal_opinion_provided": False,
        },
    }


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    if path.exists() or path.with_suffix(path.suffix + ".part").exists():
        raise PublicReleaseAuditError(f"Release audit is immutable and already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = audit()
    _atomic_json(payload, args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
