# When a State Is Not Stable Enough

## Real-Time Measurement Reliability in Euro-Area Monetary-Policy Research

[![CI](https://github.com/rolffcoelho-bravo/shockbridge-state-reliability/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/rolffcoelho-bravo/shockbridge-state-reliability/actions/workflows/ci.yml)
[![CodeQL](https://github.com/rolffcoelho-bravo/shockbridge-state-reliability/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/rolffcoelho-bravo/shockbridge-state-reliability/actions/workflows/codeql.yml)
[![Python 3.9–3.12](https://img.shields.io/badge/Python-3.9%E2%80%933.12-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![Code: Apache-2.0](https://img.shields.io/badge/code-Apache--2.0-6E4AFF)](LICENSE)
[![Research materials: CC BY 4.0](https://img.shields.io/badge/research_materials-CC_BY_4.0-2B579A)](LICENSE-DOCS.md)

> An outcome-blind reliability audit of whether a macro-financial state is
> stable enough to support state-dependent monetary-policy research.

This project asks a question that must be answered before estimating
state-dependent monetary-policy effects: is the proposed pre-event state stable
enough to be used as a conditioning variable?

The current evidence says **no** for the registered four-feature euro-area state
measurement. Prospectively frozen tests reject one- and two-dimensional state
representations across expanding and rolling information histories. The failure
persists under a matched-period latest official ECB real-time-data vintage. The
project therefore selects no state and does not estimate transmission effects.

**Evidence status:** clean-reproduced, outcome-blind negative measurement
evidence plus a completed official-series history pilot, a fail-closed wider-
panel protocol, its value-free reliability-engine implementation, an audited
outcome-blind build of the registered official panels, and a validated archive-
identifier and release-time sensitivity.
This repository contains no validated state-dependent transmission effect,
amplification result, trading signal, or production model.

## Project status

| Dimension | Current verified status |
|---|---|
| Research gate | Four-feature measurement rejected; Run 025 validates the DFR effective-date clock and freezes four wider-panel source-clock scenarios; reliability fitting and transmission remain blocked |
| Main finding | No registered one- or two-dimensional state representation passes the prospective joint stability gates |
| Empirical basis | Real, freely retrievable official ECB sources with point-in-time timing controls |
| Reproduction | Exact Run 010 byte-hash reproduction in clean and locked Python 3.9 environments |
| Public verification | Python 3.9 and 3.12 on Ubuntu 24.04; prospective Ubuntu 26.04 compatibility lane |
| Test contract | Private canonical suite: 260/260 at 90% coverage; prospective public slice: 248 tests, 239 executions plus exactly nine evidence-bound skips |
| Security | CodeQL, secret and push protection, Dependabot, immutable action pins, and private vulnerability reporting |

### Dimensional scope

The flagship program is designed to study high-dimensional macro-financial
state measurement. The executed and published empirical panel in this release,
however, contains four registered features. It is therefore a disciplined
low-dimensional stress test of the broader methodology—not a large-*N*
high-dimensional result. Run 019 supplies the source-feasibility audit and
channel architecture. Run 020 then checks eleven exact real ECB series across
all eight channels: six are replay eligible, four require frozen release-lag
treatment, and CISS remains forward-only. The seven-series core panel spans
five channels; the ten-series augmented panel spans seven. These short pilot
samples establish metadata and timing feasibility only. Run 021 now freezes
the full-panel manifest, decision clock, transformation lookbacks, ragged-edge
rank rule, 56-scenario ceiling, mature-label evaluation calendar, comparator
set, invariance tests, and stopping rules. Run 022 implements and adversarially
tests the value-free numerical kernel without retrieving the histories. Run
023 then hash-registers ten real official series responses and seven release-
evidence pages and constructs the two outcome-blind panels over 274 monthly
origins. Run 024 then validates exact legacy archive identifiers, raising fully
observed augmented-panel origins from 102 to 123, and rebuilds a conservative
next-day timing variant. Run 025 then validates 51 official DFR effective-date
events against 8,366 retained daily observations, raises fully observed origins
to 179 in both panels, and freezes four archive × DFR clock scenarios. It does
not fit or validate the reliability envelope. The ten-series design is a wider
multichannel panel, not a high-dimensional empirical result.

### Reviewer paths

- **Understand the finding:** [main result](#main-result) and
  [`research/paper/evidence_ledger.md`](research/paper/evidence_ledger.md)
- **Inspect the wider-panel design:**
  [`research/data/run_019_source_feasibility_matrix_v1.csv`](research/data/run_019_source_feasibility_matrix_v1.csv),
  [`research/data/run_019_channel_architecture_v1.yaml`](research/data/run_019_channel_architecture_v1.yaml), and
  [`research/methodology/run_019_information_set_reliability_concept_v1.md`](research/methodology/run_019_information_set_reliability_concept_v1.md)
- **Inspect the real-series pilot and corrected method:**
  [`reports/methodology/run_020_series_history_and_reliability_result_2026-10-12.md`](reports/methodology/run_020_series_history_and_reliability_result_2026-10-12.md),
  [`reports/methodology/run_020_series_history_pilot.audit.json`](reports/methodology/run_020_series_history_pilot.audit.json), and
  [`research/methodology/run_020_information_set_reliability_method_v1.md`](research/methodology/run_020_information_set_reliability_method_v1.md)
- **Inspect the frozen full-panel contract:**
  [`reports/methodology/run_021_protocol_design_result_2026-10-14.md`](reports/methodology/run_021_protocol_design_result_2026-10-14.md),
  [`research/methodology/run_021_full_panel_build_protocol_v1.yaml`](research/methodology/run_021_full_panel_build_protocol_v1.yaml), and
  [`reports/methodology/run_021_protocol_preflight.audit.json`](reports/methodology/run_021_protocol_preflight.audit.json)
- **Inspect the reliability-engine implementation:**
  [`reports/methodology/run_022_reliability_engine_result_2026-10-15.md`](reports/methodology/run_022_reliability_engine_result_2026-10-15.md),
  [`src/shockbridge_state_risk/state/reliability_engine.py`](src/shockbridge_state_risk/state/reliability_engine.py), and
  [`tests/test_reliability_engine.py`](tests/test_reliability_engine.py)
- **Inspect the official panel build:**
  [`reports/methodology/run_023_full_panel_build_result_2026-10-15.md`](reports/methodology/run_023_full_panel_build_result_2026-10-15.md),
  [`reports/methodology/run_023_full_panel_coverage.audit.json`](reports/methodology/run_023_full_panel_coverage.audit.json), and
  [`src/shockbridge_state_risk/data/full_panel_build.py`](src/shockbridge_state_risk/data/full_panel_build.py)
- **Inspect the source-clock amendments:**
  [`reports/methodology/run_024_archive_timing_sensitivity_result_2026-10-16.md`](reports/methodology/run_024_archive_timing_sensitivity_result_2026-10-16.md),
  [`reports/methodology/run_025_dfr_effective_date_source_result_2026-10-16.md`](reports/methodology/run_025_dfr_effective_date_source_result_2026-10-16.md), and
  the corresponding implementations in
  [`archive_timing_amendment.py`](src/shockbridge_state_risk/data/archive_timing_amendment.py) and
  [`dfr_effective_date.py`](src/shockbridge_state_risk/data/dfr_effective_date.py)
- **Reproduce the software gates:** [`REPRODUCING.md`](REPRODUCING.md) and
  [reproducibility](#reproducibility)
- **Review tables and figures:**
  [`reports/paper/run011/`](reports/paper/run011/)
- **Audit the research contract:**
  [`docs/governance/research_artifact_protocol.md`](docs/governance/research_artifact_protocol.md)
- **Contribute or report a problem:** [`CONTRIBUTING.md`](CONTRIBUTING.md),
  [`SUPPORT.md`](SUPPORT.md), and [`SECURITY.md`](SECURITY.md)

## Licensing and public boundary

The software is licensed under Apache-2.0. Owner-authored documentation,
tables, and figures are licensed under CC BY 4.0 unless a file or source note
states otherwise. External data and third-party source material are not
relicensed or redistributed; see `NOTICE` and `LICENSE-DOCS.md`.

The public reproducibility surface began as a clean, parentless release commit;
later release-engineering corrections are appended without rewriting that
root. It excludes the two flagship blueprints, ignored local evidence, raw and
processed data, and the canonical repository's private development history.
The canonical research archive and public repository are intentionally
separate.

## Why the negative result matters

A model can have favorable predictive density while its economic orientation or
factor geometry changes enough to undermine downstream interpretation. This
project links model screening, point-in-time measurement, geometry diagnostics,
vintage sensitivity, and an outcome firewall in one prospective evidence
sequence. Failed models and null results remain in the record rather than being
replaced after outcomes are inspected.

The candidate contribution is this auditable validation and scientific-
governance sequence in a specific euro-area application. Principal components,
factor-geometry diagnostics, vintage comparisons, loading-instability methods,
and block resampling are established methods and are not claimed as novel.

## Next research design

The next candidate method is an **admissible information-set reliability
envelope**. Run 021 freezes a set of panels that differ only by documented
source, publication timing, ragged-edge, and channel-composition rules. The
future engine would authorize a state only when its economically relevant
subspace is stable across that set; otherwise it would abstain before outcomes
are opened.

Run 020 corrects the cross-panel geometry before implementation. Factor-score
projectors are compared in a common 120-month calendar space, while loadings
are mapped to the same frozen eight-channel economic space. This avoids the
invalid subtraction of loading projectors defined on different variables.

Run 021 makes that proposal falsifiable. It binds ten exact official ECB
series, two panels, seven represented channels, and at most 56 scenarios before
exact deduplication. Calibration ends in 2017, 2018 is an embargo, evaluation
runs from January 2019 through October 2024, and the diagnostic tail through
October 2025 matures every twelve-month future-failure label. The envelope must
beat the single augmented panel at useful participation and is also compared
with always abstain, aligned panel combination, and robust PCA. Thresholds and
participation matching use calibration data only.

Run 022 implements the deterministic, value-free numerical kernel: observed-
moment standardization, signed channel balancing, ragged-edge EM-PCA, ICp2 rank
selection, rotation-invariant projectors, Procrustes alignment, and exact
scenario deduplication. Nineteen focused tests establish software behavior,
not empirical reliability. The envelope remains a candidate methodological
synthesis, not an empirically validated method. Real-time monetary-policy
analysis, ragged-edge dynamic factors, vintage combination, model uncertainty,
and robust PCA are established. Research value must come from a falsifiable
comparison showing useful nondegenerate authorization or consequential
information-set fragility. Universal abstention, cosmetic expansion, or
outcome-selected panels count as failure.

Run 023 executes only the registered retrieval and panel-build gate. The
accepted atomic bundle contains ten official ECB histories and seven official
timing-evidence responses. P0 has 1,918 rows and P1 has 2,740 rows across 274
monthly origins, with zero duplicate keys, non-finite transformed values, or
point-in-time violations. P0 and P1 are fully observed at 123 and 102 origins,
respectively. These are feasibility and provenance results, not evidence that
the reliability method works.

Run 024 reuses the preserved official responses and admits only exact legacy
MIR and BSI identifiers that pass entry-local, year, and strictly-prior-month
validation. The amended P1 covers 261 MIR, 260 adjusted-loan, and 272 M3
origins and is fully observed at 123 origins. Moving every mapped release to
the next calendar day changes selected values at 23 origins but changes no
missingness status or complete-origin count. Both clocks remain future
reliability scenarios; neither is a reliability result.

Run 025 replaces the DFR API database-validity clock with an independently
preserved official effective-date table after 8,366/8,366 daily exact matches.
DFR coverage rises from 123 to 274 origins and fully observed P0/P1 coverage
rises to 179/179. Moving DFR usability to the next calendar day changes stored
timestamps but no monthly selected observation, value, or missingness state.
The four source-clock panels remain outcome blind and unfitted.

## Evidence sequence

```text
official source audit
        ↓
point-in-time monthly panel
        ↓
prospective state-model comparison ── no eligible model
        ↓
continuous and subspace redesigns ─── kill gates remain active
        ↓
factor-geometry diagnosis ─────────── persistent instability
        ↓
matched latest-vintage sensitivity ─ classification unchanged
        ↓
clean and locked reproduction ────── exact byte-hash equality
        ↓
chronological buffer calibration ─── no improvement; original gate retained
        ↓
wider official-source audit ──────── feasible, heterogeneous timing classes
        ↓
exact series-history pilot ───────── two panels pass source-level gates
        ↓
common-space method correction ───── definition frozen before implementation
        ↓
full-panel protocol preflight ─────── 56 scenarios; mature labels; no retrieval
        ↓
value-free numerical engine ───────── 19 focused tests; no empirical fit
        ↓
official full-history panel build ─── 274 origins; zero timing violations
        ↓
archive and timing amendment ──────── P1 complete origins 102→123; two clocks
        ↓
DFR effective-date amendment ──────── both panels complete at 179; four clocks
        ↓
transmission outcomes remain sealed; reliability fitting requires a new protocol
```

The main public scientific records are:

- [`research/paper/evidence_ledger.md`](research/paper/evidence_ledger.md) —
  candidate claims and remaining requirements;
- [`reports/methodology/run_011_reproduction_and_positioning_result_2026-10-04.md`](reports/methodology/run_011_reproduction_and_positioning_result_2026-10-04.md)
  — exact reproduction and literature-positioning result;
- [`reports/methodology/run_019_high_dimensional_source_feasibility_result_2026-10-12.md`](reports/methodology/run_019_high_dimensional_source_feasibility_result_2026-10-12.md)
  — wider official-source and method-concept decision;
- [`reports/methodology/run_020_series_history_and_reliability_result_2026-10-12.md`](reports/methodology/run_020_series_history_and_reliability_result_2026-10-12.md)
  — real-series timing pilot and corrected common-space method decision;
- [`reports/methodology/run_021_protocol_design_result_2026-10-14.md`](reports/methodology/run_021_protocol_design_result_2026-10-14.md)
  — fail-closed full-panel implementation and evaluation contract;
- [`reports/methodology/run_022_reliability_engine_result_2026-10-15.md`](reports/methodology/run_022_reliability_engine_result_2026-10-15.md)
  — value-free numerical implementation and software-validation boundary;
- [`reports/methodology/run_023_full_panel_build_result_2026-10-15.md`](reports/methodology/run_023_full_panel_build_result_2026-10-15.md)
  — official outcome-blind panel build, coverage, and interpretation boundary;
- [`reports/methodology/run_024_archive_timing_sensitivity_result_2026-10-16.md`](reports/methodology/run_024_archive_timing_sensitivity_result_2026-10-16.md)
  — validated archive extension and registered release-time sensitivity; and
- [`docs/governance/research_artifact_protocol.md`](docs/governance/research_artifact_protocol.md)
  — versioning, claim-chain, negative-result, and recovery controls.

The private canonical archive retains the complete manuscript, claim,
literature, novelty, decision, result, and deviation ledgers. The public
repository exposes only the records needed to evaluate and reuse the released
research surface.

## Main result

Across 96-, 120-, and 144-month rolling histories, the full-panel factor
geometry fails the frozen joint stability classification under both the
point-in-time and matched-period latest official vintage. All 15
leave-one-feature-out window classifications are unchanged across vintages.
Primary full-panel breach episodes overlap by 0.904–0.981 across vintages.

These are descriptive measurement-stability results. They are not causal
effects of data revisions, estimated structural breaks, or evidence that factor
models fail generally.

Paper-ready tables, vector figures, and provenance are in
[`reports/paper/run011/`](reports/paper/run011/).

## Reproducibility

Run 011 reproduced all four registered Run 010 outputs byte for byte from a
clean Git archive and isolated Python environment. Run 012 repeated the exact
reproduction using explicit Python 3.9 build, runtime, and development locks,
while also running static analysis, the then-registered 140-test suite, and the
90% coverage gate. The current private canonical contract contains 260 tests
and adds cross-version, cross-runner, archive-safety, release-boundary, source-
feasibility, series-history, protocol-contract, reliability-engine, and hosted
security regression coverage. The prospective public slice contains 248 tests; the
difference is private evidence and unpublished research-bound material.

Create a locked Python 3.9 environment:

```bash
python3.9 -m venv .venv
.venv/bin/python -m pip install -r requirements/build-py39.lock
.venv/bin/python -m pip install -r requirements/dev-py39.lock
.venv/bin/python -m pip install --no-deps -e .
make quality
make test
```

The abstract dependency ranges remain in `pyproject.toml` for supported Python
installation. The lock files describe the exact verified Python 3.9
environment. A second operating system or Python minor version has not yet
reproduced the empirical bundle.

Public CI cannot access ignored empirical artifacts. It requires exactly nine
explicitly labeled evidence-bound skips, executes the remaining 239 tests, and
enforces an 87% source-only coverage floor. The locked local reproduction
hydrates all hash-registered evidence, executes all 260 tests, and retains the
90% coverage floor. These are separate, visible gates.

Locally retained empirical artifacts are verified with:

```bash
make inventory-audit
```

The empirical contract audit intentionally exits with status `2`: the
transmission estimand remains blocked because no state passed the prospective
measurement gates and transmission prerequisites remain unresolved.

## Repository map

| Path | Role |
|---|---|
| `src/shockbridge_state_risk/` | Typed analytical and validation library |
| `tests/` | Unit, invariance, hostile-input, and evidence-bound tests |
| `experiments/` | Frozen execution configurations |
| `research/methodology/` | Prospective protocols and approved amendments |
| `research/paper/` | Claim, novelty, decision, evidence, and result ledgers |
| `reports/methodology/` | Immutable audits, manifests, and run interpretations |
| `reports/paper/run011/` | Paper-ready tables, vector figures, and provenance |
| `data/manifests/` | Source and artifact metadata; not redistributed datasets |
| `.github/` | CI, CodeQL, dependency, issue, and review governance |

## Data availability and public boundary

Raw and processed datasets are not tracked. The repository records official
source URLs, series identifiers, retrieval logic, timestamps, byte sizes, and
SHA-256 hashes. ECB statistical transformations and attribution requirements
are documented; authored ECB workbooks/documents and third-party factor files
remain fetch-only under the conservative rights policy.

The code and owner-authored documentation have the explicit licenses stated
above. The sanitized release is public at
[`rolffcoelho-bravo/shockbridge-state-reliability`](https://github.com/rolffcoelho-bravo/shockbridge-state-reliability).
Its parentless root commit passed the release security and source-only
verification gates with both flagship blueprints and all protected data
excluded. Every subsequent public correction is appended, rechecked under the
same data boundary, and subjected to the GitHub Actions matrix; current hosted
results remain visible in the repository's Actions and Security pages. See
[`docs/governance/public_private_boundary.md`](docs/governance/public_private_boundary.md).

## Original broader research question

The project began by asking whether a pre-announcement macro-financial state
changes the response to an identified ECB policy shock and whether uncertainty
about that state changes the response contrast. Those questions remain
scientifically relevant, but the registered state measurement did not pass the
prerequisite gate. No transmission result is reported.

Synthetic design experiments remain clearly labeled. They test software,
support, and power behavior; they are not substitutes for empirical evidence.
