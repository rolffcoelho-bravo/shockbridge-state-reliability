"""Single source of truth for files that must never enter a public export."""

from __future__ import annotations

PRIVATE_ONLY_PATHS = {
    ".github/workflows/private-empirical-reproduction.yml",
    "reports/methodology/run_013_public_export_build_attempt1.audit.json",
    "reports/methodology/run_013_public_export_build_attempt2.audit.json",
    "reports/methodology/run_013_public_export_build_attempt3.audit.json",
    "reports/methodology/run_013_public_export_build_attempt4.audit.json",
    "reports/methodology/run_013_public_export_build_attempt5.audit.json",
    "reports/methodology/run_013_public_export_build_attempt6.audit.json",
    "reports/methodology/run_013_public_export_security_attempt1.audit.json",
    "reports/methodology/run_013_public_export_security_attempt2.audit.json",
    "reports/methodology/run_013_public_export_security_attempt3.audit.json",
    "reports/methodology/run_013_public_export_security_attempt4.audit.json",
    "reports/methodology/run_013_public_export_security_attempt5.audit.json",
    "reports/methodology/run_013_public_export_security_attempt6.audit.json",
    "reports/methodology/run_013_public_export_verification_attempt5.audit.json",
    "reports/methodology/run_013_public_export_verification_attempt6.audit.json",
    "reports/methodology/run_019_high_dimensional_source_feasibility_v1.manifest.yaml",
    "reports/methodology/run_019_manuscript_v1_5_citation_locator_audit.yaml",
    "reports/methodology/run_019_manuscript_v1_5_claim_audit.yaml",
    "reports/methodology/run_020_series_history_and_reliability_v1.manifest.yaml",
    "reports/methodology/run_020_manuscript_v1_6_citation_locator_audit.yaml",
    "reports/methodology/run_020_manuscript_v1_6_claim_audit.yaml",
    "reports/methodology/run_021_protocol_design_v1.manifest.yaml",
    "reports/methodology/run_021_manuscript_v1_7_citation_locator_audit.yaml",
    "reports/methodology/run_021_manuscript_v1_7_claim_audit.yaml",
    "reports/methodology/run_021_public_release_receipt_2026-10-15.json",
    "reports/methodology/run_022_manuscript_v1_8_citation_locator_audit.yaml",
    "reports/methodology/run_022_manuscript_v1_8_claim_audit.yaml",
    "reports/methodology/run_022_reliability_engine_v1.manifest.yaml",
    "reports/methodology/run_022_public_release_receipt_2026-10-15.json",
    "shockbridge_state_risk_flagship_blueprint_v1.md",
    "shockbridge_state_risk_flagship_blueprint_v2.md",
    "scripts/reproduce_run010_portable.py",
    "tests/test_portable_reproduction.py",
    "research/methodology/deviation_log.md",
    "research/paper/claim_matrix.md",
    "research/paper/decision_log.md",
    "research/paper/literature_ledger.md",
    "research/paper/novelty_ledger.md",
    "research/paper/results_register.md",
}

PRIVATE_ONLY_PREFIXES = (
    "private/",
    "research/paper/manuscript_v1",
    "research/paper/external_review_packet_",
    "research/methodology/run_016_manuscript",
    "research/methodology/run_016_adversarial",
    "research/methodology/run_017_",
    "research/methodology/run_018_",
    "reports/methodology/run_016_manuscript",
    "reports/methodology/run_016_adversarial",
    "reports/methodology/run_017_",
    "reports/methodology/run_018_",
    "reports/methodology/state_abstention_run018_",
    "reports/methodology/run_019_public_export_",
    "reports/methodology/run_020_series_history_pilot_attempt",
    "reports/paper/run016/run016_journal_fit_",
    "reports/paper/run018/",
)


def is_private_only_path(relative: str) -> bool:
    """Return whether a repository-relative path is excluded from public export."""
    return relative in PRIVATE_ONLY_PATHS or relative.startswith(PRIVATE_ONLY_PREFIXES)
