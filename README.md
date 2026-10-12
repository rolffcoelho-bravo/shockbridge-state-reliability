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
evidence plus an outcome-blind feasibility design for a wider real-data study.
This repository contains no validated state-dependent transmission effect,
amplification result, trading signal, or production model.

## Project status

| Dimension | Current verified status |
|---|---|
| Research gate | Four-feature measurement rejected; wider-panel source feasibility complete; transmission remains blocked |
| Main finding | No registered one- or two-dimensional state representation passes the prospective joint stability gates |
| Empirical basis | Real, freely retrievable official ECB sources with point-in-time timing controls |
| Reproduction | Exact Run 010 byte-hash reproduction in clean and locked Python 3.9 environments |
| Public verification | Python 3.9 and 3.12 on Ubuntu 24.04; prospective Ubuntu 26.04 compatibility lane |
| Test contract | Private canonical suite: 180/180 at 90% coverage; public repository: 168 tests, 161 executions plus exactly seven evidence-bound skips |
| Security | CodeQL, secret and push protection, Dependabot, immutable action pins, and private vulnerability reporting |

### Dimensional scope

The flagship program is designed to study high-dimensional macro-financial
state measurement. The executed and published empirical panel in this release,
however, contains four registered features. It is therefore a disciplined
low-dimensional stress test of the broader methodology—not a large-*N*
high-dimensional result. Run 019 now supplies a frozen source-feasibility audit
and channel architecture for the prospective extension. It identifies ten
real, zero-cost official source families across eight policy-relevant channels:
two historical-replay anchors, seven release-lag candidates, and one forward-
only source class. No wider observations have yet been retrieved or estimated.
A series-level pilot, frozen panel manifest, missingness design, redundancy
controls, and multiplicity plan remain mandatory before any high-dimensional
result is reported.

### Reviewer paths

- **Understand the finding:** [main result](#main-result) and
  [`research/paper/evidence_ledger.md`](research/paper/evidence_ledger.md)
- **Inspect the wider-panel design:**
  [`research/data/run_019_source_feasibility_matrix_v1.csv`](research/data/run_019_source_feasibility_matrix_v1.csv),
  [`research/data/run_019_channel_architecture_v1.yaml`](research/data/run_019_channel_architecture_v1.yaml), and
  [`research/methodology/run_019_information_set_reliability_concept_v1.md`](research/methodology/run_019_information_set_reliability_concept_v1.md)
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
envelope**. A later protocol would freeze a set of panels that differ only by
documented source, vintage, publication-lag, ragged-edge, and channel-balance
rules. It would authorize a state only when its economically relevant subspace
is stable across that set; otherwise it would abstain before outcomes are
opened.

This is a candidate methodological synthesis, not an implemented or validated
method. Real-time monetary-policy analysis, ragged-edge dynamic factors,
vintage combination, model uncertainty, and robust PCA are established. The
research value must come from a falsifiable comparison showing that the
official-release-derived envelope provides useful nondegenerate authorization
or detects consequential information-set fragility. Universal abstention,
cosmetic feature expansion, or outcome-selected panels will count as failure.

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
transmission outcomes remain sealed; new empirical protocol required
```

The main public scientific records are:

- [`research/paper/evidence_ledger.md`](research/paper/evidence_ledger.md) —
  candidate claims and remaining requirements;
- [`reports/methodology/run_011_reproduction_and_positioning_result_2026-10-04.md`](reports/methodology/run_011_reproduction_and_positioning_result_2026-10-04.md)
  — exact reproduction and literature-positioning result;
- [`reports/methodology/run_019_high_dimensional_source_feasibility_result_2026-10-12.md`](reports/methodology/run_019_high_dimensional_source_feasibility_result_2026-10-12.md)
  — wider official-source and method-concept decision; and
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
90% coverage gate. The current private canonical contract contains 180 tests and adds
cross-version, cross-runner, archive-safety, release-boundary, source-feasibility,
and hosted security regression coverage. The public repository contains 168 tests; the
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

Public CI cannot access ignored empirical artifacts. It requires exactly seven
explicitly labeled evidence-bound skips, executes the remaining 161 tests, and
enforces an 87% source-only coverage floor. The locked local reproduction
hydrates all hash-registered evidence, executes all 180 tests, and retains the
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
