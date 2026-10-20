#!/usr/bin/env python3
"""Write the immutable value-free Run 029 Stage-A readiness audit."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from shockbridge_state_risk.state.calibration_readiness import (  # noqa: E402
    audit_calibration_readiness,
)


def _write_once(payload: dict[str, object], output: Path) -> None:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite readiness audit: {output}")
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
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    audit = audit_calibration_readiness(
        ROOT
        / "research/methodology/run_026_information_clock_reliability_execution_protocol_v1.yaml",
        ROOT / "research/methodology/run_027_reliability_execution_amendment_proposal_v1.yaml",
        ROOT / "research/methodology/run_028_reliability_execution_amendment_approval_v1.yaml",
        ROOT / "src/shockbridge_state_risk/state/reliability_execution_harness.py",
        ROOT / "research/methodology/run_029_stage_A_calibration_approval_v1.yaml",
    )
    payload = audit.as_dict()
    if args.output is not None:
        _write_once(payload, args.output)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if audit.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
