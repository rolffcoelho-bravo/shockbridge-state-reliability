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
evidence. This repository contains no validated state-dependent transmission
effect, amplification result, trading signal, or production model.

## Project status

| Dimension | Current verified status |
|---|---|
| Research gate | State measurement completed; transmission estimation remains blocked |
| Main finding | No registered one- or two-dimensional state representation passes the prospective joint stability gates |
| Empirical basis | Real, freely retrievable official ECB sources with point-in-time timing controls |
| Reproduction | Exact Run 010 byte-hash reproduction in clean and locked Python 3.9 environments |
| Public verification | Python 3.9 and 3.12 on Ubuntu 24.04; prospective Ubuntu 26.04 compatibility lane |
| Test contract | 158 tests: 151 public executions plus exactly seven evidence-bound skips; complete local suite at 90% coverage |
| Security | CodeQL, secret and push protection, Dependabot, immutable action pins, and private vulnerability reporting |

### Reviewer paths

- **Understand the finding:** [main result](#main-result) and
  [`research/paper/claim_matrix.md`](research/paper/claim_matrix.md)
- **Inspect the evidence sequence:**
  [`research/paper/results_register.md`](research/paper/results_register.md) and
  [`research/paper/evidence_ledger.md`](research/paper/evidence_ledger.md)
- **Reproduce the software gates:** [reproducibility](#reproducibility)
- **Review tables and figures:**
  [`reports/paper/run011/`](reports/paper/run011/)
- **Audit changes and limitations:**
  [`research/methodology/deviation_log.md`](research/methodology/deviation_log.md)
- **Contribute or report a problem:** [`CONTRIBUTING.md`](CONTRIBUTING.md) and
  [`SECURITY.md`](SECURITY.md)

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
transmission outcomes remain sealed
```

The main scientific records are:

- [`research/paper/results_register.md`](research/paper/results_register.md) —
  every executed run, including failures;
- [`research/paper/evidence_ledger.md`](research/paper/evidence_ledger.md) —
  candidate claims and remaining requirements;
- [`research/paper/claim_matrix.md`](research/paper/claim_matrix.md) — current
  fact, estimate, limitation, and prohibited-claim boundaries;
- [`research/paper/novelty_ledger.md`](research/paper/novelty_ledger.md) —
  closest-method and contribution discipline;
- [`research/methodology/deviation_log.md`](research/methodology/deviation_log.md)
  — defects and post-result changes without silent rewriting; and
- [`reports/methodology/run_011_reproduction_and_positioning_result_2026-10-04.md`](reports/methodology/run_011_reproduction_and_positioning_result_2026-10-04.md)
  — exact reproduction and literature-positioning result.

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
90% coverage gate. The current repository contract contains 158 tests and adds
cross-version, cross-runner, archive-safety, release-boundary, and hosted
security regression coverage.

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
explicitly labeled evidence-bound skips, executes the remaining 151 tests, and
enforces an 87% source-only coverage floor. The locked local reproduction
hydrates all hash-registered evidence, executes all 158 tests, and retains the
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
