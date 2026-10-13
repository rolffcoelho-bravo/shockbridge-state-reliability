#!/usr/bin/env python3
"""Fetch and audit the frozen Run 020 official-series pilot."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from shockbridge_state_risk.data.series_history import (  # noqa: E402
    audit_existing_series_pilot,
    fetch_and_audit_series_pilot,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "research/data/run_020_series_pilot_manifest_v1.yaml",
    )
    parser.add_argument(
        "--raw-directory",
        type=Path,
        default=ROOT / "data/raw/run020_series_pilot_v1",
    )
    parser.add_argument(
        "--audit-output",
        type=Path,
        default=ROOT / "reports/methodology/run_020_series_history_pilot.audit.json",
    )
    parser.add_argument(
        "--audit-existing",
        action="store_true",
        help="audit already downloaded immutable responses without network retrieval",
    )
    args = parser.parse_args()
    runner = audit_existing_series_pilot if args.audit_existing else fetch_and_audit_series_pilot
    audit = runner(
        args.manifest.resolve(), args.raw_directory.resolve(), args.audit_output.resolve()
    )
    print(json.dumps(asdict(audit), indent=2, sort_keys=True))
    return 0 if audit.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
