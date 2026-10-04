# Run 008 subspace-component audit

**Date:** 2026-10-03
**Status:** software components complete; exact numerical gates await approval
**Outcome access:** none
**Empirical Run 008 execution:** none

## Why this redesign is scientifically distinct

Run 007 tested the stability of one ordered principal-component loading. A first component can rotate or exchange variance with a neighboring component even when their combined factor space remains similar. Run 008 therefore separates:

1. rotation-invariant stability of the leading two-dimensional subspace;
2. economic identification of an ordered basis inside that subspace;
3. stability of a scalar loading frozen before its evaluation period; and
4. a two-factor filtered diagnostic that retains its covariance.

This is a post-Run 007 validation redesign, not a claim that two true structural factors exist.

## Implemented components

`src/shockbridge_state_risk/state/subspace.py` implements:

- principal-angle and normalized projector-distance comparison of two factor spaces;
- orthogonal Procrustes alignment to two prespecified, orthonormal targets;
- anchor-capture diagnostics that are invariant to within-subspace rotation;
- a scalar AR(1) factor with a loading frozen in an earlier development block;
- a two-factor VAR(1) filter with full factor-innovation covariance;
- joint observed-feature predictive density and exact marginalization of missing current features;
- filtered factor means and covariance for any later uncertainty-aware use.

The target directions are a slack contrast (`unemployment - industrial production`) and a point-in-time policy-minus-inflation proxy (`deposit facility rate - HICP`). The latter is not labeled an expected real rate.

## Code-audit corrections

DEV-023 records three issues corrected before empirical execution:

- reject a rank-deficient requested subspace instead of returning undefined explained-variance ratios;
- recompute projectors from audited orthonormal bases rather than trusting a stored projector field;
- require a strictly positive VAR ridge so a manually altered contract cannot expose a singular solve.

Additional fail-closed checks cover infinite inputs, all-missing current vectors, insufficient feature history, non-orthonormal anchors, incompatible basis shapes, invalid loading norms, nonpositive variance floors, and invalid transition-radius controls.

## Source-extension result

The separate official-source audit finds that a complete November 2025–October 2026 validation block cannot be built under the current contract. HICP, unemployment, and the policy rate extend into 2026, but admitted real-time industrial production ends in August 2025 and becomes stale under the frozen 120-day cap. No revised-data substitution or staleness relaxation was made.

## Prior-art boundary

Factor rotation and factor-count uncertainty are established. Bai and Ng (2002) address factor-count determination in large panels, which does not justify a two-factor truth claim in this four-series panel. Nakagawa, Kato and Imamura (2026) directly study economically regularized factor subspaces. Run 008 does not implement their regularized estimator and cannot claim subspace stabilization as novel. Its value is the prospective point-in-time validation architecture and honest recovery from a failed first-component gate.

## Proposed numerical contract

`research/methodology/run_008_subspace_design_proposal_v1.yaml` proposes:

- two-dimensional expanding and rolling-120 subspaces;
- second-principal-cosine minimum 0.75 and 10th percentile 0.90;
- projector-distance median at most 0.20 and 90th percentile at most 0.35;
- per-target anchor-capture 10th percentile at least 0.50, with at most 10% below 0.35;
- per-factor anchored-loading-cosine median at least 0.90 and 10th percentile at least 0.75;
- a scalar slack loading frozen over January 2002–December 2011, evaluated from January 2012 under the same correlation/sign/difference gates used in Run 007, plus positive mean log-density gain in each history;
- a two-factor VAR ridge of `1e-6`, transition-radius cap 0.98, and variance floor 0.05;
- factorwise two-factor diagnostics at correlation 0.75, sign disagreement 0.15, and standardized difference 0.50;
- no Run 008 transmission eligibility for the two-factor model.

Every subspace and scalar gate is conjunctive. Predictive score cannot compensate for instability. The HMM cannot be promoted from Run 007.

## Verification

- 105/105 automated tests pass;
- strict mypy passes over 29 source files;
- Ruff lint and format pass over 93 files;
- combined line-and-branch coverage is 90.7790%;
- the new subspace component has 95.8955% line-and-branch coverage;
- Run 008 components were tested only on synthetic software arrays;
- no empirical Run 008 output or transmission estimate exists.

## Approval boundary

The software is ready for an outcome-blind Run 008 orchestration layer only if the exact numerical contract is explicitly approved. Approval would authorize freezing and testing the orchestration, followed by a separate audited state-only execution. It would not authorize transmission outcomes.
