# Run 007 downstream component audit

**Date:** 2026-10-03  
**Status:** approved methods implemented; exact downstream numerical values approved and frozen
**Outcome access:** none  
**Empirical Run 007 state execution:** completed; downstream execution none

## Implemented

- Convex-hull support at both the treated and zero-dose endpoints.
- Gaussian-kernel local effective sample size at both endpoints.
- Exact integration of filtered-state mean and variance through the quadratic tensor basis.
- A minimal cubic tensor-product B-spline robustness basis with a second-difference curvature penalty.
- Forward-only expanding validation for a basis frozen from an outer development block.
- Deterministic circular moving-block bootstrap plans and a callback contract requiring both state and transmission re-estimation inside every draw.
- Complete stochastic PCA restart records with seeds, inertia gaps, semantically aligned assignments, and agreements.

## Audit corrections

DEV-018 corrects PCA restart assignments that were stored in pre-semantic label space. DEV-019 corrects unequal weighting of a short final spline-validation block and explicitly records the outer-development basis-freeze requirement. DEV-020 replaces penalized normal equations with rank-checked augmented least squares and validates spline specifications. DEV-021 validates complete bootstrap plans before any nested-estimator callback can run. All corrections precede empirical execution.

## Exact numerical design

`research/methodology/run_007_downstream_design_proposal_v1.yaml` freezes:

- primary local-support bandwidth 0.75 standardized units and minimum local ESS 20;
- support sensitivities at bandwidths 0.50/1.00 and ESS 15/25;
- one median interior knot per cubic marginal, yielding a 25-term tensor spline;
- penalty grid 0.01, 0.10, 1, 10, 100 with 120 initial events and 20-event forward validation blocks;
- 1,999 circular moving-block replications, six-event primary blocks, and four/eight-event sensitivity blocks.

The proposed six-event block approximates one year of scheduled ECB meetings. The final block length must be increased if the frozen outcome horizon creates dependence spanning more than six event observations.

## Important boundaries

The bootstrap engine guarantees deterministic dependence-preserving index plans and invokes the supplied nested estimator once per draw. The actual state/transmission callback cannot be wired until the Run 007 state representation and transmission sample are frozen. Its contract and audit output must prove that the first stage was refit rather than reused.

The spline tuning routine is not leakage-safe if a caller constructs knots or boundaries using an outer final block. Every selection result therefore carries the explicit requirement `FROZEN_FROM_OUTER_DEVELOPMENT_BLOCK`.

No support eligibility, model choice, response estimate, confidence interval, or scientific claim was produced.

## Verification

- 101 automated tests pass;
- strict mypy passes over 28 source files;
- Ruff lint and format pass over 89 files;
- combined line-and-branch coverage is 90.4474%, above the 90% gate;
- all 30 registered local artifacts verify;
- state-only Run 007 execution was later authorized; transmission-outcome execution remains false.

## Post-audit status

The values above were approved before Run 007 empirical execution and are recorded in D019. Run 007 subsequently failed its state stability kill gate (D020), so none of these downstream components has been empirically executed and transmission outcomes remain sealed.
