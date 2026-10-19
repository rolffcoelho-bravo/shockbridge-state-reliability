"""Fail-closed preflight for the frozen Run 026 reliability execution.

The preflight verifies provenance, panel structure, and exact analytic clock
equivalence. It deliberately does not import the numerical reliability engine,
fit a state, open the evaluation block, or access transmission outcomes.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml


class ReliabilityExecutionContractError(ValueError):
    """Raised when the Run 026 execution contract is incomplete or changed."""


PANEL_COLUMNS = (
    "panel_id",
    "origin_month",
    "origin_timestamp",
    "series_id",
    "observation_period",
    "usable_timestamp",
    "transformed_value",
    "is_missing",
    "missing_reason",
    "source_response_sha256",
)

ANALYTIC_FIELDS = (
    "origin_month",
    "series_id",
    "observation_period",
    "transformed_value",
    "is_missing",
    "missing_reason",
)

EXPECTED_CLOCK_IDS = {
    "registered_mir_bsi__effective_day_dfr",
    "registered_mir_bsi__next_day_dfr",
    "next_day_mir_bsi__effective_day_dfr",
    "next_day_mir_bsi__next_day_dfr",
}

EXPECTED_PANEL_ROWS = {
    "P0_CORE_REPLAY_AND_FAST": 1918,
    "P1_AUGMENTED_BANK_CREDIT": 2740,
}

EXPECTED_COMPARATORS = {
    "B0_ALWAYS_ABSTAIN",
    "B1_SINGLE_AUGMENTED_PANEL",
    "B2_VINTAGE_PANEL_COMBINATION",
    "B3_ROBUST_PCA",
}


@dataclass(frozen=True)
class ReliabilityExecutionContractAudit:
    """Outcome-sealed Run 026 protocol preflight result."""

    audit_id: str
    protocol_id: str
    protocol_path: str
    protocol_sha256: str
    bound_inputs_verified: int
    source_clock_labels: int
    panel_files_verified: int
    panel_rows_verified: int
    analytic_equivalence_classes: int
    analytic_class_members: tuple[dict[str, object], ...]
    provenance_labeled_scenario_ceiling: int
    unique_analytic_scenario_ceiling: int
    comparator_count: int
    evaluation_labels_matured: bool
    empirical_reliability_fit_performed: bool
    evaluation_results_accessed: bool
    transmission_outcomes_accessed: bool
    synthetic_empirical_observations_used: bool
    passed: bool


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReliabilityExecutionContractError(f"{label} must be a mapping")
    return value


def _list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise ReliabilityExecutionContractError(f"{label} must be a nonempty list")
    return value


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReliabilityExecutionContractError(f"{label} must be a nonempty string")
    return value.strip()


def _positive_int(value: object, label: str) -> int:
    if type(value) is not int or value < 1:
        raise ReliabilityExecutionContractError(f"{label} must be a positive integer")
    return value


def _exact_bool(value: object, expected: bool, label: str) -> None:
    if value is not expected:
        raise ReliabilityExecutionContractError(f"{label} must be {expected}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_root(path: Path) -> Path:
    for candidate in (path.resolve().parent, *path.resolve().parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise ReliabilityExecutionContractError("cannot locate project root containing pyproject.toml")


def _inside(root: Path, relative: str, label: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise ReliabilityExecutionContractError(f"{label} escapes the project root") from error
    return candidate


def _validate_registered_file(root: Path, entry: dict[str, Any], label: str) -> tuple[Path, str]:
    relative = _nonempty(entry.get("path"), f"{label} path")
    expected_bytes = _positive_int(entry.get("bytes"), f"{label} bytes")
    expected_sha = _nonempty(entry.get("sha256"), f"{label} sha256")
    if len(expected_sha) != 64 or any(
        character not in "0123456789abcdef" for character in expected_sha
    ):
        raise ReliabilityExecutionContractError(f"{label} must register an exact SHA-256")
    path = _inside(root, relative, label)
    if not path.is_file():
        raise ReliabilityExecutionContractError(f"{label} is missing: {relative}")
    if path.stat().st_size != expected_bytes or _sha256(path) != expected_sha:
        raise ReliabilityExecutionContractError(f"{label} byte or hash mismatch: {relative}")
    return path, relative


def _month_index(value: object, label: str) -> int:
    text = _nonempty(value, label)
    try:
        parsed = date.fromisoformat(f"{text}-01")
    except ValueError as error:
        raise ReliabilityExecutionContractError(f"{label} must use YYYY-MM") from error
    return parsed.year * 12 + parsed.month - 1


def _analytic_panel_hash(path: Path, panel_id: str, expected_rows: int) -> tuple[str, int]:
    digest = hashlib.sha256()
    keys: set[tuple[str, str]] = set()
    rows = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != PANEL_COLUMNS:
            raise ReliabilityExecutionContractError(f"panel schema mismatch: {path}")
        for row in reader:
            rows += 1
            if row["panel_id"] != panel_id:
                raise ReliabilityExecutionContractError(f"panel_id mismatch: {path}")
            key = (row["origin_month"], row["series_id"])
            if key in keys:
                raise ReliabilityExecutionContractError(f"duplicate panel key: {path}")
            keys.add(key)
            missing = row["is_missing"]
            if missing not in {"0", "1"}:
                raise ReliabilityExecutionContractError(f"invalid missingness flag: {path}")
            value = row["transformed_value"]
            if missing == "0":
                try:
                    numeric = float(value)
                except ValueError as error:
                    raise ReliabilityExecutionContractError(
                        f"observed panel value is not numeric: {path}"
                    ) from error
                if not math.isfinite(numeric):
                    raise ReliabilityExecutionContractError(
                        f"observed panel value is nonfinite: {path}"
                    )
            elif value:
                raise ReliabilityExecutionContractError(
                    f"missing panel row contains a transformed value: {path}"
                )
            for field in ANALYTIC_FIELDS:
                encoded = row[field].encode("utf-8")
                digest.update(len(encoded).to_bytes(8, "big"))
                digest.update(encoded)
    if rows != expected_rows:
        raise ReliabilityExecutionContractError(
            f"panel row count mismatch for {path}: {rows} != {expected_rows}"
        )
    return digest.hexdigest(), rows


def _expected_classes(payload: dict[str, Any]) -> set[tuple[str, frozenset[str]]]:
    contract = _mapping(
        payload.get("analytic_equivalence_contract"), "analytic_equivalence_contract"
    )
    if tuple(contract.get("canonical_fields", ())) != ANALYTIC_FIELDS:
        raise ReliabilityExecutionContractError("analytic canonical fields changed")
    _exact_bool(
        contract.get("clock_labels_as_independent_draws"),
        False,
        "clock_labels_as_independent_draws",
    )
    _exact_bool(
        contract.get("provenance_mapping_retained_in_every_output"),
        True,
        "provenance_mapping_retained_in_every_output",
    )
    if contract.get("multiplicity_weight") != "one_per_exact_analytic_class":
        raise ReliabilityExecutionContractError("analytic multiplicity must be neutralized")
    expected: set[tuple[str, frozenset[str]]] = set()
    for raw in _list(contract.get("expected_classes"), "expected_classes"):
        item = _mapping(raw, "expected analytic class")
        panel_id = _nonempty(item.get("panel_id"), "expected class panel_id")
        members = frozenset(
            _nonempty(value, "expected class member")
            for value in _list(item.get("members"), "expected class members")
        )
        expected.add((panel_id, members))
    declared = _positive_int(
        contract.get("exact_class_count_before_model_scenario_generation"),
        "exact analytic class count",
    )
    if declared != 3 or len(expected) != declared:
        raise ReliabilityExecutionContractError("exact analytic class count must remain three")
    return expected


def audit_reliability_execution_contract(
    protocol_path: Path,
) -> ReliabilityExecutionContractAudit:
    """Validate Run 026 without fitting or exposing evaluation results."""
    protocol_path = protocol_path.resolve()
    root = _project_root(protocol_path)
    payload = _mapping(yaml.safe_load(protocol_path.read_text(encoding="utf-8")), "protocol")
    if payload.get("status") != "APPROVED_AND_FROZEN_BEFORE_EMPIRICAL_RELIABILITY_EXECUTION":
        raise ReliabilityExecutionContractError("protocol must be frozen before execution")
    protocol_id = _nonempty(payload.get("protocol_id"), "protocol_id")
    boundary = _mapping(payload.get("scientific_boundary"), "scientific_boundary")
    required_true = (
        "real_official_data_only",
        "zero_cost_sources_only",
        "preserved_hash_bound_panels_only",
    )
    required_false = (
        "new_network_retrieval_allowed",
        "synthetic_empirical_observations_allowed",
        "software_fixture_values_are_empirical_evidence",
        "empirical_reliability_fit_allowed_during_protocol_freeze",
        "evaluation_results_access_allowed_during_protocol_freeze",
        "transmission_outcomes_access_allowed",
        "transmission_module_import_allowed",
        "high_dimensional_empirical_claim_allowed",
        "methodological_novelty_claim_allowed",
        "monetary_policy_recommendation_allowed",
    )
    for field in required_true:
        _exact_bool(boundary.get(field), True, field)
    for field in required_false:
        _exact_bool(boundary.get(field), False, field)

    seen_bound: set[str] = set()
    for index, raw in enumerate(_list(payload.get("bound_inputs"), "bound_inputs")):
        item = _mapping(raw, f"bound input {index}")
        _, relative = _validate_registered_file(root, item, f"bound input {index}")
        if relative in seen_bound:
            raise ReliabilityExecutionContractError(f"duplicate bound input: {relative}")
        seen_bound.add(relative)

    source = _mapping(payload.get("source_clock_inputs"), "source_clock_inputs")
    if _positive_int(source.get("expected_source_clock_labels"), "source clock labels") != 4:
        raise ReliabilityExecutionContractError("source clock label count must remain four")
    if _positive_int(source.get("expected_panel_files"), "panel files") != 8:
        raise ReliabilityExecutionContractError("panel file count must remain eight")
    if _positive_int(source.get("expected_total_rows"), "total rows") != 18632:
        raise ReliabilityExecutionContractError("registered total rows must remain 18632")

    clock_ids: set[str] = set()
    paths: set[str] = set()
    analytic_groups: dict[tuple[str, str], list[str]] = {}
    panel_rows = 0
    panel_files = 0
    for raw_scenario in _list(source.get("scenarios"), "source clock scenarios"):
        scenario = _mapping(raw_scenario, "source clock scenario")
        scenario_id = _nonempty(scenario.get("scenario_id"), "source clock scenario_id")
        if scenario_id in clock_ids:
            raise ReliabilityExecutionContractError("source clock identifiers must be unique")
        clock_ids.add(scenario_id)
        panels = _list(scenario.get("panels"), f"{scenario_id} panels")
        if len(panels) != 2:
            raise ReliabilityExecutionContractError(
                f"{scenario_id} must contain exactly two panels"
            )
        scenario_panels: set[str] = set()
        for raw_panel in panels:
            panel = _mapping(raw_panel, f"{scenario_id} panel")
            panel_id = _nonempty(panel.get("panel_id"), "panel_id")
            if panel_id not in EXPECTED_PANEL_ROWS or panel_id in scenario_panels:
                raise ReliabilityExecutionContractError(
                    f"{scenario_id} has an unknown or duplicate panel"
                )
            scenario_panels.add(panel_id)
            expected_rows = _positive_int(panel.get("rows"), f"{scenario_id} rows")
            if expected_rows != EXPECTED_PANEL_ROWS[panel_id]:
                raise ReliabilityExecutionContractError(
                    f"{scenario_id} registered row count changed"
                )
            path, relative = _validate_registered_file(root, panel, f"{scenario_id} {panel_id}")
            if relative in paths:
                raise ReliabilityExecutionContractError("panel paths must be unique")
            paths.add(relative)
            analytic_hash, rows = _analytic_panel_hash(path, panel_id, expected_rows)
            analytic_groups.setdefault((panel_id, analytic_hash), []).append(scenario_id)
            panel_rows += rows
            panel_files += 1
    if clock_ids != EXPECTED_CLOCK_IDS:
        raise ReliabilityExecutionContractError("the four source clock labels changed")
    if panel_files != 8 or panel_rows != 18632:
        raise ReliabilityExecutionContractError("verified panel totals changed")

    observed_classes = {
        (panel_id, frozenset(members)) for (panel_id, _), members in analytic_groups.items()
    }
    if observed_classes != _expected_classes(payload):
        raise ReliabilityExecutionContractError(
            "the eight panel files do not match the three frozen analytic classes"
        )

    generator = _mapping(payload.get("model_scenario_generator"), "model_scenario_generator")
    provenance_ceiling = _positive_int(
        generator.get("provenance_labeled_ceiling_before_deduplication"),
        "provenance scenario ceiling",
    )
    analytic_ceiling = _positive_int(
        generator.get("unique_analytic_ceiling_after_input_clock_deduplication"),
        "analytic scenario ceiling",
    )
    if provenance_ceiling != 224 or analytic_ceiling != 88:
        raise ReliabilityExecutionContractError("scenario ceilings must remain 224 and 88")
    if generator.get("release_lag_policies") != [
        "observed_registered_source_clock",
        "run021_class_B_plus_one_calendar_month_stress",
    ]:
        raise ReliabilityExecutionContractError("the Run 021 slow-release stress was dropped")

    calendar = _mapping(payload.get("execution_clock_and_calendar"), "execution_clock_and_calendar")
    evaluation_end = _month_index(calendar.get("evaluation_end"), "evaluation_end")
    tail_end = _month_index(calendar.get("diagnostic_tail_end"), "diagnostic_tail_end")
    horizon = _positive_int(calendar.get("future_failure_horizon_months"), "future failure horizon")
    matured = evaluation_end + horizon <= tail_end
    if not matured or calendar.get("every_evaluation_label_matured") is not True:
        raise ReliabilityExecutionContractError("every evaluation label must be matured")
    _exact_bool(calendar.get("evaluation_once_only"), True, "evaluation_once_only")
    _exact_bool(
        calendar.get("transmission_outcomes_remain_sealed"),
        True,
        "transmission_outcomes_remain_sealed",
    )

    comparators = {
        _nonempty(_mapping(raw, "comparator").get("id"), "comparator id")
        for raw in _list(payload.get("registered_comparators"), "registered_comparators")
    }
    if comparators != EXPECTED_COMPARATORS:
        raise ReliabilityExecutionContractError("registered comparator set changed")

    authorization = _mapping(
        payload.get("geometry_and_authorization"), "geometry_and_authorization"
    )
    _exact_bool(
        authorization.get("provenance_duplicates_may_satisfy_two_scenario_rule"),
        False,
        "provenance_duplicates_may_satisfy_two_scenario_rule",
    )
    inference = _mapping(payload.get("inference"), "inference")
    _exact_bool(
        inference.get("resample_source_clock_labels"),
        False,
        "resample_source_clock_labels",
    )

    class_records: tuple[dict[str, object], ...] = tuple(
        {
            "panel_id": panel_id,
            "member_ids": sorted(members),
            "analytic_sha256": analytic_hash,
        }
        for (panel_id, analytic_hash), members in sorted(
            analytic_groups.items(), key=lambda item: (item[0][0], sorted(item[1]))
        )
    )
    return ReliabilityExecutionContractAudit(
        audit_id="run-026-protocol-preflight-v1",
        protocol_id=protocol_id,
        protocol_path=str(protocol_path.relative_to(root)),
        protocol_sha256=_sha256(protocol_path),
        bound_inputs_verified=len(seen_bound),
        source_clock_labels=len(clock_ids),
        panel_files_verified=panel_files,
        panel_rows_verified=panel_rows,
        analytic_equivalence_classes=len(analytic_groups),
        analytic_class_members=class_records,
        provenance_labeled_scenario_ceiling=provenance_ceiling,
        unique_analytic_scenario_ceiling=analytic_ceiling,
        comparator_count=len(comparators),
        evaluation_labels_matured=matured,
        empirical_reliability_fit_performed=False,
        evaluation_results_accessed=False,
        transmission_outcomes_accessed=False,
        synthetic_empirical_observations_used=False,
        passed=True,
    )


def write_reliability_execution_contract_audit(
    audit: ReliabilityExecutionContractAudit, output_path: Path
) -> None:
    """Write an immutable JSON preflight record through an atomic rename."""
    if output_path.exists():
        raise ReliabilityExecutionContractError(f"refusing to overwrite {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", suffix=".part", dir=output_path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(asdict(audit), handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output_path)
    finally:
        if temporary.exists():
            temporary.unlink()
