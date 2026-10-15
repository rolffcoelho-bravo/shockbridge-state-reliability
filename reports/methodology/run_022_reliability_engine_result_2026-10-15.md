# Run 022 reliability-engine implementation result

**Date:** 2026-10-15  
**Run ID:** `run-022-reliability-engine-implementation-v1`  
**Decision:** accept the value-free numerical kernel; authorize no empirical execution

## Result

Run 022 implements the deterministic numerical core of the frozen admissible
information-set reliability design. The engine standardizes observed histories,
constructs signed inverse-square-root channel weights, fits missing-value
EM-PCA, selects identified ranks with the registered observed-entry ICp2
adaptation, constructs rotation-invariant score and economic-channel
projectors, aligns equal-rank scores by orthogonal Procrustes, and deduplicates
exact scenarios with deterministic representatives.

The implementation contains no network or filesystem interface. It accepts
in-memory arrays and metadata only. It retrieved no official full history,
built no wider panel, fitted no empirical state, inspected no transmission
outcome, and generated no empirical performance result. Numerical fixtures in
the test suite are software checks and are not research observations.

## Audit and corrections

The first mathematical audit resolved an ambiguous coordinate convention
before execution. The singular-value step uses the signed channel-weighted
matrix; returned loadings are transformed back to standardized-series
coordinates; the frozen channel map is then applied exactly once. This avoids
double weighting.

Four prospective corrections are registered:

1. `DEV-079` fixes the weighting-coordinate convention before implementation.
2. `DEV-080` requires exact byte preservation of observed standardized entries
   in the returned completed matrix.
3. `DEV-081` makes sign validation invariant to NumPy integer width and rejects
   samples outside the positive ICp2 penalty domain.
4. `DEV-082` computes the algebraically equivalent projector from left singular
   vectors, preventing the Gram matrix from squaring the condition number and
   collapsing nearly collinear but identified spaces.

Nineteen focused tests pass at 92% branch-aware engine coverage. They cover
determinism, exact observed-cell preservation, nonconvergence, rank selection,
rotation invariance, unequal-rank distances, Procrustes recovery,
near-collinearity, channel balance, canonical scenario hashing, order-
independent deduplication, hostile inputs, and the absence of retrieval and
filesystem surfaces. The complete private suite passes 225/225 tests at the
fixed 90% gate. The disclosure-safe public candidate discovers 213 tests,
executes 206, records exactly seven registered evidence-bound skips, and passes
the 87% branch-aware floor.

## Scientific interpretation

This run removes implementation ambiguity and creates a reusable, inspectable
test surface. That improves credibility and lowers the risk that a later result
is driven by silent coordinate, missing-value, or projector errors. It does not
show that the wider official panel is feasible over the full calendar, that the
envelope authorizes useful origins, that it beats the registered comparators,
or that the synthesis is methodologically novel.

The correct status is therefore
`PASS_IMPLEMENTATION_ONLY_NO_EMPIRICAL_VALIDATION`. Manuscript v1.8 records the
implementation without upgrading any state, transmission, high-dimensional, or
novelty claim.

## Next gate

The next scientifically relevant run is a separately approved, outcome-blind
retrieval and decision-time panel build from only the ten registered real,
freely retrievable official ECB series. It should stop after immutable raw-byte
registration, release-calendar verification, transformations, and panel audits.
Estimator execution and authorization evaluation should remain a later gate so
that data availability problems cannot silently modify the frozen model design.
