# Run 007 targeted literature and methodology audit

**Date:** 2026-10-02  
**Status:** completed audit; three implementation choices awaiting approval  
**Outcome access:** none

## Audit question

What can be frozen for the continuous-factor and near-optimal-stability redesign without importing arbitrary thresholds or overstating novelty?

## Findings supported by primary sources

1. Principal-component/diffusion-index factors are an established transparent way to compress macroeconomic information and can be evaluated in simulated real time. This supports a continuous factor baseline but does not make that factor an economically valid state by itself.
2. One-dimensional k-means has an exact dynamic-programming solution. Replacing random-start clustering on a scalar factor is therefore a defensible removal of optimizer noise, not a novel method.
3. Local projections accommodate flexible specifications, and state-dependent monetary-policy transmission is established prior art. A continuous factor interaction is not a contribution by itself.
4. The 2024 *Journal of Econometrics* result on state-dependent local projections creates a direct identification constraint: when the state responds to macroeconomic shocks, a conventional state-dependent LP generally targets an infinitesimal response rather than an arbitrary finite shock response. The Blueprint's estimand explicitly contains a shock dose, so this cannot be left implicit.
5. A 2026 working paper argues that linear shock–state interactions generally fail when the state-response function is nonlinear and develops a sieve alternative under sufficient conditions. Because the inspected version is a working paper and focuses on micro–macro panels, it is a design warning and challenger—not settled authority for this aggregate event study.
6. No inspected primary source supplies a universal HMM “near-optimal restart” objective-gap cutoff. Importing the 1e-6 relative-inertia tolerance used in the exact 1-D k-means paper would be category error: k-means inertia and a regularized HMM log posterior are different objectives.

## Code-method anomalies

### PCA challenger assignment mismatch

`predict_pca_cluster` estimates clusters in PCA-score space and computes the current observation's PCA score, but discards that score. The current posterior and density score are then calculated using a raw-feature Gaussian mixture. This is deterministic code, not a runtime error, but the fitted cluster geometry and assignment geometry do not match. Correcting it would alter the benchmark definition and therefore requires prospective approval.

### Restart stability conflates two phenomena

The current minimum agreement across every random start combines optimization failure with genuine disagreement among competitive solutions. The approved redesign should retain all restart seeds, convergence flags, raw likelihoods, regularized objectives, objective gaps, and aligned assignments. Because there is no universal cutoff, a single undisclosed tolerance is not defensible.

### Continuous factor needs a real-time identity

Factor sign and scale are not intrinsically identified. Every historical refit must orient the factor using a prespecified outcome-blind slack direction and normalize it using only the estimation window. Cross-window comparison must align sign before computing consistency. Otherwise apparent instability can be a representation artifact.

## Approval-gated recommendations

### R1 — Finite-dose response surface

Preserve the Blueprint's finite-dose estimand and plan a flexible shock-by-state response surface as the primary transmission specification after the state engine is frozen. Keep the conventional linear interaction as a transparent benchmark. Require explicit diagnostics for shock nonlinearity and state evolution before using causal language.

### R2 — Objective-weighted restart consensus

Avoid a universal hard “near-optimal” cutoff as the primary HMM stability statistic. Use objective weights proportional to `exp(objective - best_objective)` after per-origin normalization, report effective restart count and weighted aligned agreement, and disclose an objective-gap sensitivity curve. Retain all-start minimum agreement as a conservative diagnostic, not the sole gate.

### R3 — Coherent PCA-space challenger

For the prospective Run 007 benchmark, assign the current observation and compute its cluster likelihood in the same PCA-score space used to fit the clusters. Preserve the Run 006 raw-space-mixture implementation as the versioned historical benchmark.

## Already-authorized components

- continuous filtered factor using only information available at each origin;
- exact one-dimensional clustering for factor discretization;
- complete per-restart provenance;
- expanding-versus-rolling consistency assessment;
- no outcome access during state-model selection;
- real freely retrievable empirical data only, with synthetic arrays restricted to software tests.

## Boundary

The audit does not authorize R1–R3. Each changes either the later estimand, the stability gate, or a benchmark definition. Numerical thresholds for cross-window consistency also remain to be frozen prospectively after the user decides on these recommendations.
