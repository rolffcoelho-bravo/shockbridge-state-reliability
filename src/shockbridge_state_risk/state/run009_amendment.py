"""Audited right-censoring amendment for immutable Run 009 v1 episodes."""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
import yaml

from shockbridge_state_risk.data.download import sha256_file
from shockbridge_state_risk.state.instability import detect_breach_episodes
from shockbridge_state_risk.state.run009 import EpisodeRule


class Run009AmendmentError(ValueError):
    """Raised when the Run 009 amendment cannot preserve the original evidence."""


@dataclass(frozen=True)
class Run009AmendmentConfig:
    config_sha256: str
    amendment_id: str
    evidence_status: str
    approved_protocol_path: Path
    approved_protocol_sha256: str
    source_manifest_path: Path
    source_manifest_sha256: str
    diagnostic_path: Path
    diagnostic_sha256: str
    original_episode_path: Path
    original_episode_sha256: str
    source_audit_path: Path
    source_audit_sha256: str
    common_origin_start: str
    common_origin_end: str
    episode_rules: tuple[EpisodeRule, ...]
    outcomes_accessed: bool
    amendment_execution_authorized: bool
    transmission_outcome_execution_authorized: bool


@dataclass(frozen=True)
class AmendedEpisodeRow:
    panel_variant: str
    omitted_feature: Optional[str]
    rolling_months: int
    minimum_consecutive_breaches: int
    recovery_consecutive_stable: int
    primary_rule: bool
    episode_number: int
    start_month: str
    end_month: str
    duration_months: int
    breach_months: int
    open_at_sample_end: bool


@dataclass(frozen=True)
class Run009AmendmentResult:
    episode_rows: tuple[AmendedEpisodeRow, ...]
    audit: Mapping[str, Any]


