"""Semantic completeness audit for the frozen reliability execution protocol.

Run 026 established byte integrity, provenance, and calendar consistency.  This
module performs the separate question that must be answered before empirical
execution: does the protocol uniquely determine every result-sensitive
operation?  It never imports panel values, the reliability engine, or any
transmission module.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


class ReliabilityProtocolCompletenessError(ValueError):
    """Raised when the semantic audit cannot safely inspect a protocol."""


@dataclass(frozen=True)
class ProtocolGap:
    gap_id: str
    severity: str
    location: str
    issue: str
    empirical_consequence: str
    required_resolution: str


@dataclass(frozen=True)
class ProtocolCompletenessAudit:
    audit_id: str
    protocol_path: str
    protocol_sha256: str
    passed: bool
    critical_gap_count: int
    result_sensitive_choice_count: int
    empirical_fit_performed: bool
    evaluation_results_accessed: bool
    transmission_outcomes_accessed: bool
    gaps: tuple[ProtocolGap, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReliabilityProtocolCompletenessError(f"{label} must be a mapping")
    return value


def _project_root(path: Path) -> Path:
    for candidate in (path.parent, *path.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate.resolve()
    raise ReliabilityProtocolCompletenessError("Cannot locate project root from protocol")


def _gap(
    gap_id: str,
    location: str,
    issue: str,
    consequence: str,
    resolution: str,
) -> ProtocolGap:
    return ProtocolGap(
        gap_id=gap_id,
        severity="CRITICAL_STOP_BEFORE_EMPIRICAL_FIT",
        location=location,
        issue=issue,
        empirical_consequence=consequence,
        required_resolution=resolution,
    )


def audit_protocol_completeness(protocol_path: Path) -> ProtocolCompletenessAudit:
    """Return a value-free audit of result-sensitive operational definitions."""
    path = protocol_path.resolve()
    if not path.is_file():
        raise ReliabilityProtocolCompletenessError(f"Protocol is missing: {path}")
    root = _project_root(path)
    try:
        protocol_name = path.relative_to(root).as_posix()
    except ValueError as error:
        raise ReliabilityProtocolCompletenessError("Protocol escapes the project root") from error
    raw = path.read_bytes()
    payload = _mapping(yaml.safe_load(raw), "Protocol")
    if payload.get("protocol_id") != "run-026-information-clock-reliability-execution-v1":
        raise ReliabilityProtocolCompletenessError("Unexpected protocol identifier")

    gaps = (
        _gap(
            "XG-01",
            "data_matrix",
            "The protocol does not state whether rows are origin snapshots or observation periods.",
            "Different row semantics change histories, ranks, projectors, and labels.",
            "Freeze the exact origin-by-series matrix construction and history windows.",
        ),
        _gap(
            "XG-02",
            "model_scenario_generator.release_lag_policies",
            "The one-calendar-month class-B stress is named but has no executable value/mask rule.",
            "Alternative shifts create different admissible panels and authorization rates.",
            "Define the exact series set, calendar shift, boundary missingness, "
            "and provenance fields.",
        ),
        _gap(
            "XG-03",
            "model_scenario_generator.missingness_policies",
            "Complete-case fitting has no rule for recovering scores on the "
            "required 120 calendar rows.",
            "Dropping rows makes the common-calendar projector undefined or incomparable.",
            "Freeze complete-row fitting and observed-row score recovery with failure conditions.",
        ),
        _gap(
            "XG-04",
            "redundancy_and_channel_balance",
            "The bound method invokes a 0.98 near-duplicate rule, but Run 026 "
            "omits its graph and tie-break execution.",
            "Order-dependent column retention changes channel weights and factor geometry.",
            "Freeze connected-component construction and the complete deterministic "
            "representative tie-break.",
        ),
        _gap(
            "XG-05",
            "geometry_and_authorization.orientation_anchor",
            "The signed eight-channel anchor is not a numerical vector and "
            "unequal-rank state alignment is undefined.",
            "Orientation gates and state-score summaries can change under "
            "arbitrary implementation choices.",
            "Freeze the channel order, anchor vector, rank-invariant scalar "
            "projection, and normalization.",
        ),
        _gap(
            "XG-06",
            "geometry_and_authorization.authorize_only_if",
            "Within-panel quality gates and the role of expanding versus rolling "
            "fits are not enumerated.",
            "The same scenario can be accepted or rejected under multiple defensible readings.",
            "Define each binary gate and which fit pairs enter within-panel and "
            "cross-scenario envelopes.",
        ),
        _gap(
            "XG-07",
            "registered_comparators",
            "B1 and B2 lack calibrated authorization statistics and B3 lacks an "
            "objective, penalty grid, solver, and failure rule.",
            "Primary benchmark loss and matched participation are not reproducible.",
            "Freeze comparator estimands, cutoff grids, calibration losses, "
            "robust-PCA algorithm, and tie-breaks.",
        ),
        _gap(
            "XG-08",
            "negative_controls",
            "Channel-label and source-clock relabeling are algebraic invariances "
            "under the registered distances and deduplication.",
            "These controls cannot diagnose mechanical authorization or supply a pass/fail result.",
            "Reclassify pure relabelings as invariances and register nondegenerate "
            "structure-breaking controls.",
        ),
        _gap(
            "XG-09",
            "negative_control_interpretation",
            "No numerical failure criterion is defined for any negative control.",
            "The success gate can be declared passed or failed after observing results.",
            "Freeze control-specific expected effects and exact rejection or "
            "non-inferiority rules.",
        ),
        _gap(
            "XG-10",
            "inference",
            "Bootstrap seed, edge-block enumeration, zero-variance handling, and "
            "studentization are unspecified.",
            "Intervals are not byte-reproducible and may differ in small samples.",
            "Freeze the deterministic resampling stream and all finite-sample "
            "computational conventions.",
        ),
        _gap(
            "XG-11",
            "execution_firewall",
            "The protocol requires one-time evaluation but does not define lock "
            "artifacts, state transitions, or overwrite refusal.",
            "Calibration choices and evaluation access cannot be independently audited.",
            "Freeze a two-stage state machine with immutable calibration lock, "
            "evaluation marker, and hash chain.",
        ),
    )
    return ProtocolCompletenessAudit(
        audit_id="run-027-run026-executable-completeness-v1",
        protocol_path=protocol_name,
        protocol_sha256=hashlib.sha256(raw).hexdigest(),
        passed=False,
        critical_gap_count=len(gaps),
        result_sensitive_choice_count=len(gaps),
        empirical_fit_performed=False,
        evaluation_results_accessed=False,
        transmission_outcomes_accessed=False,
        gaps=gaps,
    )
