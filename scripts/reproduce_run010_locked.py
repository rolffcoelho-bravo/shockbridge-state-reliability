#!/usr/bin/env python3
"""Verify the Run 012 lock files in a clean archive and reproduce Run 010 exactly."""

from __future__ import annotations

import io
import json
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import venv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.reproduce_run010_clean import (  # noqa: E402
    CANONICAL_HASHES,
    INPUT_HASHES,
    OUTPUT_HASHES,
    ReproductionError,
    _atomic_json,
    _run,
    sha256_file,
    verify_files,
)

AUDIT_PATH = ROOT / "reports/methodology/run_012_locked_reproduction.audit.json"
LOCK_PATHS = {
    "build": ROOT / "requirements/build-py39.lock",
    "runtime": ROOT / "requirements/runtime-py39.lock",
    "dev": ROOT / "requirements/dev-py39.lock",
}
INVENTORY_PATH = ROOT / "data/manifests/local_artifact_inventory_2026-10-02.yaml"
EXPECTED_VERSIONS = {
    "PyYAML": "6.0.3",
    "certifi": "2026.7.22",
    "coverage": "7.10.7",
    "et_xmlfile": "2.0.0",
    "librt": "0.16.0",
    "mypy": "1.19.1",
    "mypy_extensions": "1.1.0",
    "numpy": "1.26.4",
    "openpyxl": "3.1.5",
    "packaging": "26.3",
    "pathspec": "1.1.1",
    "pip": "26.0.1",
    "ruff": "0.16.10",
    "setuptools": "82.0.1",
    "tomli": "2.4.1",
    "types-PyYAML": "6.0.12.20250915",
    "typing_extensions": "4.16.0",
    "wheel": "0.48.0",
}


def _lock_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name, canonical in LOCK_PATHS.items():
        relative = canonical.relative_to(ROOT)
        path = root / relative
        if not path.is_file():
            raise ReproductionError(f"Missing dependency lock: {relative}")
        hashes[name] = sha256_file(path)
    return hashes


def _runtime_versions(python: Path, checkout: Path) -> dict[str, str]:
    packages = json.dumps(tuple(EXPECTED_VERSIONS))
    command = (
        "import json, platform; from importlib.metadata import version; "
        f"names={packages}; "
        "print(json.dumps({'python': platform.python_version(), "
        "**{name: version(name) for name in names}}, sort_keys=True))"
    )
    payload = json.loads(_run([str(python), "-c", command], checkout).stdout)
    observed = {name: payload[name] for name in EXPECTED_VERSIONS}
    if observed != EXPECTED_VERSIONS:
        raise ReproductionError(
            "Locked environment version mismatch: "
            f"expected={EXPECTED_VERSIONS}, observed={observed}"
        )
    if not str(payload["python"]).startswith("3.9."):
        raise ReproductionError(f"Locked reproduction requires Python 3.9, got {payload['python']}")
    return {str(key): str(value) for key, value in payload.items()}


