# Run 027 — Executable-completeness audit of the Run 026 reliability protocol

**Status:** mandatory prospective amendment required before empirical fitting
**Date:** 19 October 2026
**Evidence boundary:** protocol semantics and software only; no empirical fit,
evaluation result, transmission outcome, or synthetic empirical observation

## Decision

The approved Run 026 execution did not begin. Its byte-integrity preflight is
valid, but it is not sufficient to make the empirical result reproducible.
The executable-completeness audit identifies eleven result-sensitive choices
that are not uniquely determined by the frozen text. The correct scientific
action is to stop before calibration, preserve Run 026 unchanged, and seek
approval for a prospective amendment.

This is a valuable fail-closed result. It prevents implementation discretion
from becoming unreported researcher degrees of freedom and protects the
one-time 2019-01–2024-10 evaluation block.

## Critical gaps

| ID | Unresolved operation | Why it can change the result |
|---|---|---|
| XG-01 | Origin-snapshot versus observation-period matrix rows | Changes histories, ranks, projectors, and labels |
| XG-02 | Exact one-month class-B release stress | Changes admissible values and missingness |
| XG-03 | Complete-case score recovery on 120 calendar rows | Otherwise makes the score projector undefined |
| XG-04 | Near-duplicate graph and representative selection | Changes columns, channel weights, and factor geometry |
| XG-05 | Numerical anchor and unequal-rank state orientation | Changes orientation gates and state summaries |
| XG-06 | Expanding/rolling within-panel and envelope roles | Changes scenario eligibility and authorization |
| XG-07 | B1–B3 statistics, cutoffs, and robust-PCA solver | Makes benchmark loss nonreproducible |
| XG-08 | Two nominal controls are algebraic invariances | They cannot falsify mechanical authorization |
| XG-09 | Negative-control pass/fail criteria | Allows post-result interpretation |
| XG-10 | Bootstrap computational conventions | Changes intervals and prevents byte reproduction |
| XG-11 | Calibration lock and one-time evaluation state machine | Prevents independent audit of data access and retuning |

## Important methodological correction

The source-clock relabeling control is necessarily neutral after exact analytic
deduplication; that neutrality is a required invariance. A common permutation
of the eight channel-coordinate labels is also an orthogonal relabeling, so
spectral projector distances remain unchanged. Neither operation is a
discriminating negative control. The amendment proposal reclassifies them as
invariances and replaces them with controls that break series-to-channel
structure or temporal alignment while preserving the primary data boundary.

## Proposed resolution

The unapproved amendment proposal freezes:

1. the exact origin-by-series matrix and expanding/rolling windows;
2. the slow-release and complete-case operators;
3. deterministic redundancy resolution;
4. a rotation- and rank-invariant channel-anchor scalar;
5. all within-panel and cross-scenario gates;
6. executable B0–B3 comparator definitions;
7. nondegenerate controls with numerical failure rules;
8. byte-reproducible block-bootstrap conventions; and
9. a hash-chained calibration lock followed by a single-use evaluation marker.

The proposal is stored as
`research/methodology/run_027_reliability_execution_amendment_proposal_v1.yaml`.
It is explicitly **not approved** and cannot be used to fit calibration data
until the owner accepts it.

## Verification

- Four focused completeness tests pass.
- The checker returns a deliberate nonzero stop code for the incomplete Run
  026 protocol.
- The audit binds the unchanged Run 026 protocol hash
  `78d562c4d2e20529f5609198721c4d2be85694544ca66f62a48132cf29216aeb`.
- The audit records zero empirical fits, zero evaluation-result access, and
  zero transmission-outcome access.

## Research implication

No negative or positive empirical result has been produced. The prior
measurement findings remain unchanged. The candidate contribution becomes
more credible because operational completeness is now separated from byte
integrity and because nominal controls that were mathematically incapable of
falsification are not allowed to support a success claim.

## Next decision — approval required

Approve the Run 027 amendment proposal. After approval, implement and
adversarially test the complete execution harness without fitting official
values. Only after the implementation gate passes should calibration and the
2018 label-maturation embargo run. The one-time evaluation remains sealed
until the calibration lock is immutable. Transmission outcomes remain sealed
under every result.
