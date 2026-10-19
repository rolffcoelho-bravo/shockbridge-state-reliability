#!/usr/bin/env python3
"""Audit whether Run 026 uniquely determines an empirical execution."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from shockbridge_state_risk.state.reliability_protocol_completeness import (
    audit_protocol_completeness,
)


def _write_once(payload: dict[str, object], output: Path) -> None:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite completeness audit: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".part", dir=output.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


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
    audit = audit_protocol_completeness(args.protocol)
    payload = audit.as_dict()
    if args.output is not None:
        _write_once(payload, args.output)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if audit.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
