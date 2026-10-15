#!/usr/bin/env python3
"""Retrieve and build the approved Run 023 point-in-time panels."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from shockbridge_state_risk.data.full_panel_build import (
    build_run023_panels,
    retrieve_run023_inputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("retrieve", "build", "all"))
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path(
            "research/methodology/run_023_full_history_retrieval_and_panel_build_protocol_v1.yaml"
        ),
    )
    parser.add_argument("--raw-directory", type=Path, default=Path("data/raw/run023_full_panel_v1"))
    parser.add_argument(
        "--retrieval-manifest",
        type=Path,
        default=Path("data/manifests/run_023_full_history_sources_v1.yaml"),
    )
    parser.add_argument(
        "--processed-directory",
        type=Path,
        default=Path("data/processed/run023_full_panel_v1"),
    )
    parser.add_argument(
        "--audit-output",
        type=Path,
        default=Path("reports/methodology/run_023_full_panel_build.audit.json"),
    )
    args = parser.parse_args()

    if args.mode in {"retrieve", "all"}:
        records = retrieve_run023_inputs(args.protocol, args.raw_directory, args.retrieval_manifest)
        print(json.dumps({"retrieved": len(records)}, sort_keys=True))
    if args.mode in {"build", "all"}:
        audit = build_run023_panels(
            args.protocol,
            args.raw_directory,
            args.retrieval_manifest,
            args.processed_directory,
            args.audit_output,
        )
        print(json.dumps(asdict(audit), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
