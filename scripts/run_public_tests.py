#!/usr/bin/env python3
"""Run the source-only public test surface with an exact evidence-skip contract."""

from __future__ import annotations

import argparse
import json
import unittest

EVIDENCE_SKIP_REASON = "requires local hash-registered evidence"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-evidence-skips", type=int, default=7)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.discover("tests")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    skip_reasons = [reason for _test, reason in result.skipped]
    unexpected_reasons = sorted(reason for reason in skip_reasons if reason != EVIDENCE_SKIP_REASON)
    summary = {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "expected_evidence_skips": args.expected_evidence_skips,
        "unexpected_skip_reasons": unexpected_reasons,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not result.wasSuccessful():
        return 1
    if len(result.skipped) != args.expected_evidence_skips or unexpected_reasons:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