def _mapping(value: object, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise Run009AmendmentError(f"{context} must be a mapping.")
    return value


def _sequence(value: object, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise Run009AmendmentError(f"{context} must be a list.")
    return value


def _boolean(value: object, context: str) -> bool:
    if not isinstance(value, bool):
        raise Run009AmendmentError(f"{context} must be Boolean.")
    return value


def _integer(value: object, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise Run009AmendmentError(f"{context} must be an integer.")
    return value


def _exact_fields(payload: Mapping[str, Any], expected: set[str], context: str) -> None:
    if set(payload) != expected:
        missing = sorted(expected - payload.keys())
        unexpected = sorted(payload.keys() - expected)
        raise Run009AmendmentError(
            f"{context} fields differ from the frozen amendment: {missing=}, {unexpected=}."
        )


def _validate_config(config: Run009AmendmentConfig) -> None:
    if (
        config.outcomes_accessed
        or not config.amendment_execution_authorized
        or config.transmission_outcome_execution_authorized
    ):
        raise Run009AmendmentError("The amendment must remain authorized and outcome blind.")
    expected_rules = {(3, 3, True), (1, 1, False), (6, 6, False)}
    actual_rules = {
        (
            rule.minimum_consecutive_breaches,
            rule.recovery_consecutive_stable,
            rule.primary,
        )
        for rule in config.episode_rules
    }
    if len(config.episode_rules) != 3 or actual_rules != expected_rules:
        raise Run009AmendmentError("Episode rules differ from immutable Run 009 v1.")
    if config.evidence_status != "REAL_DATA_OUTCOME_BLIND_AMENDMENT":
        return
    expected = (
        config.amendment_id == "state-instability-run009-v1-amendment-1",
        config.approved_protocol_sha256
        == "028e3393d24fd235fe09178b913f108364adae501561580e471f2c0d727af581",
        config.source_manifest_sha256
        == "9ff27f2b27d2de008be2ffce09d2c551680679f00ac102ed4de1ca9d8889c9aa",
        config.diagnostic_sha256
        == "c177cfac7fe553d48ada0509d95d665c9c424aa93d339fa3a96ae69bb6553af4",
        config.original_episode_sha256
        == "baed3f89be85284c9162ce681480bbac89d793ee53469a9627d882609b6c6d3b",
        config.source_audit_sha256
        == "0ee8a3b3637e4c45d83edeb7c08412d646e9f099698b925713b38f7fd6430301",
        config.common_origin_start == "month-2014-02",
        config.common_origin_end == "month-2025-10",
    )
    if not all(expected):
        raise Run009AmendmentError("Settings differ from the approved empirical amendment.")


def _validate_source_bundle(config: Run009AmendmentConfig) -> None:
    manifest = _mapping(
        yaml.safe_load(config.source_manifest_path.read_text(encoding="utf-8")),
        "Run 009 source manifest",
    )
    outputs = _mapping(manifest.get("outputs"), "Run 009 source outputs")
    diagnostics = _mapping(outputs.get("diagnostics"), "Run 009 diagnostic output")
    episodes = _mapping(outputs.get("episodes"), "Run 009 episode output")
    audit = _mapping(outputs.get("audit"), "Run 009 audit output")
    decision = _mapping(manifest.get("decision"), "Run 009 source decision")
    if (
        manifest.get("artifact_id") != "state-instability-run009-v1"
        or diagnostics.get("sha256") != config.diagnostic_sha256
        or episodes.get("sha256") != config.original_episode_sha256
        or audit.get("sha256") != config.source_audit_sha256
        or decision.get("state_selected") is not False
        or decision.get("transmission_estimation_authorized") is not False
    ):
        raise Run009AmendmentError("The Run 009 source bundle is not the immutable v1 result.")
    source_audit = _mapping(
        json.loads(config.source_audit_path.read_text(encoding="utf-8")),
        "Run 009 source audit",
    )
    expected_episode_rows = (
        44 if config.evidence_status == "REAL_DATA_OUTCOME_BLIND_AMENDMENT" else None
    )
    if (
        source_audit.get("outcomes_accessed") is not False
        or (
            expected_episode_rows is not None
            and source_audit.get("episode_rows") != expected_episode_rows
        )
        or not isinstance(source_audit.get("episode_rows"), int)
        or int(source_audit["episode_rows"]) < 1
        or source_audit.get("transmission_estimation_authorized") is not False
    ):
        raise Run009AmendmentError("The Run 009 source audit violates the amendment boundary.")


def load_run009_amendment_config(path: Path) -> Run009AmendmentConfig:
    """Load the hash-bound Run 009 episode amendment contract."""
    payload = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "amendment config")
    fields = {
        "schema_version",
        "amendment_id",
        "evidence_status",
        "approved_protocol_path",
        "approved_protocol_sha256",
        "source_manifest_path",
        "source_manifest_sha256",
        "diagnostic_path",
        "diagnostic_sha256",
        "original_episode_path",
        "original_episode_sha256",
        "source_audit_path",
        "source_audit_sha256",
        "common_origin_start",
        "common_origin_end",
        "episode_rules",
        "outcomes_accessed",
        "amendment_execution_authorized",
        "transmission_outcome_execution_authorized",
    }
    _exact_fields(payload, fields, "amendment config")
    paths = {
        "approved_protocol": Path(str(payload["approved_protocol_path"])),
        "source_manifest": Path(str(payload["source_manifest_path"])),
        "diagnostic": Path(str(payload["diagnostic_path"])),
        "original_episode": Path(str(payload["original_episode_path"])),
        "source_audit": Path(str(payload["source_audit_path"])),
    }
    for name, candidate in paths.items():
        expected = str(payload[f"{name}_sha256"])
        if not candidate.is_file() or sha256_file(candidate) != expected:
            raise Run009AmendmentError(f"The amendment {name} file is missing or changed.")
    protocol = _mapping(
        yaml.safe_load(paths["approved_protocol"].read_text(encoding="utf-8")),
        "approved amendment protocol",
    )
    if (
        protocol.get("status") != "APPROVED_AND_FROZEN_FOR_OUTCOME_BLIND_AMENDMENT"
        or protocol.get("outcomes_accessed") is not False
        or protocol.get("amendment_execution_authorized") is not True
        or protocol.get("transmission_outcome_execution_authorized") is not False
    ):
        raise Run009AmendmentError("The amendment protocol is not authorized and outcome blind.")
    try:
        rules = []
        for item in _sequence(payload["episode_rules"], "episode_rules"):
            rule = _mapping(item, "episode rule")
            _exact_fields(rule, set(EpisodeRule.__dataclass_fields__), "episode rule")
            rules.append(
                EpisodeRule(
                    _integer(
                        rule["minimum_consecutive_breaches"],
                        "minimum_consecutive_breaches",
                    ),
                    _integer(
                        rule["recovery_consecutive_stable"],
                        "recovery_consecutive_stable",
                    ),
                    _boolean(rule["primary"], "primary"),
                )
            )
        config = Run009AmendmentConfig(
            config_sha256=sha256_file(path),
            amendment_id=str(payload["amendment_id"]),
            evidence_status=str(payload["evidence_status"]),
            approved_protocol_path=paths["approved_protocol"],
            approved_protocol_sha256=str(payload["approved_protocol_sha256"]),
            source_manifest_path=paths["source_manifest"],
            source_manifest_sha256=str(payload["source_manifest_sha256"]),
            diagnostic_path=paths["diagnostic"],
            diagnostic_sha256=str(payload["diagnostic_sha256"]),
            original_episode_path=paths["original_episode"],
            original_episode_sha256=str(payload["original_episode_sha256"]),
            source_audit_path=paths["source_audit"],
            source_audit_sha256=str(payload["source_audit_sha256"]),
            common_origin_start=str(payload["common_origin_start"]),
            common_origin_end=str(payload["common_origin_end"]),
            episode_rules=tuple(rules),
            outcomes_accessed=_boolean(payload["outcomes_accessed"], "outcomes_accessed"),
            amendment_execution_authorized=_boolean(
                payload["amendment_execution_authorized"], "amendment_execution_authorized"
            ),
            transmission_outcome_execution_authorized=_boolean(
                payload["transmission_outcome_execution_authorized"],
                "transmission_outcome_execution_authorized",
            ),
        )
    except (TypeError, ValueError) as error:
        if isinstance(error, Run009AmendmentError):
            raise
        raise Run009AmendmentError(f"Invalid amendment setting: {error}") from error
    if payload["schema_version"] != 1:
        raise Run009AmendmentError("Amendment schema version is not frozen version 1.")
    _validate_config(config)
    _validate_source_bundle(config)
    return config


def _read_diagnostics(
    config: Run009AmendmentConfig,
) -> tuple[tuple[tuple[str, int], ...], dict[tuple[str, int], tuple[tuple[str, bool], ...]]]:
    groups: dict[tuple[str, int], list[tuple[str, bool]]] = {}
    order: list[tuple[str, int]] = []
    with config.diagnostic_path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row.get("primary_common_sample") != "True":
                continue
            month = row.get("month_id", "")
            if not config.common_origin_start <= month <= config.common_origin_end:
                raise Run009AmendmentError("A primary diagnostic row lies outside the sample.")
            try:
                window = int(row["rolling_months"])
            except (KeyError, ValueError) as error:
                raise Run009AmendmentError("Invalid diagnostic rolling window.") from error
            raw_breach = row.get("core_breach")
            if raw_breach not in {"True", "False"}:
                raise Run009AmendmentError("Invalid diagnostic breach flag.")
            key = (row.get("panel_variant", ""), window)
            if not key[0]:
                raise Run009AmendmentError("Diagnostic panel variant is empty.")
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append((month, raw_breach == "True"))
    frozen = {key: tuple(values) for key, values in groups.items()}
    if len(frozen) != 15 or any(len(values) != 141 for values in frozen.values()):
        raise Run009AmendmentError("The source diagnostic common sample is incomplete.")
    return tuple(order), frozen


def _read_original_episodes(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        expected = set(AmendedEpisodeRow.__dataclass_fields__) - {"open_at_sample_end"}
        if set(reader.fieldnames or ()) != expected:
            raise Run009AmendmentError("Original episode fields differ from Run 009 v1.")
        return tuple(dict(row) for row in reader)


def _original_payload(row: AmendedEpisodeRow) -> dict[str, str]:
    payload = asdict(row)
    payload.pop("open_at_sample_end")
    return {key: "" if value is None else str(value) for key, value in payload.items()}


def run_run009_amendment(config: Run009AmendmentConfig) -> Run009AmendmentResult:
    """Reconstruct v1 episodes, prove equality, and append censoring status."""
    _validate_config(config)
    for path, expected, context in (
        (config.approved_protocol_path, config.approved_protocol_sha256, "protocol"),
        (config.source_manifest_path, config.source_manifest_sha256, "manifest"),
        (config.diagnostic_path, config.diagnostic_sha256, "diagnostic"),
        (config.original_episode_path, config.original_episode_sha256, "episode"),
        (config.source_audit_path, config.source_audit_sha256, "audit"),
    ):
        if sha256_file(path) != expected:
            raise Run009AmendmentError(f"The source {context} changed after validation.")
    _validate_source_bundle(config)
    group_order, groups = _read_diagnostics(config)
    rows: list[AmendedEpisodeRow] = []
    for variant, window in group_order:
        values = groups[(variant, window)]
        month_ids = tuple(month for month, _ in values)
        breaches = np.asarray([breach for _, breach in values], dtype=bool)
        omitted = None if variant == "full" else variant.removeprefix("omit_")
        for rule in config.episode_rules:
            episodes = detect_breach_episodes(
                month_ids,
                breaches,
                rule.minimum_consecutive_breaches,
                rule.recovery_consecutive_stable,
            )
            for number, episode in enumerate(episodes, start=1):
                rows.append(
                    AmendedEpisodeRow(
                        panel_variant=variant,
                        omitted_feature=omitted,
                        rolling_months=window,
                        minimum_consecutive_breaches=rule.minimum_consecutive_breaches,
                        recovery_consecutive_stable=rule.recovery_consecutive_stable,
                        primary_rule=rule.primary,
                        episode_number=number,
                        start_month=episode.start_month,
                        end_month=episode.end_month,
                        duration_months=episode.duration_months,
                        breach_months=episode.breach_months,
                        open_at_sample_end=episode.open_at_sample_end,
                    )
                )
    amended = tuple(rows)
    original = _read_original_episodes(config.original_episode_path)
    reconstructed = tuple(_original_payload(row) for row in amended)
    if reconstructed != original:
        raise Run009AmendmentError("Reconstructed episodes differ from immutable Run 009 v1.")
    open_rows = [row for row in amended if row.open_at_sample_end]
    real_data = config.evidence_status == "REAL_DATA_OUTCOME_BLIND_AMENDMENT"
    audit = {
        "amendment_id": config.amendment_id,
        "evidence_status": (
            "REAL_DATA_OUTCOME_BLIND_RUN_009_EPISODE_AMENDMENT"
            if real_data
            else "SOFTWARE_TEST_ONLY"
        ),
        "config_sha256": config.config_sha256,
        "approved_protocol_sha256": config.approved_protocol_sha256,
        "source_manifest_sha256": config.source_manifest_sha256,
        "diagnostic_sha256": config.diagnostic_sha256,
        "original_episode_sha256": config.original_episode_sha256,
        "source_audit_sha256": config.source_audit_sha256,
        "episode_rows": len(amended),
        "original_fields_exact_match": True,
        "added_field": "open_at_sample_end",
        "open_episode_rows": len(open_rows),
        "open_episodes": [asdict(row) for row in open_rows],
        "numerical_classifications_changed": False,
        "original_artifacts_overwritten": False,
        "outcomes_accessed": False,
        "synthetic_observations_used": not real_data,
        "transmission_estimation_authorized": False,
    }
    return Run009AmendmentResult(amended, audit)


def write_run009_amendment_outputs(
    result: Run009AmendmentResult, episode_path: Path, audit_path: Path
) -> None:
    """Write the non-destructive amendment bundle through temporary files."""
    if not result.episode_rows or not result.audit:
        raise Run009AmendmentError("Cannot write an incomplete amendment bundle.")
    if episode_path == audit_path:
        raise Run009AmendmentError("Amendment output paths must be distinct.")
    paths = (episode_path, audit_path)
    temporary_paths = tuple(path.with_suffix(path.suffix + ".part") for path in paths)
    if any(path.exists() for path in temporary_paths):
        raise Run009AmendmentError("A stale amendment temporary artifact exists.")
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with temporary_paths[0].open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(AmendedEpisodeRow.__dataclass_fields__))
            writer.writeheader()
            writer.writerows(asdict(row) for row in result.episode_rows)
        temporary_paths[1].write_text(
            json.dumps(result.audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except Exception:
        for temporary in temporary_paths:
            temporary.unlink(missing_ok=True)
        raise
    for target, temporary in zip(paths, temporary_paths):
        temporary.replace(target)
