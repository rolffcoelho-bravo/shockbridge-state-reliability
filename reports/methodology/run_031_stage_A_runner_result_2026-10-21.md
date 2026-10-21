# Run 031 — Typed Stage-A geometry and calibration transaction

**Status:** transaction and geometry gate passed; official fit not started  
**Date:** 21 October 2026  
**Evidence boundary:** approved methodology and hostile software fixtures only;
no official origin geometry, calibration result, evaluation label or metric,
or transmission outcome was accessed

## Decision

Accept the separate geometry and calibration-transaction layers as the next
prospective implementation checkpoint. Do not supply official geometry yet.
The complete origin-by-scenario panel generator remains a required pre-fit
gate and must bind exact panel bytes, provenance-to-analytic mappings, family
and timing operators, origin failures, and evaluation identities.

## Implemented transaction

The calibration layer requires exactly 60 ordered origin records and Boolean
matured labels. It materializes and hashes every decision vector on the frozen
(6\times6\times4=144) threshold grid before selection. The loss is

\[
\widehat L(\theta)=60^{-1}\sum_t
\left[A_t(\theta)Y_t+0.25\{1-A_t(\theta)\}\right].
\]

Primary, B1, B2, B3, NC1, NC2, and NC3 are selected through one typed
transaction. Comparator matching uses calibration participation only. B3
jointly considers multipliers 0.5, 1.0, and 2.0 and uses the lower multiplier
only as the last exact-tie rule.

## Geometry kernel

The geometry layer supports observed ragged-edge EM-PCA, complete-case fitting
with exact 120-month score recovery, and the corrected projected-observed-entry
PCP. Every history is standardized and filtered independently. It returns
rank-invariant anchor scalars, 120-month score projectors, eight-channel
projectors, anchor capture, selected rank, and represented-channel count.

The primary record takes maximum pairwise score/channel distances and minimum
anchor capture across all unique nondegenerate scenario-history fits. B2 uses
every unique nondegenerate primary analytic scenario at the origin and gives
provenance duplicates zero incremental weight.

## Anomalies corrected

1. The first Run 031 draft classified NC1/NC2 degradation using only
   participation and loss. This omitted the registered scenario-support and
   B1-matched future-failure analogues. The final implementation evaluates all
   four conditions before the control can count as degraded.
2. Manuscript Version 1.16 retained an obsolete 56-scenario statement in its
   conclusion. Version 1.17 corrects this to the frozen Run 026 ceiling of 88
   unique analytic scenarios after input-clock deduplication.
3. The explicit public-boundary registry did not yet list the Run 030 and Run
   031 private claim, citation, and manifest records. None had been published,
   but the omission could have exposed them in a later complete export. All
   six exact paths and a regression assertion are now registered.

## Verification

- Immutable audit status:
  `STAGE_A_TRANSACTION_AND_GEOMETRY_GATE_PASSED`.
- Ten focused hostile test methods pass.
- Focused branch-aware coverage: 96% for the calibration transaction and 95%
  for the geometry kernel.
- Complete private suite: 318/318 tests passed at 90% branch-aware coverage.
- Ruff and strict mypy pass.
- Static imports contain no evaluation, outcome, or transmission module.
- No official panel value entered an estimator in Run 031.

## Scientific interpretation

This checkpoint reduces researcher degrees of freedom and makes the
label-bearing operation small enough to audit directly. It is not evidence of
useful participation, benchmark superiority, future-failure reduction,
methodological novelty, or monetary-policy relevance. Those claims require the
protected real-data execution and, later, the one-time evaluation.

## Next gate

Implement and hostile-test the hash-bound origin-by-scenario generator. It
must construct the 60 calibration origins, future reference failures through
the embargo, 70 metric-free evaluation identity maps, all primary/comparator
and negative-control geometry, and the complete failure/provenance ledger.
Only after that generator passes may the official Stage-A transaction run
once and write the immutable calibration lock.
