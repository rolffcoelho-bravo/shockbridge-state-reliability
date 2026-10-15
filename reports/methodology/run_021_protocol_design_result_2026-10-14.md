# Run 021 full-panel protocol-design result

**Date:** 2026-10-14
**Run ID:** `run-021-full-panel-protocol-design-v1`
**Decision:** accept the audited design freeze; perform no retrieval or estimation

## Result

Run 021 converts the Run 020 feasibility result into a fail-closed
implementation and evaluation contract. The registered empirical universe is
ten real, freely retrievable official ECB series. Panel P0 contains seven
series across five channels; panel P1 contains ten series across seven
channels. This is a wider multichannel design, not a high-dimensional
empirical result.

The preflight verifies five hash-bound inputs, ten exact series, two panels,
seven represented channels, six replay-eligible and four release-lag-eligible
series, and a maximum of 56 admissible scenarios before exact deduplication.
It confirms that Run 021 performs no full-history retrieval, state estimation,
synthetic empirical construction, transmission-outcome access, or outcome
analysis.

## Corrections made before execution

1. Class-B timing is now series specific. FX uses the official publication
   clock; MIR and BSI require archived reference-period release timestamps.
   Missing evidence produces a missing value.
2. Retrieval lookbacks now cover every transformation. HICP and industrial
   production begin in January 2002 for a January 2003 panel start.
3. Ragged-edge rank selection now specifies deterministic EM-PCA, an
   observed-entry ICp2 adaptation, convergence, tie-breaking, and fixed-rank
   sensitivities.
4. One-time evaluation ends in October 2024, while the diagnostic tail ends in
   October 2025, so all twelve-month future-failure labels are mature.
5. Future failure is defined independently of the candidate envelope, and
   benchmark participation matching uses calibration data only.
6. The scenario ceiling is 56, not 112. The draft had counted the base-panel
   axis twice: `(6 + 8) × 2 × 2 = 56`.
7. The first preflight rejected malformed benchmark YAML before any data were
   retrieved. The corrected frozen file represents four benchmark mappings.

## Frozen evaluation design

Calibration spans January 2013 through December 2017, followed by a 2018
embargo. Evaluation spans January 2019 through October 2024, with a diagnostic
tail through October 2025. The comparator set is always abstain, the single
augmented P1 panel, equal-weight aligned panel combination, and robust PCA.
Primary success requires at least 10 percent participation, at least two
nondegenerate admissible scenarios at authorized origins, strictly lower loss
than P1, no higher future-failure rate at calibration-matched participation,
and passing invariance and negative controls.

## Prior-art and novelty boundary

A focused closest-prior-art update finds established precedents for real-time
data, ragged-edge factors, dataset selection, factor instability, projector
geometry, robust PCA, model uncertainty, and selective prediction. No exact
implementation of the registered official-information-set envelope was found
in the bounded search. That gap is a research opportunity, not proof of
priority. N06 remains
`CANDIDATE_METHODOLOGICAL_SYNTHESIS_NOT_CLAIMED` until real-data execution
beats the frozen comparators at useful participation, survives sensitivities,
and receives independent assessment.

## Evidence boundary and next gate

No empirical performance, reliable state, monetary-policy transmission
effect, mechanism, or methodological novelty is established. The next
permissible stage is a separately approved implementation-only run that builds
and adversarially tests the deterministic construction engine without
retrieving the full histories. Full retrieval requires another explicit
approval after that software gate passes.
