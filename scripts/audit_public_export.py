#!/usr/bin/env python3
"""Audit a sanitized single-commit repository without exposing secret values."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_public_release import (  # noqa: E402
    PRIVACY_PATTERNS,
    SECRET_PATTERNS,
    _is_allowed_data_placeholder,
    _pattern_hits,
)

PRIVATE_ONLY_PATHS = {
    "reports/methodology/run_013_public_export_build_attempt1.audit.json",
    "reports/methodology/run_013_public_export_build_attempt2.audit.json",
    "reports/methodology/run_013_public_export_build_attempt3.audit.json",
    "reports/methodology/run_013_public_export_build_attempt4.audit.json",
    "reports/methodology/run_013_public_export_build_attempt5.audit.json",
    "reports/methodology/run_013_public_export_build_attempt6.audit.json",
    "reports/methodology/run_013_public_export_security_attempt1.audit.json",
    "reports/methodology/run_013_public_export_security_attempt2.audit.json",
    "reports/methodology/run_013_public_export_security_attempt3.audit.json",
    "reports/methodology/run_013_public_export_security_attempt4.audit.json",
    "reports/methodology/run_013_public_export_security_attempt5.audit.json",
    "reports/methodology/run_013_public_export_security_attempt6.audit.json",
    "reports/methodology/run_013_public_export_verification_attempt5.audit.json",
    "reports/methodology/run_013_public_export_verification_attempt6.audit.json",
    "shockbridge_state_risk_flagship_blueprint_v1.md",
    "shockbridge_state_risk_flagship_blueprint_v2.md",
}
REQUIRED_RELEASE_FILES = {"CITATION.cff", "LICENSE", "LICENSE-DOCS.md", "NOTICE"}
TOKEN_PATTERN = re.compile(rb"(?<![A-Za-z0-9])[A-Za-z0-9_+/=-]{24,160}(?![A-Za-z0-9])")
HEX_PATTERN = re.compile(rb"[0-9a-fA-F]{32,128}")


class PublicExportAuditError(RuntimeError):
    """Raised when an export cannot be audited deterministically."""


def _git(root: Path, arguments: list[str], *, text: bool = True) -> Any:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=text,
    ).stdout


def shannon_entropy(value: bytes) -> float:
    """Return Shannon entropy in bits per byte for an ASCII candidate."""
    if not value:
        return 0.0
    counts = Counter(value)
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def is_high_entropy_candidate(value: bytes, *, threshold: float = 4.5) -> bool:
    """Conservatively flag secret-like mixed tokens while excluding registered hashes."""
    if HEX_PATTERN.fullmatch(value):
        return False
    if value.count(b"/") >= 2:
        return False
    if b"=" in value.rstrip(b"="):
        return False
    classes = (
        any(65 <= char <= 90 for char in value),
        any(97 <= char <= 122 for char in value),
        any(48 <= char <= 57 for char in value),
        any(char in b"_+/=-" for char in value),
    )
    if sum(classes) < 3 or not classes[2]:
        return False
    return shannon_entropy(value) >= threshold


def _tracked_paths(root: Path) -> list[str]:
    output = _git(root, ["ls-files", "-z"], text=False)
    return sorted(path.decode("utf-8") for path in output.split(b"\x00") if path)


def _scan_file(path: Path, relative: str) -> dict[str, list[dict[str, Any]]]:
    content = path.read_bytes()
    if b"\x00" in content:
        return {"secrets": [], "privacy": [], "entropy": []}
    secrets = [
        {"pattern": name, "path": relative} for name in _pattern_hits(content, SECRET_PATTERNS)
    ]
    privacy = [
        {"pattern": name, "path": relative} for name in _pattern_hits(content, PRIVACY_PATTERNS)
    ]
    entropy: list[dict[str, Any]] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        for match in TOKEN_PATTERN.finditer(line):
            candidate = match.group()
            if is_high_entropy_candidate(candidate):
                entropy.append(
                    {
                        "path": relative,
                        "line": line_number,
                        "length": len(candidate),
                        "entropy": round(shannon_entropy(candidate), 3),
                        "fingerprint": hashlib.sha256(candidate).hexdigest()[:12],
                    }
                )
    return {"secrets": secrets, "privacy": privacy, "entropy": entropy}


def _verify_manifest(root: Path, tracked: list[str]) -> list[dict[str, str]]:
    path = root / "PUBLIC_EXPORT_MANIFEST.json"
    if not path.is_file():
        return [{"path": "PUBLIC_EXPORT_MANIFEST.json", "reason": "missing"}]
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = payload.get("files", {})
    actual_paths = set(tracked) - {"PUBLIC_EXPORT_MANIFEST.json"}
    failures: list[dict[str, str]] = []
    if set(expected) != actual_paths:
        failures.append({"path": "PUBLIC_EXPORT_MANIFEST.json", "reason": "path_set_mismatch"})
        return failures
    for relative, registered_hash in sorted(expected.items()):
        actual_hash = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        if actual_hash != registered_hash:
            failures.append({"path": relative, "reason": "sha256_mismatch"})
    return failures


def audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    if not (root / ".git").is_dir():
        raise PublicExportAuditError(f"Not a Git repository: {root}")
    tracked = _tracked_paths(root)
    findings = {"secrets": [], "privacy": [], "entropy": []}
    for relative in tracked:
        result = _scan_file(root / relative, relative)
        for family in findings:
            findings[family].extend(result[family])

    commits = _git(root, ["rev-list", "--all"]).splitlines()
    head_with_parents = _git(root, ["rev-list", "--parents", "-n", "1", "HEAD"]).split()
    remotes = _git(root, ["remote"]).splitlines()
    prohibited_data = [path for path in tracked if not _is_allowed_data_placeholder(path)]
    excluded_present = sorted(PRIVATE_ONLY_PATHS.intersection(tracked))
    required_missing = sorted(REQUIRED_RELEASE_FILES.difference(tracked))
    manifest_failures = _verify_manifest(root, tracked)
    author_records = sorted(set(_git(root, ["log", "--format=%an%x00%ae"]).splitlines()))
    blockers = {
        "known_secret_findings": len(findings["secrets"]),
        "privacy_path_findings": len(findings["privacy"]),
        "high_entropy_candidate_findings": len(findings["entropy"]),
        "prohibited_data_paths": len(prohibited_data),
        "private_only_paths_present": len(excluded_present),
        "required_release_files_missing": len(required_missing),
        "manifest_failures": len(manifest_failures),
        "history_shape_failures": int(len(commits) != 1 or len(head_with_parents) != 1),
        "configured_remotes": len(remotes),
    }
    return {
        "schema_version": 1,
        "audit_id": "run-013-sanitized-public-export-v1",
        "root_name": root.name,
        "head": _git(root, ["rev-parse", "HEAD"]).strip(),
        "tracked_file_count": len(tracked),
        "commit_count": len(commits),
        "head_is_parentless": len(head_with_parents) == 1,
        "configured_remotes": remotes,
        "author_records": author_records,
        "status": "PUBLIC_EXPORT_READY" if not any(blockers.values()) else "PUBLIC_EXPORT_BLOCKED",
        "blocker_counts": blockers,
        "known_secret_findings": findings["secrets"],
        "privacy_path_findings": findings["privacy"],
        "high_entropy_candidate_findings": findings["entropy"],
        "prohibited_data_paths": prohibited_data,
        "private_only_paths_present": excluded_present,
        "required_release_files_missing": required_missing,
        "manifest_failures": manifest_failures,
        "scan_boundaries": {
            "secret_values_retained_in_report": False,
            "known_patterns_are_not_exhaustive": True,
            "high_entropy_threshold_bits_per_byte": 4.5,
            "pure_hex_hashes_excluded": True,
            "path_like_candidates_with_multiple_separators_excluded": True,
            "source_assignment_expressions_excluded": True,
            "binary_files_skipped": True,
            "hosted_secret_scan_still_required_before_publication": True,
        },
    }


def write_audit(payload: dict[str, Any], output: Path) -> None:
    if output.exists():
        raise PublicExportAuditError(f"Audit output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = audit(args.root)
    write_audit(payload, args.output)
    print(args.output)
    return 0 if payload["status"] == "PUBLIC_EXPORT_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
