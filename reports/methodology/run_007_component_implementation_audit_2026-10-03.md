# Run 007 component implementation audit

**Date:** 2026-10-03  
**Status:** software components pass; empirical execution remains blocked  
**Outcome access:** none

## Implemented under approval

### Continuous filtered factor

The prospective component standardizes features using the historical estimation window only, mean-fills missing standardized training entries, estimates the first principal component, orients its sign toward higher unemployment relative to industrial production, fits a bounded AR(1), and filters the current factor with observed feature dimensions. It records filtered mean and variance, historical-window factor location and scale, loadings, sign-anchor value, feature standardization moments, AR coefficient, factor-innovation variance, idiosyncratic variances, and a joint feature-density score.

The component does not access event outcomes and has not been run on the empirical panel.

### Exact scalar clustering

The new dynamic-programming solver obtains the global minimum one-dimensional within-cluster sum of squares. It reports labels, ordered centers, boundaries, and the exact dynamic-program objective. Tests compare it with exhaustive partitions on small samples and check input-order and large-translation invariance.

The discrete output is explicitly a descriptive challenger; exact optimization is not evidence that economic regimes exist.

### HMM restart provenance and consensus

Every restart can now retain its seed, convergence, iterations, raw log likelihood, regularized MAP objective, gap from the best objective, aligned hard-assignment vector, aligned agreement, and normalized objective weight. The audit reports objective-weighted agreement, effective restart count, and the conservative all-start minimum. Objective weights are numerical diagnostics, not posterior probabilities.

A hostile test supplies a structurally disagreeing local optimum 50 objective units below the best. It remains visible through a 0.60 all-start minimum but receives negligible objective weight, demonstrating that optimization failure and competitive-solution disagreement are no longer conflated.

## Defects caught before empirical execution

The initial exact solver had three reproducibility/exactness weaknesses: undefined tolerance against an infinite baseline, order-sensitive final summation, and tolerance-based retention of a marginally higher objective. DEV-012 records the repairs. A second component audit found that the continuous-factor score omitted factor-induced cross-feature covariance and that HMM restart records omitted the aligned assignment vector required by the protocol. DEV-014 and DEV-015 record the repairs. No empirical result was produced with any defective version.

## Full verification

- 76 automated tests pass;
- strict mypy passes over 21 source files;
- Ruff lint and format pass over 72 files;
- combined line-and-branch coverage is 90.49%, above the 90% gate;
- Run 006 code paths remain available and unchanged in definition;
- no Run 007 real-data artifact exists.

## Newly exposed methodological choices

### R1 refinement — finite-dose surface complexity

The approved finite-dose response-surface concept still needs a frozen basis. The recommended primary is a standardized quadratic tensor surface in shock and continuous state. It has nine basis terms before controls, directly yields finite-dose contrasts, is feasible with roughly 242 events, and nests the linear interaction benchmark. A penalized tensor spline would be a robustness challenger because its tuning and effective degrees of freedom create greater researcher discretion in this sample.

### R3 refinement — coherent PCA density

Using only two retained PCA coordinates for likelihood would produce a two-dimensional score that is not comparable with four-feature model scores. The recommended correction is:

1. fit clusters using the prespecified leading PCA coordinates;
2. estimate state emissions in the full orthogonal PCA rotation;
3. transform the diagonal full-PC covariance back to a raw-feature covariance;
4. marginalize that covariance to whichever raw features are observed at the current origin;
5. compute both state posterior and raw-feature density from this same generative model.

This retains PCA-cluster geometry, keeps density dimension comparable, and handles missing current features coherently. The simpler alternative—distance-based PCA assignment plus a separately calculated raw density—would leave selection probabilities and predictive scores attached to different statistical models.

### Sign-anchor strength

The continuous factor exposes its orientation statistic rather than silently hiding weak economic alignment. A prospective minimum sign-anchor-strength gate should be considered alongside the cross-window gates; its numerical value is not yet chosen.

## Boundary

No empirical Run 007 execution is authorized until the R1 and R3 refinements and all numerical consistency gates are approved and frozen.
