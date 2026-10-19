#!/usr/bin/env python3
"""Run the outcome-sealed Run 026 protocol preflight."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from shockbridge_state_risk.state.reliability_execution_contract import (
    audit_reliability_execution_contract,
    write_reliability_execution_contract_audit,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path(
            "research/methodology/run_026_information_clock_reliability_execution_protocol_v1.yaml"
        ),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    audit = audit_reliability_execution_contract(args.protocol)
    if args.output is not None:
        write_reliability_execution_contract_audit(audit, args.output)
    print(json.dumps(asdict(audit), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
