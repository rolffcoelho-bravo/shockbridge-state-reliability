# Run 012 public-release reproducibility and manuscript result

**Result date:** 2026-10-04  
**Protocol:** `run-012-public-release-and-manuscript-v1`  
**Primary status:** `LOCKED_REPRODUCTION_PASS_PUBLICATION_BLOCKED`  
**New empirical estimation:** none  
**Transmission outcomes accessed:** no  
**GitHub repository created:** no

## Result

The project is now organized around the evidence it actually supports. The
working title is *When a State Is Not Stable Enough: Real-Time Measurement
Reliability in Euro-Area Monetary-Policy Research*. The README, package
description, manuscript architecture, dependency controls, public CI contract,
and release-rights record consistently describe a clean-reproduced negative
measurement result rather than an unestimated transmission effect.

Run 010 reproduces exactly under an explicit Python 3.9 version lock. A clean
Git archive at commit `7be05cf` hydrated 35 untracked artifacts only after
verifying the portable 73-artifact inventory, installed exact build/runtime/dev
versions, passed static analysis and the full 140-test/90%-coverage gate, and
matched all four registered Run 010 SHA-256 hashes. Canonical artifacts remained
unchanged and the temporary checkout was removed.

This is an exact-version, same-host reproduction. It is not yet a second-
operating-system replication or a cryptographically hash-pinned package supply
chain.

## Reproducibility controls added

- exact Python 3.9 build, runtime, and development lock files;
- a clean-archive locked reproducer that refuses a dirty source tree;
- exact version validation for 18 packages and packaging tools;
- complete local-inventory hydration with byte-size and SHA-256 checks;
- full Ruff, formatting, strict-mypy, unit-test, and coverage execution inside
  the isolated archive;
- exact Run 010 output-hash comparison; and
- a portable artifact inventory resolved relative to its own location.

No second Python installation, Docker, Podman, or other container runtime was
available on the audited host. The absence is recorded as an environment
limitation rather than silently treated as a cross-platform pass.

## Public CI boundary

A source-only Git archive cannot access ignored empirical artifacts. Seven tests
are now explicitly labeled `requires local hash-registered evidence`. The public
runner fails unless exactly seven tests have that one skip reason. It executes
the remaining 137 of 144 tests and enforces 87% source-only coverage. The locked
local reproduction hydrates every registered artifact, executes the complete
suite for its frozen commit, and retains the 90% scientific coverage gate.

The GitHub Actions workflow uses read-only repository permissions, disables
checkout credential persistence, pins action revisions, tests locked Python 3.9
and abstract-dependency Python 3.12 environments, and uses the explicit public
test contract.

## Release audit

The current tracked tree passes:

- known credential-signature scanning;
- suspicious credential-filename scanning;
- current-tree workstation-path scanning;
- non-local Git author-identity scanning; and
- the raw/processed data boundary.

The full history contains no detected credential signature, but historical
versions of `PROJECT_STORAGE.md` and the local artifact inventory retain 28
home-path blob-pattern findings. The current files are portable. The appropriate
public route is a new, squashed current-tree export while preserving the full
local scientific history privately.

The scanner does not perform generic high-entropy secret detection, so a hosted
secret-protection scan remains mandatory before publication.

## Rights and licensing

The official ESCB statistical reuse policy permits reuse of publicly released
statistics with source attribution and excludes third-party data without
originator permission. The ECB disclaimer also requires accurate reproduction
and disclosure of user transformations. The project therefore keeps raw ECB
workbooks, archives, documentation PDFs, and third-party factor files fetch-only
while treating retrieval code, manifests, hashes, transformations, and
attributed aggregate displays as public candidates.

No open-source license has been selected. This is an owner-level blocker, not a
technical default. Blueprint v1/v2 also remain outside the proposed first
public export pending owner approval because their broad aspirational and
private-boundary material is not required to reproduce the reported result.

## Manuscript architecture

`research/paper/manuscript_architecture_v1.md` defines:

- the central research question and negative-result estimand;
- a ten-section paper structure;
- six main tables, four main figures, and eight appendix groups;
- exact source artifacts for every section;
- supportable, interpretive, and prohibited claims;
- ECB attribution language; and
- seven manuscript completion gates.

The architecture preserves synthetic design work in a separate appendix and
does not treat it as real-data evidence.

## Defects and anomalies corrected

DEV-036 through DEV-041 record six release-stage issues: a workstation path in
the inventory, a direct-entrypoint import failure, incomplete clean-checkout
hydration, a scanner self-match, two unlabeled evidence-bound tests, and an
undisclosed source-only coverage difference. Every failed attempt stopped before
publishing a registered conclusion. No observation, statistic, threshold,
classification, or Run 010 output changed.

## Decision

Accept the title change, manuscript architecture, portable inventory, locked
same-host reproduction, rights matrix, and explicit public-CI boundary. Preserve
all Run 008–011 scientific decisions, select no state, and keep transmission
outcomes sealed.

Do not create a public repository yet. Publication requires owner decisions on
the code/document license and blueprint exclusion, followed by a sanitized
squashed export and hosted secret scan. Cross-platform exact empirical
reproduction remains a high-value improvement after a suitable runtime or
remote runner becomes available.
