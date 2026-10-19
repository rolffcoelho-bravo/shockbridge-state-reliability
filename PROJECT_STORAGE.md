# Public repository storage and recovery map

**Canonical project root:** the repository root, resolved portably from the local inventory
**Storage audit date:** 2026-10-14

This repository is the curated public reproducibility surface. Public code,
protocols, manifests, aggregate audits, result reports, and attributed derived
displays are stored under its root. Raw external data, the working manuscript,
rejected-attempt diagnostics, and internal claim, decision, deviation,
literature, novelty, and complete-results ledgers are retained in the separate
private canonical archive.

## Canonical locations

| Material | Location | Persistence rule |
|---|---|---|
| Python package | `src/shockbridge_state_risk/` | Git checkpoint |
| Automated tests | `tests/` | Git checkpoint |
| Public empirical contracts and protocols | `research/` | Git checkpoint; immutable run IDs and prospective amendments |
| Public methodology and source audits | `reports/` | Git checkpoint; aggregate and disclosure-safe artifacts only |
| Source and output manifests | `data/manifests/`, `research/state_sources_v1.yaml`, and `reports/methodology/*.manifest.yaml` | Git checkpoint |
| Downloaded source artifacts | `data/raw/` | Local, Git-ignored, hash-registered, recoverable from recorded HTTPS sources |
| Derived point-in-time panel | `data/processed/state_panel_v1.csv` | Local, Git-ignored, hash-registered, deterministically rebuildable |
| Derived filtered state probabilities | `data/processed/state_probabilities_v1.csv` | Local, Git-ignored, hash-registered, reproducible from the frozen run bundle |
| Regular monthly state panels | `data/processed/monthly_state_panel_v1.csv` and `monthly_state_panel_v2.csv` | Local, Git-ignored, both retained and hash-registered; v1 rejected, v2 accepted for model comparison |
| State-model comparison outputs | `data/processed/state_model_comparison_v1*.csv` | Local, Git-ignored and hash-registered; invalid attempt retained separately from corrected final run |
| Run 007 state outputs | `data/processed/state_factor_run007_v1.csv`, `state_challengers_run007_v1.csv`, and `state_restart_provenance_run007_v1.jsonl` | Local, Git-ignored and hash-registered; kill-gate result retained with complete restart provenance |
| Run 008 state outputs | `data/processed/state_subspace_run008_v1.csv`, `state_fixed_factor_run008_v1.csv`, and `state_two_factor_run008_v1.csv` | Local, Git-ignored and hash-registered; failed subspace/scalar gates retained with projector, aligned-loading, score, and covariance provenance |
| Run 009 instability outputs | `data/processed/state_instability_run009_v1.csv` and `state_instability_episodes_run009_v1.csv` | Local, Git-ignored and hash-registered after execution; outcome-blind diagnostic geometry, feature-deletion sensitivity, and breach episodes only |
| Run 009 episode amendment | `data/processed/state_instability_episodes_run009_v1_amendment_1.csv` | Local, Git-ignored and hash-registered after execution; adds explicit right-censoring status without replacing v1 |
| Run 010 official latest-vintage sources | `data/raw/ecb_state/run010_latest_*.csv` | Local, Git-ignored and hash-registered; exact ECB RTD responses are recoverable from `data/manifests/run010_latest_sources_v1.yaml` |
| Run 010 vintage-robustness outputs | `data/processed/state_vintage_*_run010_v1.csv` | Local, Git-ignored and hash-registered; matched-period comparison, geometry, and episode evidence only |
| Run 011 clean-reproduction evidence | `reports/methodology/run_011_clean_reproduction.audit.json` | Git checkpoint; exact hash comparison from a removed temporary checkout and isolated runtime |
| Run 011 paper evidence bundle | `reports/paper/run011/` | Git checkpoint; deterministic CSV tables, SVG figures, and provenance generated only from registered Run 010 outputs |
| Run 012 exact dependency locks | `requirements/*.lock` | Git checkpoint; exact verified Python 3.9 build, runtime, and development versions |
| Run 012 public-release records | `reports/methodology/run_012_*` and `research/paper/manuscript_architecture_v1.md` | Git checkpoint; locked reproduction, rights/privacy audit, public-CI boundary, and claim-controlled paper structure |
| Run 020 public reliability records | `research/data/run_020_*`, `research/methodology/run_020_*`, and `reports/methodology/run_020_series_history_*` | Git checkpoint; exact-series timing pilot and corrected common-space method, excluding raw responses and rejected attempts |
| Run 027 executable-completeness records | `research/methodology/run_027_*`, `src/shockbridge_state_risk/state/reliability_protocol_completeness.py`, `scripts/run027_protocol_completeness_audit.py`, `tests/test_reliability_protocol_completeness.py`, and `reports/methodology/run_027_*` public records | Git checkpoint; 11-gap fail-closed semantic audit and unapproved prospective amendment, excluding the working manuscript and private claim/decision records |
| CI and build configuration | `.github/`, `Makefile`, and `pyproject.toml` | Git checkpoint |

