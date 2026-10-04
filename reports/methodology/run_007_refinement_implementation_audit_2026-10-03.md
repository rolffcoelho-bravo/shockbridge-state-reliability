# Run 007 refinement implementation audit

**Date:** 2026-10-03  
**Status:** approved components software-tested; numerical gates await approval  
**Outcome access:** none  
**Real Run 007 state-panel execution:** none

## Implemented refinements

### R1: finite-dose quadratic response surface

The primary design component now constructs a standardized hierarchical 3-by-3 tensor of shock and continuous state: intercept, each main effect through degree two, and every cross-product. The nine-term basis nests the four-term linear interaction benchmark exactly. It also constructs explicit finite-dose contrasts against the zero-shock baseline and stores outcome-blind scaling moments.

A rectangular observed-range check is implemented only as a diagnostic. It is not sufficient evidence of joint shock-state overlap and is not authorized as the final support gate.

### R3: coherent full-rank PCA emissions

The prospective PCA challenger clusters historical observations in the prespecified leading-PC coordinates, estimates state emissions over the complete orthogonal PC rotation, transforms each covariance back to the standardized feature axes, marginalizes to current observed features, and derives both posterior state probabilities and the feature-density score from that same mixture.

Run 006 remains unchanged. The new component is versioned separately and retains its rotation, leading-space centers, full-PC emission moments, feature-axis covariances, mixture weights, semantically aligned labels, likelihood dimension, and restart agreement.

### Stability and restart sensitivity

The continuous-factor gate component reports Pearson and Spearman agreement, sign disagreement, standardized mean absolute difference, loading cosines, and sign-anchor strength. Anchor summaries take the worse of expanding and rolling windows so one window cannot conceal weakness in the other.

HMM consensus can now be recomputed over any prospectively supplied objective-gap grid while preserving the all-start minimum. Objective weights remain numerical diagnostics rather than posterior model probabilities.

## Proposed numerical gates

The exact values are stored in `research/methodology/run_007_threshold_proposal_v1.yaml`. They are intentionally not execution-authorized. The proposal requires:

- Pearson and Spearman cross-window correlations of at least 0.80;
- sign disagreement no greater than 10%;
- standardized mean absolute difference no greater than 0.35;
- median loading cosine of at least 0.90 and origin-level minimum of at least 0.75;
- worse-window anchor 10th percentile of at least 0.20;
- no more than 5% of origins below the weak-anchor cutoff of 0.10;
- HMM gap summaries at 0, 2, 5, and 10 objective units, alongside the all-start minimum.

These are governance thresholds, not estimates learned from state or outcome results. Predictive-score strength cannot compensate for failing them.

## Defects corrected before empirical use

DEV-016 records the correction from pooled to worse-window anchor summaries. DEV-017 records stronger dimension and finiteness contracts for response-surface and gate inputs. All corrections precede numerical gate approval, state-panel evaluation, and outcome access.

## Verification

- 88 automated tests pass;
- strict mypy passes over 25 source files;
- Ruff lint and format pass over 80 files;
- combined line-and-branch coverage is 90.36%, above the 90% gate;
- all 24 registered local artifacts verify;
- the working implementation creates no empirical Run 007 artifact.

## Newly exposed decisions

### Joint support geometry

A rectangular range check can admit unsupported shock-state corners. The recommended primary support rule is a two-dimensional convex-hull requirement supplemented by a local-neighborhood effective-sample gate. Exact neighborhood size and minimum support must be frozen before outcome analysis.

### State-uncertainty propagation

Using only the filtered factor mean would discard first-stage uncertainty already estimated by the state engine. The recommended downstream design integrates the quadratic basis over the Gaussian filtered-state distribution and re-estimates the first stage inside dependence-aware bootstrap replications.

### Spline robustness definition

The approved spline challenger still needs fixed marginal degrees of freedom, penalty grid, and time-respecting tuning rule. These choices can materially change flexibility and must not be selected after viewing response outcomes.

## Boundary

No real-data Run 007 output, response estimate, causal claim, or state-model eligibility decision was produced. Execution remains blocked pending explicit approval of the numerical thresholds and the three downstream design choices above.
