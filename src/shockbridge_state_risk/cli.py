"""Command-line interface for research gates."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from shockbridge_state_risk.contracts import audit_contract, load_contract
from shockbridge_state_risk.data.download import download_https
from shockbridge_state_risk.data.ecb_events import audit_ea_empd, audit_ea_mpd
from shockbridge_state_risk.data.inventory import verify_inventory
from shockbridge_state_risk.data.monthly_state_panel import (
    build_monthly_state_panel,
    load_monthly_panel_config,
)
from shockbridge_state_risk.data.state_panel import (
    audit_panel,
    build_candidate_state_panel,
    load_source_registry,
    write_panel_csv,
)
from shockbridge_state_risk.design.power import load_design_grid, run_design_grid
from shockbridge_state_risk.state.comparison import (
    load_comparison_config,
    run_comparison,
    write_comparison_audit,
    write_comparison_csv,
)
from shockbridge_state_risk.state.replay import (
    load_state_replay_config,
    run_state_replay,
    write_replay_csv,
)
from shockbridge_state_risk.state.run007 import (
    load_run007_config,
    run_run007,
    write_run007_outputs,
)
from shockbridge_state_risk.state.run008 import (
    load_run008_config,
    run_run008,
    write_run008_outputs,
)
from shockbridge_state_risk.state.run009 import (
    load_run009_config,
    run_run009,
    write_run009_outputs,
)
from shockbridge_state_risk.state.run009_amendment import (
    load_run009_amendment_config,
    run_run009_amendment,
    write_run009_amendment_outputs,
)
from shockbridge_state_risk.state.run010 import (
    fetch_run010_sources,
    load_run010_config,
    run_run010,
    write_run010_outputs,
)
from shockbridge_state_risk.synthetic import run_synthetic_replay

EA_MPD_URL = "https://www.ecb.europa.eu/pub/pdf/annex/Dataset_EA-MPD.xlsx"
EA_EMPD_URL = "https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp3157-annex-EA-EMPD~8b94679d77.en.xlsx"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="state-risk")
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("audit-contract")
    audit.add_argument("path", type=Path)
    subparsers.add_parser("synthetic-replay")
    workbook = subparsers.add_parser("audit-ecb-events")
    workbook.add_argument("kind", choices=("ea-mpd", "ea-empd"))
    workbook.add_argument("path", type=Path)
    fetch = subparsers.add_parser("fetch-ecb-events")
    fetch.add_argument("kind", choices=("ea-mpd", "ea-empd"))
    fetch.add_argument("output", type=Path)
    fetch.add_argument("--expected-sha256")
    power = subparsers.add_parser("design-power")
    power.add_argument("config", type=Path)
    power.add_argument("--output", type=Path)
    state_panel = subparsers.add_parser("build-state-panel")
    state_panel.add_argument("registry", type=Path)
    state_panel.add_argument("output", type=Path)
    state_panel.add_argument("--audit-output", type=Path)
    state_replay = subparsers.add_parser("state-replay")
    state_replay.add_argument("config", type=Path)
    state_replay.add_argument("output", type=Path)
    state_replay.add_argument("--audit-output", type=Path)
    inventory = subparsers.add_parser("verify-artifacts")
    inventory.add_argument("manifest", type=Path)
    monthly_panel = subparsers.add_parser("build-monthly-state-panel")
    monthly_panel.add_argument("config", type=Path)
    monthly_panel.add_argument("output", type=Path)
    monthly_panel.add_argument("--audit-output", type=Path)
    comparison = subparsers.add_parser("compare-state-models")
    comparison.add_argument("config", type=Path)
    comparison.add_argument("output", type=Path)
    comparison.add_argument("--audit-output", required=True, type=Path)
    run007 = subparsers.add_parser("run-state-redesign")
    run007.add_argument("config", type=Path)
    run007.add_argument("--factor-output", required=True, type=Path)
    run007.add_argument("--challenger-output", required=True, type=Path)
    run007.add_argument("--restart-output", required=True, type=Path)
    run007.add_argument("--audit-output", required=True, type=Path)
    run008 = subparsers.add_parser("run-state-subspace")
    run008.add_argument("config", type=Path)
    run008.add_argument("--subspace-output", required=True, type=Path)
    run008.add_argument("--fixed-factor-output", required=True, type=Path)
    run008.add_argument("--two-factor-output", required=True, type=Path)
    run008.add_argument("--audit-output", required=True, type=Path)
    run009 = subparsers.add_parser("run-state-instability")
    run009.add_argument("config", type=Path)
    run009.add_argument("--diagnostic-output", required=True, type=Path)
    run009.add_argument("--episode-output", required=True, type=Path)
    run009.add_argument("--audit-output", required=True, type=Path)
    run009_amendment = subparsers.add_parser("amend-state-instability-episodes")
    run009_amendment.add_argument("config", type=Path)
    run009_amendment.add_argument("--episode-output", required=True, type=Path)
    run009_amendment.add_argument("--audit-output", required=True, type=Path)
    run010_fetch = subparsers.add_parser("fetch-run010-sources")
    run010_fetch.add_argument("approved_design", type=Path)
    run010_fetch.add_argument("output_directory", type=Path)
    run010_fetch.add_argument("--manifest-output", required=True, type=Path)
    run010 = subparsers.add_parser("run-vintage-robustness")
    run010.add_argument("config", type=Path)
    run010.add_argument("--comparison-output", required=True, type=Path)
    run010.add_argument("--geometry-output", required=True, type=Path)
    run010.add_argument("--episode-output", required=True, type=Path)
    run010.add_argument("--audit-output", required=True, type=Path)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "audit-contract":
        report = audit_contract(load_contract(args.path))
        print(json.dumps(asdict(report), indent=2, sort_keys=True))
        return 0 if report.ready_for_real_estimation else 2
    if args.command == "synthetic-replay":
        print(json.dumps(asdict(run_synthetic_replay()), indent=2, sort_keys=True))
        return 0
    if args.command == "audit-ecb-events":
        workbook_audit = (
            audit_ea_mpd(args.path) if args.kind == "ea-mpd" else audit_ea_empd(args.path)
        )
        print(json.dumps(asdict(workbook_audit), indent=2, sort_keys=True))
        return 0
    if args.command == "fetch-ecb-events":
        url = EA_MPD_URL if args.kind == "ea-mpd" else EA_EMPD_URL
        download_manifest = download_https(url, args.output, args.expected_sha256)
        print(json.dumps(asdict(download_manifest), indent=2, sort_keys=True))
        return 0
    if args.command == "design-power":
        payload = json.dumps(
            run_design_grid(load_design_grid(args.config)), indent=2, sort_keys=True
        )
        if args.output is None:
            print(payload)
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.output.with_suffix(args.output.suffix + ".part")
            temporary.write_text(payload + "\n", encoding="utf-8")
            temporary.replace(args.output)
            print(str(args.output))
        return 0
    if args.command == "build-state-panel":
        rows = build_candidate_state_panel(load_source_registry(args.registry))
        write_panel_csv(rows, args.output)
        audit_payload = json.dumps(asdict(audit_panel(rows)), indent=2, sort_keys=True)
        if args.audit_output is None:
            print(audit_payload)
        else:
            args.audit_output.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.audit_output.with_suffix(args.audit_output.suffix + ".part")
            temporary.write_text(audit_payload + "\n", encoding="utf-8")
            temporary.replace(args.audit_output)
            print(str(args.audit_output))
        return 0
    if args.command == "state-replay":
        replay = run_state_replay(load_state_replay_config(args.config))
        write_replay_csv(replay.rows, args.output)
        audit_payload = json.dumps(replay.audit, indent=2, sort_keys=True)
        if args.audit_output is None:
            print(audit_payload)
        else:
            args.audit_output.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.audit_output.with_suffix(args.audit_output.suffix + ".part")
            temporary.write_text(audit_payload + "\n", encoding="utf-8")
            temporary.replace(args.audit_output)
            print(str(args.audit_output))
        return 0
    if args.command == "verify-artifacts":
        inventory_audit = verify_inventory(args.manifest)
        print(json.dumps(asdict(inventory_audit), indent=2, sort_keys=True))
        return 0 if inventory_audit.passed else 2
    if args.command == "build-monthly-state-panel":
        monthly_config = load_monthly_panel_config(args.config)
        rows = build_monthly_state_panel(
            load_source_registry(monthly_config.source_registry),
            monthly_config.start,
            monthly_config.end,
            monthly_config.cutoff_rule,
        )
        write_panel_csv(rows, args.output)
        audit_payload = json.dumps(asdict(audit_panel(rows)), indent=2, sort_keys=True)
        if args.audit_output is None:
            print(audit_payload)
        else:
            args.audit_output.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.audit_output.with_suffix(args.audit_output.suffix + ".part")
            temporary.write_text(audit_payload + "\n", encoding="utf-8")
            temporary.replace(args.audit_output)
            print(str(args.audit_output))
        return 0
    if args.command == "compare-state-models":
        comparison_result = run_comparison(load_comparison_config(args.config))
        write_comparison_csv(comparison_result.rows, args.output)
        write_comparison_audit(comparison_result.audit, args.audit_output)
        print(str(args.audit_output))
        return 0
    if args.command == "run-state-redesign":
        run007_result = run_run007(load_run007_config(args.config))
        write_run007_outputs(
            run007_result,
            args.factor_output,
            args.challenger_output,
            args.restart_output,
            args.audit_output,
        )
        print(str(args.audit_output))
        return 0
    if args.command == "run-state-subspace":
        run008_result = run_run008(load_run008_config(args.config))
        write_run008_outputs(
            run008_result,
            args.subspace_output,
            args.fixed_factor_output,
            args.two_factor_output,
            args.audit_output,
        )
        print(str(args.audit_output))
        return 0
    if args.command == "run-state-instability":
        run009_result = run_run009(load_run009_config(args.config))
        write_run009_outputs(
            run009_result,
            args.diagnostic_output,
            args.episode_output,
            args.audit_output,
        )
        print(str(args.audit_output))
        return 0
    if args.command == "amend-state-instability-episodes":
        amendment_result = run_run009_amendment(load_run009_amendment_config(args.config))
        write_run009_amendment_outputs(
            amendment_result,
            args.episode_output,
            args.audit_output,
        )
        print(str(args.audit_output))
        return 0
    if args.command == "fetch-run010-sources":
        fetch_run010_sources(
            args.approved_design,
            args.output_directory,
            args.manifest_output,
        )
        print(str(args.manifest_output))
        return 0
    if args.command == "run-vintage-robustness":
        run010_result = run_run010(load_run010_config(args.config))
        write_run010_outputs(
            run010_result,
            args.comparison_output,
            args.geometry_output,
            args.episode_output,
            args.audit_output,
        )
        print(str(args.audit_output))
        return 0
    return 1
