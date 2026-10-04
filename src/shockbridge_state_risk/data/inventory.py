"""Fail-closed verification for locally retained research artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from shockbridge_state_risk.data.download import sha256_file


class InventoryError(ValueError):
    """Raised when an artifact inventory is malformed or escapes its root."""


@dataclass(frozen=True)
class InventoryAudit:
    inventory_id: str
    canonical_root: str
    registered_artifacts: int
    verified_artifacts: int
    failures: tuple[str, ...]
    passed: bool


def _mapping(value: object, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InventoryError(f"{context} must be a mapping.")
    return value


def verify_inventory(path: Path) -> InventoryAudit:
    payload = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "inventory")
    try:
        inventory_id = str(payload["inventory_id"])
        root_value = Path(str(payload["canonical_root"]))
        root = (
            root_value.resolve()
            if root_value.is_absolute()
            else (path.parent / root_value).resolve()
        )
        artifacts = payload["artifacts"]
    except KeyError as exc:
        raise InventoryError(f"Inventory is missing {exc.args[0]!r}.") from exc
    if not isinstance(artifacts, list):
        raise InventoryError("artifacts must be a list.")

    failures: list[str] = []
    verified = 0
    seen: set[Path] = set()
    for index, raw_record in enumerate(artifacts):
        record = _mapping(raw_record, f"artifacts[{index}]")
        try:
            relative = Path(str(record["path"]))
            expected_bytes = int(record["bytes"])
            expected_hash = str(record["sha256"]).lower()
        except KeyError as exc:
            raise InventoryError(f"artifacts[{index}] is missing {exc.args[0]!r}.") from exc
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise InventoryError(f"Artifact path escapes canonical root: {relative}") from exc
        if candidate in seen:
            raise InventoryError(f"Duplicate artifact path: {relative}")
        seen.add(candidate)
        if not candidate.is_file():
            failures.append(f"missing:{relative}")
            continue
        observed_bytes = candidate.stat().st_size
        if observed_bytes != expected_bytes:
            failures.append(f"size:{relative}:expected={expected_bytes}:observed={observed_bytes}")
            continue
        observed_hash = sha256_file(candidate)
        if observed_hash.lower() != expected_hash:
            failures.append(f"sha256:{relative}:expected={expected_hash}:observed={observed_hash}")
            continue
        verified += 1
    return InventoryAudit(
        inventory_id=inventory_id,
        canonical_root=str(root),
        registered_artifacts=len(artifacts),
        verified_artifacts=verified,
        failures=tuple(failures),
        passed=not failures,
    )
