"""Empirical-contract loading and fail-closed readiness checks."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REQUIRED_PATHS: tuple[tuple[str, ...], ...] = (
    ("contract_id",),
    ("status",),
    ("region",),
    ("shock", "primary_component"),
    ("shock", "event_window"),
    ("shock", "normalization"),
    ("outcomes", "primary"),
    ("horizons", "primary"),
    ("estimand", "target"),
    ("evaluation", "development_block"),
    ("evaluation", "calibration_block"),
    ("evaluation", "final_block"),
    ("reliability", "failure_event"),
    ("rights", "redistribution_status"),
)

BLOCKING_TOKENS = ("TBD", "UNRESOLVED", "PENDING")


class ContractError(ValueError):
    """Raised when a contract is malformed."""


@dataclass(frozen=True)
class ContractAudit:
    contract_id: str
    declared_status: str
    blockers: tuple[str, ...]

    @property
    def ready_for_real_estimation(self) -> bool:
        return self.declared_status == "FROZEN" and not self.blockers


def load_contract(path: Path) -> dict[str, Any]:
    """Load a YAML contract and require a mapping at the root."""
    with path.open("r", encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise ContractError("The empirical contract root must be a mapping.")
    return value


def _lookup(mapping: Mapping[str, Any], path: Sequence[str]) -> Any:
    value: Any = mapping
    for key in path:
        if not isinstance(value, Mapping) or key not in value:
            return None
        value = value[key]
    return value


def _walk(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield from _walk(nested, path)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _walk(nested, f"{prefix}[{index}]")
    else:
        yield prefix, value


def _is_blocking(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        normalized = value.strip().upper()
        return not normalized or any(token in normalized for token in BLOCKING_TOKENS)
    if isinstance(value, (list, tuple, dict)):
        return len(value) == 0
    return False


def audit_contract(contract: Mapping[str, Any]) -> ContractAudit:
    """Return explicit blockers; never infer readiness from document presence."""
    blockers: list[str] = []
    for required_path in REQUIRED_PATHS:
        value = _lookup(contract, required_path)
        if _is_blocking(value):
            blockers.append("required:" + ".".join(required_path))

    for field_path, value in _walk(contract):
        if _is_blocking(value) and field_path and f"required:{field_path}" not in blockers:
            blockers.append(f"unresolved:{field_path}")

    contract_id = contract.get("contract_id")
    status = contract.get("status")
    if not isinstance(contract_id, str) or not contract_id.strip():
        raise ContractError("contract_id must be a non-empty string.")
    if status not in {"DRAFT", "BLOCKED", "FROZEN", "RETIRED"}:
        raise ContractError("status must be DRAFT, BLOCKED, FROZEN, or RETIRED.")
    if status == "FROZEN" and blockers:
        blockers.insert(0, "status:FROZEN_WITH_UNRESOLVED_FIELDS")

    return ContractAudit(contract_id, str(status), tuple(sorted(set(blockers))))
