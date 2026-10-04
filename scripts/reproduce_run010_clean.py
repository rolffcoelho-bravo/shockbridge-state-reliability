#!/usr/bin/env python3
"""Reproduce Run 010 from a clean Git archive and isolated virtual environment."""

from __future__ import annotations

import hashlib
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

ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "02fdfd1"
AUDIT_PATH = ROOT / "reports/methodology/run_011_clean_reproduction.audit.json"
INPUT_HASHES = {
    "data/processed/monthly_state_panel_v2.csv": (
        "80d5e5f4b04fb7551bc69d4c4b429271258efad09987d9971551fd4a477f527e"
    ),
    "data/processed/state_instability_run009_v1.csv": (
        "c177cfac7fe553d48ada0509d95d665c9c424aa93d339fa3a96ae69bb6553af4"
    ),
    "data/raw/ecb_state/run010_latest_hicp.csv": (
        "d04f0211cc9ab2a0d0dea254c3d814b17e74366b484c59fb62085f27cf7ce154"
    ),
    "data/raw/ecb_state/run010_latest_ip.csv": (
        "48825eaff5ec41c8653f53a97803e4c705f11bc34daff3a54633b8ed84914064"
    ),
    "data/raw/ecb_state/run010_latest_unemployment.csv": (
        "db2bac035fdb4c3497a7ced0e08f53626a88d99b925c28834328b6431c580dc0"
    ),
}
OUTPUT_HASHES = {
    "comparison.csv": "9044465d54cc51c1a7885c48d7228ba90e52747c814222cde0a0413f56ffb0df",
    "geometry.csv": "7a639d4b2b9a4bed73ded627961bdd8c08cdfba13889adaab3f652ef6f24be32",
    "episodes.csv": "67dec146bae186bc9e5680be36ec6caf80443bbc3449af99601c4a8c53e5001b",
    "audit.json": "6631f7ad8fd2bffc2d1d606e39a187029ea96d5adac61269af4c25f3d6584b81",
}
CANONICAL_OUTPUTS = {
    "comparison.csv": "data/processed/state_vintage_comparison_run010_v1.csv",
    "geometry.csv": "data/processed/state_vintage_geometry_run010_v1.csv",
    "episodes.csv": "data/processed/state_vintage_episodes_run010_v1.csv",
    "audit.json": "reports/methodology/state_vintage_robustness_run010_v1.audit.json",
}
CANONICAL_HASHES = {
    relative: OUTPUT_HASHES[filename] for filename, relative in CANONICAL_OUTPUTS.items()
}


class ReproductionError(RuntimeError):
    """Raised when the clean reproduction contract is violated."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_files(root: Path, expected: dict[str, str], context: str) -> dict[str, str]:
    observed: dict[str, str] = {}
    for relative, expected_hash in expected.items():
        path = root / relative
        if not path.is_file():
            raise ReproductionError(f"Missing {context} artifact: {relative}")
        observed_hash = sha256_file(path)
        if observed_hash != expected_hash:
            raise ReproductionError(
                f"Changed {context} artifact: {relative}; "
                f"expected {expected_hash}, observed {observed_hash}"
            )
        observed[relative] = observed_hash
    return observed


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        rendered = " ".join(command)
        raise ReproductionError(
            f"Command failed with exit {error.returncode}: {rendered}\n"
            f"stdout:\n{error.stdout}\nstderr:\n{error.stderr}"
        ) from error


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    if path.exists() or path.with_suffix(path.suffix + ".part").exists():
        raise ReproductionError("The clean-reproduction audit is immutable and already exists.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def reproduce() -> dict[str, Any]:
    if AUDIT_PATH.exists():
        raise ReproductionError("The clean-reproduction audit already exists.")
    canonical_before = verify_files(ROOT, CANONICAL_HASHES, "canonical output")
    hydrated_inputs = verify_files(ROOT, INPUT_HASHES, "registered input")
    started_at = datetime.now(timezone.utc).isoformat()
    started_clock = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="shockbridge-run011-") as temporary_text:
        temporary = Path(temporary_text)
        checkout = temporary / "checkout"
        checkout.mkdir()
        archive = subprocess.run(
            ["git", "archive", "--format=tar", SOURCE_COMMIT],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
        )
        with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as stream:
            stream.extractall(checkout)
        for relative in INPUT_HASHES:
            source = ROOT / relative
            target = checkout / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        verify_files(checkout, INPUT_HASHES, "hydrated clean-checkout input")

        environment = temporary / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = environment / "bin/python"
        pip = environment / "bin/pip"
        _run(
            [
                str(pip),
                "install",
                "--disable-pip-version-check",
                "--no-input",
                "--upgrade",
                "pip",
                "setuptools",
                "wheel",
            ],
            checkout,
        )
        _run(
            [
                str(pip),
                "install",
                "--disable-pip-version-check",
                "--no-input",
                "-e",
                str(checkout),
            ],
            checkout,
        )
        runtime = _run(
            [
                str(python),
                "-c",
                (
                    "import json, platform; "
                    "from importlib.metadata import version; "
                    "print(json.dumps({'python': platform.python_version(), "
                    "'numpy': version('numpy'), 'PyYAML': version('PyYAML'), "
                    "'certifi': version('certifi'), 'openpyxl': version('openpyxl'), "
                    "'pip': version('pip'), 'setuptools': version('setuptools'), "
                    "'wheel': version('wheel')}))"
                ),
            ],
            checkout,
        )
        runtime_versions = json.loads(runtime.stdout)
        reproduction = checkout / "reproduction"
        command = [
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
        ]
        execution = _run(command, checkout)
        reproduced_hashes = verify_files(reproduction, OUTPUT_HASHES, "reproduced output")

    canonical_after = verify_files(ROOT, CANONICAL_HASHES, "canonical output")
    if canonical_before != canonical_after:
        raise ReproductionError("Canonical Run 010 outputs changed during clean reproduction.")
    return {
        "schema_version": 1,
        "audit_id": "run-011-clean-reproduction-v1",
        "status": "EXACT_REPRODUCTION_PASS",
        "source_git_commit": SOURCE_COMMIT,
        "started_at_utc": started_at,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.monotonic() - started_clock, 3),
        "orchestrator_python": platform.python_version(),
        "isolated_runtime_versions": runtime_versions,
        "registered_input_hashes": hydrated_inputs,
        "target_output_hashes": OUTPUT_HASHES,
        "reproduced_output_hashes": reproduced_hashes,
        "canonical_outputs_unchanged": True,
        "temporary_checkout_removed": True,
        "outcomes_accessed": False,
        "synthetic_observations_used": False,
        "execution_stdout": execution.stdout.strip(),
    }


def main() -> int:
    payload = reproduce()
    _atomic_json(payload, AUDIT_PATH)
    print(AUDIT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
