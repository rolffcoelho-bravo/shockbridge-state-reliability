# Run 030 — Approved Stage-A orchestration implementation

**Status:** orchestration implementation gate passed; official calibration is
released only from a clean, committed implementation checkpoint  
**Date:** 21 October 2026  
**Evidence boundary:** approved methodology and hostile software fixtures;
no official panel value entered an estimator, no calibration or evaluation
result was accessed, and transmission outcomes remain sealed

## Decision

Accept the exact Run 029 orchestration amendment as implemented in the new
Run 030 layer. All nine resolutions OG-01 through OG-09 are explicit and
hostile-tested. The prior Run 028 harness remains byte-identical at SHA-256
`ed8480fb7c42ed48d0014d1c4a779ceb4bffd594f8f023628a1ccb00c84ba378`;
its missing-cell robust-PCA defect is preserved as historical evidence rather
than silently rewritten. The corrected projected estimator exists only in the
prospectively approved Run 030 module.

The next permitted action is Stage-A calibration from a clean Git commit,
using only the registered real, freely retrievable official ECB inputs. That
action must create the complete 60-origin ledger, pre-fit evaluation identity
map, and immutable calibration lock, then stop. Evaluation fitting, evaluation
labels and metrics, and transmission outcomes remain prohibited.

## Implemented resolution map

| Resolution | Executable rule | Hostile verification |
|---|---|---|
| OG-01 | Expanding and rolling histories retain series independently; identity binds ordered IDs, masks, and matrices | Unequal history column counts do not collide |
| OG-02 | Fourteen pipeline operations have one exact order | Any permutation fails closed |
| OG-03 | Complete categorical ranks, exact duplicate collapse, and within-channel correlation components | Every manifest category is covered; duplicate tie-break is deterministic |
| OG-04 | B2 averages unique analytic classes in common scalar and eight-channel operator spaces | Provenance duplication has zero weight; projector rotation leaves the combination unchanged |
| OG-05 | Projected observed-entry PCP carries the prior low-rank iterate on missing cells | Missing entries remain outside sparse and residual updates and acquire nonzero low-rank continuation |
| OG-06 | Stage-A success analogues use only 60 calibration origins | Wrong sample length and weak participation fail closed |
| OG-07 | Evaluation access is limited to a ten-field pre-fit identity payload | Metric, label, estimator, result, and malformed-hash fields are rejected |
| OG-08 | Lock schema fixes implementation identity, counts, settings, metrics, and hashes before atomic creation | Incomplete, malformed, and overwrite attempts fail closed |
| OG-09 | Ledger requires exactly 60 ordered origins and all registered row fields | Missing, reordered, malformed, and invalid-hash rows fail closed |

## Corrected robust comparator

For observed set \(\Omega\), Run 030 implements

\[
L^{k+1}=\operatorname{SVT}_{1/\mu_k}\!\left[
\mathcal P_\Omega(X-S^k+Y^k/\mu_k)
+\mathcal P_{\Omega^c}(L^k)\right],
\]

\[
S^{k+1}=\mathcal P_\Omega\operatorname{soft}_{\lambda/\mu_k}
(X-L^{k+1}+Y^k/\mu_k),
\quad
Y^{k+1}=Y^k+\mu_k\mathcal P_\Omega(X-L^{k+1}-S^{k+1}).
\]

Thus a missing cell is neither a zero observation nor a sparse residual. It
is a low-rank continuation updated through the current singular subspace. The
solver retains the frozen multiplier grid \(\{0.5,1,2\}\), tolerance
\(10^{-8}\), multiplier growth 1.5, and 2,000-iteration ceiling.

## Verification evidence

- The immutable audit reports `ORCHESTRATION_IMPLEMENTATION_GATE_PASSED`.
- Fourteen focused test methods cover approval identity, all nine resolutions,
  invalid fields, nonconvergence, immutability, and forbidden imports.
- The focused orchestration module reaches 97% branch-aware coverage.
- The complete private suite discovers and executes 306 tests successfully;
  final coverage is rechecked after the documentation bundle is frozen.
- Ruff and strict mypy pass across the complete source tree.
- Static imports contain no transmission or outcome module.
- No official calibration fit or evaluation operation occurred.

## Scientific interpretation

The candidate contribution is now operationally coherent: a
duplicate-neutral authorization rule over auditable information-clock
ambiguity, with history-specific admissibility, common-space geometry,
structure-breaking controls, and a cryptographic two-stage firewall. This is
still a candidate methodological synthesis, not established novelty. Its
value now depends on the protected real-data calibration and later sealed
evaluation relative to B1, B2, and B3.

The implementation gate alone establishes no useful participation, improved
future measurement reliability, benchmark superiority, transmission effect,
or monetary-policy recommendation.

## Next gate

Commit and push the exact Run 030 implementation, verify the curated public
source-only test surface, and then exercise the already authorized Stage A
once from that clean implementation commit. Stop after auditing the immutable
calibration lock. Do not fit or inspect the evaluation block and do not access
transmission outcomes.
