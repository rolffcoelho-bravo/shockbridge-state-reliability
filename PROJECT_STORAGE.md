# Project storage and recovery map

**Canonical project root:** the repository root, resolved portably from the local inventory
**Storage audit date:** 2026-10-04

All research documents, source code, tests, reports, contracts, manifests, downloaded source artifacts, and derived outputs produced for this project are stored under the canonical project root.

## Canonical locations

| Material | Location | Persistence rule |
|---|---|---|
| Research blueprints | project root, `shockbridge_state_risk_flagship_blueprint_v1.md` and `v2.md` | Git checkpoint |
| Python package | `src/shockbridge_state_risk/` | Git checkpoint |
| Automated tests | `tests/` | Git checkpoint |
| Empirical and state contracts | `research/` | Git checkpoint |
| Paper evidence, decisions, and literature records | `research/paper/` | Git checkpoint |
| Novelty and complete results registers | `research/paper/novelty_ledger.md` and `research/paper/results_register.md` | Git checkpoint; append-only in substance |
| Method protocols and deviation history | `research/methodology/` | Git checkpoint; versioned and never silently rewritten after results |
| Methodology and source audits | `reports/` | Git checkpoint |
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
| Run 012 release and manuscript records | `reports/methodology/run_012_*` and `research/paper/manuscript_architecture_v1.md` | Git checkpoint; locked reproduction, rights/privacy audit, public-CI boundary, and claim-controlled paper structure |
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
- Rebuild the Run 011 paper presentation only under a new versioned output directory; `scripts/build_run011_paper_artifacts.py` treats the published bundle as immutable.
- Recheck the exact Python 3.9 environment with `scripts/reproduce_run010_locked.py` only under a new versioned audit path; the Run 012 v1 audit is immutable.
- Audit a proposed current tree and its history with `scripts/audit_public_release.py`; use the published-repository checks for append-only corrections after the audited root release.
- Validate code and artifacts with `make quality` and `make test`.
- Verify local binary and derived artifacts with `make inventory-audit`; this checks canonical-root containment, duplicate registrations, byte sizes, and SHA-256 hashes against `data/manifests/local_artifact_inventory_2026-10-02.yaml`.

## Deliberate exclusions

Cache directories, coverage files, virtual environments, package build metadata, and interrupted downloads are not research artifacts and are excluded. Raw external data and the derived panel are not committed because their redistribution status is fetch-only or because they are reproducible outputs. Their locations, hashes, sizes, and recovery sources are committed instead.

## Current storage condition

The code and documentation layer is protected by the private canonical GitHub repository; the independently sanitized public surface is also live on GitHub. Both remote `main` refs were verified against their local heads after the first push. Ignored evidence remains outside Git and is protected by cryptographic inventories plus deterministic retrieval/build instructions. The dedicated SSH credential is stored outside the project, and no private key or token is tracked. Public corrections must be appended without rewriting the audited root commit and must pass the local release boundary plus hosted CI.

## Scientific record protocol

`docs/governance/research_artifact_protocol.md` defines the mandatory run bundle, immutable run IDs, evidence classes, claim chain, and recovery requirements. Failed and null results are retained. Novelty claims require both the novelty ledger and a closest-prior-art entry in the literature ledger.
