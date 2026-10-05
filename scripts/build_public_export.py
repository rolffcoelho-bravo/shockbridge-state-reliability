#!/usr/bin/env python3
"""Build an immutable, squashed local public-repository candidate."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.safe_tar import (  # noqa: E402
    UnsafeTarError,
    extract_tar_safely,
    safe_tar_member,
)

DEFAULT_OUTPUT = ROOT / "artifacts/public-export/shockbridge-state-reliability"
EXCLUDED_PATHS = {
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
COMMIT_DATE = "2026-10-04T12:00:00+02:00"


class PublicExportBuildError(RuntimeError):
    """Raised when the public export cannot be built without ambiguity."""


def _git(arguments: list[str], *, cwd: Path = ROOT, text: bool = True) -> Any:
    return subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=text,
    ).stdout


def _safe_member(member: tarfile.TarInfo) -> bool:
    """Compatibility wrapper for the public-export structural audit."""
    return safe_tar_member(member)


def _file_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


def _portable_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _write_export_manifest(output: Path, source_commit: str) -> None:
    payload = {
        "schema_version": 1,
        "export_id": "run-013-sanitized-public-export-v1",
        "source_commit": source_commit,
        "history_policy": "single sanitized root commit; canonical history excluded",
        "excluded_paths": sorted(EXCLUDED_PATHS),
        "files": _file_hashes(output),
    }
    (output / "PUBLIC_EXPORT_MANIFEST.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _initialize_repository(output: Path) -> str:
    _git(["init", "-b", "main"], cwd=output)
    _git(["add", "--all"], cwd=output)
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_DATE": COMMIT_DATE,
            "GIT_COMMITTER_DATE": COMMIT_DATE,
            "GIT_AUTHOR_NAME": "Rodolfo Pereira",
            "GIT_AUTHOR_EMAIL": "research-release@localhost",
            "GIT_COMMITTER_NAME": "Rodolfo Pereira",
            "GIT_COMMITTER_EMAIL": "research-release@localhost",
        }
    )
    subprocess.run(
        ["git", "commit", "-m", "Public reproducibility release candidate"],
        cwd=output,
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    return _git(["rev-parse", "HEAD"], cwd=output).strip()


def _write_reproducible_archive(output: Path, destination: Path) -> None:
    with destination.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for path in sorted(output.rglob("*")):
                    relative = path.relative_to(output)
                    if ".git" in relative.parts or not path.is_file():
                        continue
                    info = archive.gettarinfo(
                        str(path), arcname=(Path(output.name) / relative).as_posix()
                    )
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    with path.open("rb") as handle:
                        archive.addfile(info, handle)


def build(output: Path) -> dict[str, Any]:
    output = output.resolve()
    status = _git(["status", "--porcelain=v1"])
    if status:
        raise PublicExportBuildError("Canonical source tree must be clean before export")
    if output.exists():
        raise PublicExportBuildError(f"Immutable export already exists: {output}")
    archive_path = output.parent / f"{output.name}.tar.gz"
    bundle_path = output.parent / f"{output.name}.bundle"
    for artifact in (archive_path, bundle_path):
        if artifact.exists():
            raise PublicExportBuildError(f"Immutable export artifact already exists: {artifact}")

    source_commit = _git(["rev-parse", "HEAD"]).strip()
    archive_bytes = _git(["archive", "--format=tar", "HEAD"], text=False)
    output.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
        try:
            extract_tar_safely(archive, output)
        except UnsafeTarError as error:
            raise PublicExportBuildError(f"Unsafe Git archive: {error}") from error

    for relative in EXCLUDED_PATHS:
        candidate = output / relative
        if not candidate.is_file():
            raise PublicExportBuildError(
                f"Frozen exclusion missing from source archive: {relative}"
            )
        candidate.unlink()
    _write_export_manifest(output, source_commit)
    export_commit = _initialize_repository(output)
    _write_reproducible_archive(output, archive_path)
    _git(["bundle", "create", str(bundle_path), "main"], cwd=output)
    return {
        "source_commit": source_commit,
        "export_commit": export_commit,
        "output": _portable_path(output),
        "tracked_files": len(_git(["ls-files"], cwd=output).splitlines()),
        "archive": _portable_path(archive_path),
        "archive_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        "archive_bytes": archive_path.stat().st_size,
        "bundle": _portable_path(bundle_path),
        "bundle_sha256": hashlib.sha256(bundle_path.read_bytes()).hexdigest(),
        "bundle_bytes": bundle_path.stat().st_size,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    if args.receipt.exists():
        raise PublicExportBuildError(f"Receipt already exists: {args.receipt}")
    payload = build(args.output)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
