#!/usr/bin/env python3
"""Verify the complete sanitized-export story and write a portable audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any


class PublicExportVerificationError(RuntimeError):
    """Raised when a verification audit cannot be written safely."""


def _digest(value: str) -> dict[str, Any]:
    encoded = value.encode("utf-8")
    return {"bytes": len(encoded), "sha256": hashlib.sha256(encoded).hexdigest()}


def _run(
    label: str,
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
) -> tuple[dict[str, Any], subprocess.CompletedProcess[str]]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    record = {
        "label": label,
        "returncode": completed.returncode,
        "stdout": _digest(completed.stdout),
        "stderr": _digest(completed.stderr),
    }
    return record, completed


def _last_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    candidates: list[dict[str, Any]] = []
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            candidates.append(value)
    if not candidates:
        raise PublicExportVerificationError("Public test runner emitted no JSON summary")
    return candidates[-1]


def _archive_violations(archive_path: Path) -> list[str]:
    violations: list[str] = []
    protected = {"raw", "interim", "processed", "feature_store"}
    with tarfile.open(archive_path, mode="r:gz") as archive:
        for member in archive.getmembers():
            path = Path(member.name)
            if "shockbridge_state_risk_flagship_blueprint" in path.name:
                violations.append(member.name)
            parts = path.parts
            if "data" in parts:
                index = parts.index("data")
                if len(parts) > index + 2 and parts[index + 1] in protected:
                    if parts[-1] != ".gitkeep":
                        violations.append(member.name)
    return sorted(set(violations))


def verify(root: Path, archive: Path, bundle: Path) -> dict[str, Any]:
    root = root.resolve()
    archive = archive.resolve()
    bundle = bundle.resolve()
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join((str(root / "src"), str(root)))
    python = sys.executable
    commands = [
        ("ruff_check", [python, "-m", "ruff", "check", "."]),
        ("ruff_format", [python, "-m", "ruff", "format", "--check", "."]),
        ("mypy", [python, "-m", "mypy", "src"]),
        (
            "package_origin",
            [
                python,
                "-c",
                "import pathlib, shockbridge_state_risk as p; "
                "print(pathlib.Path(p.__file__).resolve())",
            ],
        ),
        (
            "public_tests",
            [
                python,
                "-m",
                "coverage",
                "run",
                "--branch",
                "--source",
                "shockbridge_state_risk",
                "scripts/run_public_tests.py",
                "--expected-evidence-skips",
                "7",
            ],
        ),
        ("public_coverage", [python, "-m", "coverage", "report", "--fail-under=87"]),
        ("git_fsck", ["git", "fsck", "--full", "--strict"]),
        ("bundle_verify", ["git", "bundle", "verify", str(bundle)]),
    ]
    records: list[dict[str, Any]] = []
    completed_by_label: dict[str, subprocess.CompletedProcess[str]] = {}
    for label, command in commands:
        record, completed = _run(label, command, cwd=root, environment=environment)
        records.append(record)
        completed_by_label[label] = completed

    public_summary: dict[str, Any] = {}
    if completed_by_label["public_tests"].stdout:
        try:
            public_summary = _last_json_object(completed_by_label["public_tests"].stdout)
        except PublicExportVerificationError:
            public_summary = {"parse_error": True}
    package_origin = completed_by_label["package_origin"].stdout.strip()
    origin_inside_export = package_origin.startswith(str(root) + os.sep)
    commits = subprocess.run(
        ["git", "rev-list", "--all"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.splitlines()
    root_fields = subprocess.run(
        ["git", "rev-list", "--parents", "-n", "1", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    status = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    archive_violations = _archive_violations(archive)
    blockers = {
        "failed_commands": sum(record["returncode"] != 0 for record in records),
        "package_origin_outside_export": int(not origin_inside_export),
        "history_shape_failures": int(len(commits) != 1 or len(root_fields) != 1),
        "uncommitted_nonignored_paths": len(status),
        "archive_boundary_violations": len(archive_violations),
        "public_test_summary_parse_failure": int(bool(public_summary.get("parse_error"))),
    }
    return {
        "schema_version": 1,
        "audit_id": "run-013-public-export-complete-verification-v1",
        "status": "PUBLIC_EXPORT_VERIFIED"
        if not any(blockers.values())
        else "PUBLIC_EXPORT_BLOCKED",
        "root_name": root.name,
        "archive_name": archive.name,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "bundle_name": bundle.name,
        "bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
        "commit_count": len(commits),
        "head_is_parentless": len(root_fields) == 1,
        "package_origin_inside_export": origin_inside_export,
        "public_test_summary": public_summary,
        "archive_boundary_violations": archive_violations,
        "blocker_counts": blockers,
        "commands": records,
        "audit_output_policy": "command output retained only as byte counts and SHA-256 hashes",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise PublicExportVerificationError(f"Audit output already exists: {args.output}")
    payload = verify(args.root, args.archive, args.bundle)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".part")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(args.output)
    return 0 if payload["status"] == "PUBLIC_EXPORT_VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
