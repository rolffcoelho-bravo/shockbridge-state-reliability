"""Fail-closed validation for the Run 019 source-feasibility registry."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml


class SourceFeasibilityError(ValueError):
    """Raised when a source registry or channel architecture violates its contract."""


REQUIRED_COLUMNS = (
    "source_row_id",
    "institution",
    "dataset_scope",
    "economic_channels",
    "frequency",
    "zero_cost",
    "machine_access",
    "stable_identifiers",
    "history_or_release_evidence",
    "revision_risk",
    "retrieval_rights",
    "redistribution_rights",
    "eligibility",
    "proposed_role",
    "primary_locator",
    "rights_locator",
    "decision_note",
)

ELIGIBILITY_CLASSES = {
    "A_REPLAY_ELIGIBLE",
    "B_RELEASE_LAG_ELIGIBLE",
    "C_BUILD_FORWARD_ONLY",
    "D_INELIGIBLE",
}

OFFICIAL_HOST_SUFFIXES = (
    "bis.org",
    "ec.europa.eu",
    "ecb.europa.eu",
    "europa.eu",
)

REQUIRED_CHANNELS = {
    "prices_and_expectations",
    "real_activity_and_labour",
    "policy_stance_and_money_market",
    "sovereign_curve_and_term_structure",
    "bank_funding_and_lending_rates",
    "credit_and_money_quantities",
    "financial_conditions_and_systemic_stress",
    "external_value_and_cross_border_conditions",
}


@dataclass(frozen=True)
class SourceFeasibilityAudit:
    """Deterministic validation summary."""

    source_rows: int
    eligibility_counts: dict[str, int]
    architecture_tiers: int
    required_channels: int
    empirical_observations_retrieved: bool
    transmission_outcomes_accessed: bool


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SourceFeasibilityError(f"{label} must be a nonempty string")
    return value.strip()


def _require_official_https(value: object, label: str) -> None:
    url = _require_string(value, label)
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not parsed.path:
        raise SourceFeasibilityError(f"{label} must be a non-root HTTPS URL")
    if not any(host == suffix or host.endswith(f".{suffix}") for suffix in OFFICIAL_HOST_SUFFIXES):
        raise SourceFeasibilityError(f"{label} does not use an approved official host: {host}")


def load_and_validate_source_matrix(path: Path) -> list[dict[str, str]]:
    """Load and validate the frozen source-feasibility CSV."""

    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != REQUIRED_COLUMNS:
            raise SourceFeasibilityError("source matrix columns do not match the frozen schema")
        rows = list(reader)

    if not rows:
        raise SourceFeasibilityError("source matrix must contain at least one row")

    seen: set[str] = set()
    for index, row in enumerate(rows, start=2):
        for column in REQUIRED_COLUMNS:
            _require_string(row.get(column), f"row {index} {column}")
        source_id = row["source_row_id"]
        if source_id in seen:
            raise SourceFeasibilityError(f"duplicate source_row_id: {source_id}")
        seen.add(source_id)
        if row["zero_cost"] != "YES":
            raise SourceFeasibilityError(f"{source_id} is not zero-cost")
        if row["stable_identifiers"] != "YES":
            raise SourceFeasibilityError(f"{source_id} lacks stable identifiers")
        if row["eligibility"] not in ELIGIBILITY_CLASSES:
            raise SourceFeasibilityError(f"{source_id} has unknown eligibility class")
        _require_official_https(row["primary_locator"], f"{source_id} primary_locator")
        _require_official_https(row["rights_locator"], f"{source_id} rights_locator")
        if row["retrieval_rights"] == row["redistribution_rights"]:
            raise SourceFeasibilityError(
                f"{source_id} must record retrieval and redistribution rights separately"
            )
    return rows


def _load_mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SourceFeasibilityError("channel architecture must be a YAML mapping")
    return payload


def validate_channel_architecture(path: Path, source_ids: set[str]) -> dict[str, Any]:
    """Validate source references and the outcome-blind architecture boundary."""

    payload = _load_mapping(path)
    if payload.get("empirical_observations_retrieved") is not False:
        raise SourceFeasibilityError("architecture must record no observation retrieval")
    if payload.get("transmission_outcomes_accessed") is not False:
        raise SourceFeasibilityError("architecture must record no outcome access")

    tiers = payload.get("tiers")
    if not isinstance(tiers, list) or not tiers:
        raise SourceFeasibilityError("architecture must contain at least one tier")
    referenced: list[str] = []
    tier_ids: set[str] = set()
    for index, tier in enumerate(tiers):
        if not isinstance(tier, dict):
            raise SourceFeasibilityError(f"tier {index} must be a mapping")
        tier_id = _require_string(tier.get("tier_id"), f"tier {index} tier_id")
        if tier_id in tier_ids:
            raise SourceFeasibilityError(f"duplicate tier_id: {tier_id}")
        tier_ids.add(tier_id)
        refs = tier.get("source_rows")
        if not isinstance(refs, list) or not refs:
            raise SourceFeasibilityError(f"{tier_id} must reference source rows")
        for ref in refs:
            referenced.append(_require_string(ref, f"{tier_id} source_rows"))

    unknown = sorted(set(referenced) - source_ids)
    missing = sorted(source_ids - set(referenced))
    if unknown or missing:
        raise SourceFeasibilityError(
            f"architecture/source mismatch; unknown={unknown!r}, missing={missing!r}"
        )
    if len(referenced) != len(set(referenced)):
        raise SourceFeasibilityError("a source row may belong to only one architecture tier")

    channels = payload.get("required_channel_families")
    if not isinstance(channels, list) or set(channels) != REQUIRED_CHANNELS:
        raise SourceFeasibilityError("required monetary-policy channels are incomplete or changed")

    stages = payload.get("staged_execution")
    if not isinstance(stages, list) or [stage.get("stage") for stage in stages] != [1, 2, 3, 4]:
        raise SourceFeasibilityError("execution stages must be ordered exactly 1 through 4")
    return payload


def audit_source_feasibility(matrix_path: Path, architecture_path: Path) -> SourceFeasibilityAudit:
    """Validate both Run 019 records and return a stable summary."""

    rows = load_and_validate_source_matrix(matrix_path)
    architecture = validate_channel_architecture(
        architecture_path, {row["source_row_id"] for row in rows}
    )
    counts = {eligibility: 0 for eligibility in sorted(ELIGIBILITY_CLASSES)}
    for row in rows:
        counts[row["eligibility"]] += 1
    tiers = architecture["tiers"]
    channels = architecture["required_channel_families"]
    assert isinstance(tiers, list)
    assert isinstance(channels, list)
    return SourceFeasibilityAudit(
        source_rows=len(rows),
        eligibility_counts=counts,
        architecture_tiers=len(tiers),
        required_channels=len(channels),
        empirical_observations_retrieved=False,
        transmission_outcomes_accessed=False,
    )
