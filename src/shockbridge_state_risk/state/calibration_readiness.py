"""Value-free Stage-A orchestration-readiness audit.

Run 028 verified isolated numerical primitives.  This module asks the separate
question required before an official calibration fit: do the frozen protocol,
approved amendment, and harness uniquely determine their end-to-end
composition?  It reads only methodology and source-code bytes.  It does not
load panel values, labels, evaluation results, or transmission outcomes.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


class CalibrationReadinessError(ValueError):
    """Raised when the readiness audit cannot verify its frozen inputs."""


@dataclass(frozen=True)
class OrchestrationGap:
    gap_id: str
    severity: str
    location: str
    issue: str
    empirical_consequence: str
    required_resolution: str


@dataclass(frozen=True)
class CalibrationReadinessAudit:
    audit_id: str
    passed: bool
    stage_A_owner_approval_recorded: bool
    primitive_implementation_gate_passed: bool
    critical_result_choice_count: int
    critical_auditability_gap_count: int
    official_panel_value_loaded_into_estimator: bool
    calibration_fit_performed: bool
    evaluation_results_accessed: bool
    transmission_outcomes_accessed: bool
    inspected_paths: tuple[str, ...]
    input_sha256: dict[str, str]
    gaps: tuple[OrchestrationGap, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CalibrationReadinessError(f"{label} must be a mapping")
    return value


def _project_root(path: Path) -> Path:
    for candidate in (path.parent, *path.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate.resolve()
    raise CalibrationReadinessError("Cannot locate project root")


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError as error:
        raise CalibrationReadinessError("Readiness input escapes the project root") from error


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise CalibrationReadinessError(f"Readiness input is missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _gap(
    gap_id: str,
    location: str,
    issue: str,
    consequence: str,
    resolution: str,
    *,
    severity: str = "CRITICAL_STOP_BEFORE_OFFICIAL_CALIBRATION",
) -> OrchestrationGap:
    return OrchestrationGap(gap_id, severity, location, issue, consequence, resolution)


def audit_calibration_readiness(
    protocol_path: Path,
    amendment_path: Path,
    approval_path: Path,
    harness_path: Path,
    stage_A_approval_path: Path,
) -> CalibrationReadinessAudit:
    """Audit whether the approved primitives uniquely compose into Stage A."""
    root = _project_root(protocol_path.resolve())
    paths = tuple(
        path.resolve()
        for path in (
            protocol_path,
            amendment_path,
            approval_path,
            harness_path,
            stage_A_approval_path,
        )
    )
    relative = tuple(_relative(root, path) for path in paths)
    if any(name.startswith(("data/", "private/")) for name in relative):
        raise CalibrationReadinessError("Value-free audit cannot inspect empirical data paths")

    protocol = _mapping(yaml.safe_load(paths[0].read_bytes()), "Run 026 protocol")
    amendment = _mapping(yaml.safe_load(paths[1].read_bytes()), "Run 027 amendment")
    approval = _mapping(yaml.safe_load(paths[2].read_bytes()), "Run 028 approval")
    stage_A_approval = _mapping(yaml.safe_load(paths[4].read_bytes()), "Stage-A approval")
    if protocol.get("protocol_id") != "run-026-information-clock-reliability-execution-v1":
        raise CalibrationReadinessError("Unexpected Run 026 protocol identifier")
    if amendment.get("proposal_id") != "run-027-reliability-execution-amendment-proposal-v1":
        raise CalibrationReadinessError("Unexpected Run 027 amendment identifier")
    if approval.get("status") != "APPROVED_FOR_IMPLEMENTATION_AND_HOSTILE_SOFTWARE_TESTS_ONLY":
        raise CalibrationReadinessError("Run 028 primitive approval is not valid")
    expected_stage_A_status = "OWNER_APPROVED_STAGE_A_CALIBRATION_SUBJECT_TO_READINESS_GATE"
    if stage_A_approval.get("status") != expected_stage_A_status:
        raise CalibrationReadinessError("Stage-A owner approval is not recorded")

    amendment_hash = _sha256(paths[1])
    approved_amendment = _mapping(approval.get("approved_amendment"), "Approved amendment")
    if approved_amendment.get("sha256") != amendment_hash:
        raise CalibrationReadinessError("Run 028 approval no longer binds the amendment bytes")
    stage_bound = _mapping(stage_A_approval.get("bound_implementation"), "Stage-A implementation")
    if stage_bound.get("run_027_amendment_sha256") != amendment_hash:
        raise CalibrationReadinessError("Stage-A approval does not bind the approved amendment")
    if stage_bound.get("run_028_harness_sha256") != _sha256(paths[3]):
        raise CalibrationReadinessError("Stage-A approval does not bind the Run 028 harness")

    gaps = (
        _gap(
            "OG-01",
            "history-specific eligibility and scenario_history_key",
            "The approved text does not say whether expanding and rolling histories "
            "select retained series independently, and the key hashes matrices without "
            "ordered series IDs.",
            "Different retained columns change ranks and geometry; different series sets can share "
            "the same value hash and provenance identity.",
            "Freeze history-specific selection and bind ordered series IDs, masks, and "
            "matrices for both histories into every scenario identity.",
        ),
        _gap(
            "OG-02",
            "scenario generator orchestration",
            "No executable ordering composes timing stress, family deletion, history slicing, "
            "coverage filtering, exact deduplication, standardization, near-duplicate resolution, "
            "channel reweighting, scenario deduplication, and provenance aggregation.",
            "All operations are individually defensible but do not commute, so alternative orders "
            "can change admissible scenarios and authorization.",
            "Freeze a single ordered pipeline, scenario-ID grammar, representative rule, and "
            "many-to-one provenance map before fitting.",
        ),
        _gap(
            "OG-03",
            "redundancy metadata materialization",
            "The harness expects numeric timing strength, revision exposure, and "
            "first-usable origin, but the frozen manifest supplies categorical strings "
            "and YYYY-MM values; exact-duplicate collapse is declared but not implemented "
            "by the redundancy primitive.",
            "Unregistered ordinal encodings or skipped exact collapse can select a "
            "different series.",
            "Freeze categorical rank maps and month encoding, execute exact value-and-missingness "
            "collapse first, and apply one deterministic representative rule to both "
            "duplicate stages.",
        ),
        _gap(
            "OG-04",
            "B2 vintage-panel combination",
            "The amendment names an equal-weight scalar score and a three-dimensional "
            "geometry grid but does not define the B2 score projector, channel operator, "
            "or anchor statistic.",
            "B2 authorization and matched participation cannot be reproduced and "
            "benchmark loss can change under multiple plausible constructions.",
            "Define the expanding and rolling combined scalar, duplicate-neutral channel operator, "
            "anchor summary, and exact three gate statistics.",
        ),
        _gap(
            "OG-05",
            "B3 observed-entry robust PCA",
            "The current SVD update inserts zero at unobserved cells, while the registered "
            "objective penalizes residuals only on observed cells; missing-cell "
            "continuation and downstream geometry construction are not frozen.",
            "Zero-filling changes the convex problem, low-rank recovery, selected rank, "
            "and B3 loss.",
            "Freeze a projected observed-entry iteration, initialization, missing-cell "
            "continuation, post-recovery rank/channel geometry, and convergence identity.",
        ),
        _gap(
            "OG-06",
            "negative-control staging",
            "The calibration-stage rule asks whether NC1/NC2 satisfy every primary "
            "success condition, but those conditions include sealed evaluation metrics.",
            "The control gate either leaks evaluation results or remains impossible to evaluate at "
            "the calibration lock.",
            "Define calibration-only analogues for Stage A, freeze control settings "
            "there, and reserve the unchanged evaluation control assessment for Stage B.",
        ),
        _gap(
            "OG-07",
            "evaluation input-only identity hashes",
            "Stage A permits evaluation scenario identities but does not define hash payload, "
            "cardinality, coordinate order, or allowed preprocessing.",
            "An implementation can omit identity-changing inputs or inadvertently serialize sealed "
            "metrics while still producing valid-looking hashes.",
            "Freeze a per-origin/per-scenario canonical identity over coordinates, "
            "retained series, masks, matrix hashes, provenance mapping, and a no-metric "
            "serialization boundary.",
            severity="CRITICAL_AUDITABILITY_STOP_BEFORE_OFFICIAL_CALIBRATION",
        ),
        _gap(
            "OG-08",
            "immutable calibration-lock schema",
            "The lock writer accepts unrestricted settings, metrics, and invariance "
            "mappings and an unvalidated implementation string.",
            "A partial lock can pass its body hash while omitting a threshold, comparator, "
            "control, origin count, failure reason, or exact code identity.",
            "Freeze required keys and types, full commit/source hashes, origin counts, "
            "comparator and control settings, and schema validation before atomic creation.",
            severity="CRITICAL_AUDITABILITY_STOP_BEFORE_OFFICIAL_CALIBRATION",
        ),
        _gap(
            "OG-09",
            "calibration origin ledger and label materialization",
            "No immutable row schema records scenario failures, representatives, authorization, "
            "matured reference labels, candidate losses, and exclusions at each "
            "calibration origin.",
            "Aggregate metrics cannot reveal silent origin loss, failed-fit handling, or "
            "label/decision misalignment.",
            "Freeze a complete 60-origin ledger, require matured labels through the "
            "embargo, and hash the ledger into the Stage-A lock.",
            severity="CRITICAL_AUDITABILITY_STOP_BEFORE_OFFICIAL_CALIBRATION",
        ),
    )
    hashes = {name: _sha256(path) for name, path in zip(relative, paths)}
    return CalibrationReadinessAudit(
        audit_id="run-029-stage-A-orchestration-readiness-v1",
        passed=False,
        stage_A_owner_approval_recorded=True,
        primitive_implementation_gate_passed=True,
        critical_result_choice_count=6,
        critical_auditability_gap_count=3,
        official_panel_value_loaded_into_estimator=False,
        calibration_fit_performed=False,
        evaluation_results_accessed=False,
        transmission_outcomes_accessed=False,
        inspected_paths=relative,
        input_sha256=hashes,
        gaps=gaps,
    )
