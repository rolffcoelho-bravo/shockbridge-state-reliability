#!/usr/bin/env python3
"""Execute the frozen Run 025 DFR effective-date source audit."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from shockbridge_state_risk.data.dfr_effective_date import (
    build_run025_dfr_effective_date_amendment,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path(
            "research/methodology/run_025_dfr_effective_date_source_audit_protocol_v1.yaml"
        ),
    )
    parser.add_argument(
        "--source-manifest",
        type=Path,
        default=Path("data/manifests/run_025_dfr_effective_date_source_v1.yaml"),
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("data/processed/run025_dfr_effective_dates_v1"),
    )
    parser.add_argument(
        "--audit-output",
        type=Path,
        default=Path("reports/methodology/run_025_dfr_effective_date_source.audit.json"),
    )
    args = parser.parse_args()
    audit = build_run025_dfr_effective_date_amendment(
        args.protocol,
        args.source_manifest,
        args.output_directory,
        args.audit_output,
    )
    print(json.dumps(asdict(audit), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
