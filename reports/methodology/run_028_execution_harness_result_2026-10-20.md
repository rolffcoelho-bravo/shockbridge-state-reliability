# Run 028 — Outcome-blind reliability execution harness

**Status:** implementation gate passed; official calibration requires a
separate prospective authorization  
**Date:** 20 October 2026  
**Evidence boundary:** approved methodology and software fixtures only; no
official value fitted, no evaluation result inspected, no transmission outcome
accessed, and no synthetic observation used as empirical evidence

## Decision

Accept the Run 028 execution harness as the unique implementation of the
approved Run 027 reliability amendment. All eleven critical gaps identified
by the Run 027 semantic audit now have explicit, adversarially tested software
operators. Preserve the Run 026 protocol unchanged. Do not begin official
calibration until a separate prospective authorization is recorded.

This is an implementation result, not a positive reliability result. It
reduces unreported researcher discretion and makes later calibration and
one-time evaluation independently auditable.

## Executable resolution map

| Gap | Frozen implementation | Hostile verification |
|---|---|---|
| XG-01 | Exact origin-by-series matrix with complete registered grid | Rejects missing and duplicate origin-series cells |
| XG-02 | Deterministic one-month class-B slow-release stress | Checks value suppression and missing-reason transitions |
| XG-03 | Complete-row loadings with weighted score recovery on the exact final 120 origins | Checks successful recovery and rank-deficient failure |
| XG-04 | Connected-component redundancy graph with frozen representative tie-break | Checks order invariance and deterministic selection |
| XG-05 | Rank-invariant signed-channel anchor | Checks orthogonal rotation invariance at ranks 1, 2, and 3 |
| XG-06 | Separate expanding-history eligibility and rolling-120 comparison keys | Checks both history roles and fail-closed calendar identity |
| XG-07 | Observed-entry stable-PCP plus calibration-only threshold and participation matching | Checks solver behavior and all tie-breaks |
| XG-08 | Structure-breaking channel and temporal controls; pure relabelings retained as invariances | Checks deterministic transformations |
| XG-09 | Numerical control-failure rules | Checks acceptance and rejection boundaries |
| XG-10 | PCG64 non-circular moving-block plan and simultaneous intervals | Checks exact replay and boundary-safe blocks |
| XG-11 | Immutable calibration lock and atomic single-use evaluation marker | Checks identity binding, overwrite refusal, and second-start refusal |

## Core mathematical operators

For observed coordinates \(O_t\), the score-recovery operator is

\[
\widehat f_t=\arg\min_f
\sum_{j\in O_t} w_j^2(z_{tj}-\lambda_j'f)^2.
\]

For loading image \(G_s\) and the all-positive direction \(h\) after the
registered series signs are applied, the cross-rank anchor is

\[
\beta_s=(G_s'G_s)^\dagger G_s'h,\qquad
c_s=\lVert G_s\beta_s\rVert_2,\qquad
q_{t,s}=f_{t,s}'\beta_s.
\]

The robust comparator uses observed-entry principal-component pursuit,

\[
\min_{L,S}\ \lVert L\rVert_*+\lambda\lVert S\rVert_1
\quad\text{s.t.}\quad
\mathcal P_\Omega(L+S)=\mathcal P_\Omega(Z),
\]

with the multiplier grid, convergence rule, loss, and tie-break frozen before
official calibration.

## Verification evidence

- The immutable audit reports `IMPLEMENTATION_GATE_PASSED`.
- Every gap XG-01 through XG-11 appears in the machine-readable implementation
  surface.
- Fifteen focused hostile tests pass using software fixtures only.
- Static import inspection finds no transmission or outcome module in the
  harness dependency surface.
- The unchanged Run 026 protocol SHA-256 is
  `78d562c4d2e20529f5609198721c4d2be85694544ca66f62a48132cf29216aeb`.
- The approved amendment SHA-256 is
  `cda763f5102d6491dfce4d3b0687cf5729089e156cf2cac59be716fb04655899`.
- The audit records `official_values_accessed=false`,
  `evaluation_results_accessed=false`, and
  `transmission_outcomes_accessed=false`.

## Scientific interpretation

The candidate methodological contribution is now executable: a
duplicate-neutral, information-clock reliability certificate that separates
expanding admissibility from rolling comparison, supports unequal factor
ranks in a common signed-channel direction, benchmarks observed-entry robust
decomposition, uses structure-breaking falsification controls, and enforces a
hash-chained calibration/evaluation firewall. These elements form a coherent
candidate synthesis; their individual ingredients are established methods.

The implementation alone does not establish novelty, useful participation,
lower future-failure risk, benchmark superiority, or monetary-policy value.
Those claims require the protected real-data calibration and evaluation,
followed by a focused prior-art audit and independent assessment.

## Next decision — approval required

Authorize official Stage-A calibration under the unchanged Run 026 protocol
and the exact Run 028 harness. The authorized run should mature calibration
labels through the 2018 embargo, freeze the selected thresholds, comparator
settings, scenario identities, and calibration metrics in an immutable lock,
and stop for audit before any one-time evaluation access. Transmission outcomes
must remain sealed regardless of the calibration result.

