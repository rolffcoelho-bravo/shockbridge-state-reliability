#!/usr/bin/env python3
"""Execute the frozen Run 024 archive-identifier and timing amendment."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from shockbridge_state_risk.data.archive_timing_amendment import (
    build_run024_archive_timing_amendment,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path(
            "research/methodology/run_024_archive_identifier_and_timing_sensitivity_protocol_v1.yaml"
        ),
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("data/processed/run024_archive_timing_v1"),
    )
    parser.add_argument(
        "--audit-output",
        type=Path,
        default=Path("reports/methodology/run_024_archive_timing_sensitivity.audit.json"),
    )
    args = parser.parse_args()
    audit = build_run024_archive_timing_amendment(
        args.protocol, args.output_directory, args.audit_output
    )
    print(json.dumps(asdict(audit), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