## Critical recovery paths

- Recreate the Python environment from `pyproject.toml`; `.venv/` is disposable and intentionally ignored.
- Re-fetch external sources using the URLs and expected hashes in `research/state_sources_v1.yaml` and `data/manifests/`.
- Rebuild the state panel with `make state-panel`.
- Rebuild the v1 state replay with `make state-replay`; its failed screening decision is intentional evidence, not an execution error.
- Rebuild the outcome-blind Run 007 bundle with `make state-redesign`; the expected result is a state stability kill gate, not transmission authorization.
- Rebuild the outcome-blind Run 008 bundle with `make state-subspace`; the expected result is a state-measurement kill gate, not transmission authorization.
- Rebuild the outcome-blind Run 009 diagnostic bundle with `make state-instability`; it explains measurement instability descriptively and cannot select a state or authorize transmission.
- Re-fetch the exact Run 010 ECB sources with `make run010-fetch` only when the immutable v1 source bundle is absent; the command refuses overwrite and source substitution.
- Rebuild the Run 010 matched-period latest-vintage bundle with `make vintage-robustness` only under a new versioned run ID if v1 already exists; the v1 writer deliberately refuses overwrite.
- Recheck Run 010 from a clean temporary checkout with `scripts/reproduce_run010_clean.py`; the script validates every hydrated input, refuses to modify canonical outputs, and records exact hash equality.
- Recheck Run 027 with `make run027-protocol-completeness`; status 2 is the registered stop result and the JSON must report exactly 11 critical gaps against the unchanged Run 026 protocol hash. The amendment proposal is not approved and must not be used to fit official values.
- Rebuild the Run 011 paper presentation only under a new versioned output directory; `scripts/build_run011_paper_artifacts.py` treats the published bundle as immutable.
- Recheck the exact Python 3.9 environment with `scripts/reproduce_run010_locked.py` only under a new versioned audit path; the Run 012 v1 audit is immutable.
- Audit a proposed current tree and its history with `scripts/audit_public_release.py`; use the published-repository checks for append-only corrections after the audited root release.
- Validate code and artifacts with `make quality` and `make test`.
- Verify local binary and derived artifacts with `make inventory-audit`; this checks canonical-root containment, duplicate registrations, byte sizes, and SHA-256 hashes against `data/manifests/local_artifact_inventory_2026-10-02.yaml`.

## Deliberate exclusions

Cache directories, coverage files, virtual environments, package build metadata, and interrupted downloads are not research artifacts and are excluded. Raw external data and the derived panel are not committed because their redistribution status is fetch-only or because they are reproducible outputs. Their locations, hashes, sizes, and recovery sources are committed instead.

## Current storage condition

The independently sanitized public surface is live on GitHub and is maintained
through protected pull requests. Ignored evidence remains outside this
repository and is protected in the canonical archive by cryptographic
inventories plus deterministic retrieval/build instructions. No credential,
private key, raw response, working manuscript, or internal research-control
ledger is tracked here. Public corrections are append-only in Git history and
must pass the local release boundary plus hosted CI.

## Scientific record protocol

`docs/governance/research_artifact_protocol.md` defines the mandatory run
bundle, immutable run IDs, evidence classes, claim chain, and recovery
requirements. Published failed and null results are retained. Novelty remains
provisional until a focused closest-prior-art audit and empirical evidence both
support it; the complete adjudication record is maintained privately.