def _hydrate_registered_artifacts(source_root: Path, checkout: Path) -> int:
    inventory_path = source_root / INVENTORY_PATH.relative_to(ROOT)
    payload = yaml.safe_load(inventory_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("artifacts"), list):
        raise ReproductionError("The local artifact inventory is malformed.")
    hydrated = 0
    for index, raw_record in enumerate(payload["artifacts"]):
        if not isinstance(raw_record, dict):
            raise ReproductionError(f"Inventory artifact {index} is not a mapping.")
        relative = Path(str(raw_record.get("path", "")))
        expected_hash = str(raw_record.get("sha256", ""))
        expected_bytes = int(raw_record.get("bytes", -1))
        if relative.is_absolute() or ".." in relative.parts or not str(relative):
            raise ReproductionError(f"Unsafe inventory artifact path: {relative}")
        source = source_root / relative
        target = checkout / relative
        if not source.is_file():
            raise ReproductionError(f"Missing inventory artifact: {relative}")
        if source.stat().st_size != expected_bytes or sha256_file(source) != expected_hash:
            raise ReproductionError(f"Changed inventory artifact: {relative}")
        if target.exists():
            if target.stat().st_size != expected_bytes or sha256_file(target) != expected_hash:
                raise ReproductionError(f"Archive artifact differs from inventory: {relative}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        hydrated += 1
    return hydrated


def reproduce() -> dict[str, Any]:
    if AUDIT_PATH.exists():
        raise ReproductionError("The locked-reproduction audit already exists.")
    status = _run(["git", "status", "--porcelain=v1"], ROOT)
    if status.stdout.strip():
        raise ReproductionError("Locked reproduction requires a clean Git worktree.")
    source_commit = _run(["git", "rev-parse", "HEAD"], ROOT).stdout.strip()
    lock_hashes = _lock_hashes(ROOT)
    canonical_before = verify_files(ROOT, CANONICAL_HASHES, "canonical output")
    hydrated_inputs = verify_files(ROOT, INPUT_HASHES, "registered input")
    started_at = datetime.now(timezone.utc).isoformat()
    started_clock = time.monotonic()

    with tempfile.TemporaryDirectory(prefix="shockbridge-run012-") as temporary_text:
        temporary = Path(temporary_text)
        checkout = temporary / "checkout"
        checkout.mkdir()
        archive = subprocess.run(
            ["git", "archive", "--format=tar", source_commit],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
        )
        with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as stream:
            stream.extractall(checkout)
        if _lock_hashes(checkout) != lock_hashes:
            raise ReproductionError("Dependency locks changed in the clean archive.")
        hydrated_artifact_count = _hydrate_registered_artifacts(ROOT, checkout)
        verify_files(checkout, INPUT_HASHES, "hydrated clean-checkout input")

        environment = temporary / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = environment / "bin/python"
        pip_base = [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
        ]
        _run([*pip_base, "-r", "requirements/build-py39.lock"], checkout)
        _run([*pip_base, "-r", "requirements/dev-py39.lock"], checkout)
        _run([*pip_base, "--no-deps", "-e", str(checkout)], checkout)
        runtime_versions = _runtime_versions(python, checkout)

        _run([str(python), "-m", "ruff", "check", "."], checkout)
        _run([str(python), "-m", "ruff", "format", "--check", "."], checkout)
        _run([str(python), "-m", "mypy", "src"], checkout)
        _run(
            [
                str(python),
                "-m",
                "coverage",
                "run",
                "--branch",
                "--source",
                "shockbridge_state_risk",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-q",
            ],
            checkout,
        )
        coverage = _run(
            [str(python), "-m", "coverage", "report", "--fail-under=90", "--format=total"],
            checkout,
        ).stdout.strip()

        reproduction = checkout / "reproduction"
        _run(
            [
                str(python),
                "-m",
                "shockbridge_state_risk",
                "run-vintage-robustness",
                "experiments/state_vintage_robustness_run010_v1.yaml",
                "--comparison-output",
                str(reproduction / "comparison.csv"),
                "--geometry-output",
                str(reproduction / "geometry.csv"),
                "--episode-output",
                str(reproduction / "episodes.csv"),
                "--audit-output",
                str(reproduction / "audit.json"),
            ],
            checkout,
        )
        reproduced_hashes = verify_files(reproduction, OUTPUT_HASHES, "reproduced output")

    canonical_after = verify_files(ROOT, CANONICAL_HASHES, "canonical output")
    if canonical_before != canonical_after:
        raise ReproductionError("Canonical Run 010 outputs changed during locked reproduction.")
    return {
        "schema_version": 1,
        "audit_id": "run-012-locked-reproduction-v1",
        "status": "LOCKED_EXACT_REPRODUCTION_PASS",
        "source_git_commit": source_commit,
        "started_at_utc": started_at,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.monotonic() - started_clock, 3),
        "orchestrator_python": platform.python_version(),
        "orchestrator_platform": platform.platform(),
        "isolated_runtime_versions": runtime_versions,
        "lock_sha256": lock_hashes,
        "local_inventory_sha256": sha256_file(INVENTORY_PATH),
        "hydrated_untracked_artifact_count": hydrated_artifact_count,
        "registered_input_hashes": hydrated_inputs,
        "target_output_hashes": OUTPUT_HASHES,
        "reproduced_output_hashes": reproduced_hashes,
        "coverage_total_percent": int(coverage),
        "full_quality_suite_passed": True,
        "canonical_outputs_unchanged": True,
        "temporary_checkout_removed": True,
        "outcomes_accessed": False,
        "synthetic_observations_used_for_empirical_result": False,
        "second_python_minor_or_operating_system_tested": False,
    }


def main() -> int:
    if sys.argv[1:] == ["--self-check"]:
        print("run012-locked-reproducer-import-ok")
        return 0
    payload = reproduce()
    _atomic_json(payload, AUDIT_PATH)
    print(AUDIT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
