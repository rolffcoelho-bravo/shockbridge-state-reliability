# Run 005 — regular monthly state calendar

**Date:** 2026-10-02

**Milestone:** 2, baseline state engine

**Status:** point-in-time calendar accepted; model comparison not yet executed

## Completed

- implemented a hash-frozen monthly panel configuration and reproducible builder;
- generated 286 monthly checkpoints from January 2002 through October 2025;
- preserved a failed month-end calendar whose coverage was incompatible with frozen staleness rules;
- corrected the calendar to month-start checkpoints without relaxing staleness, imputing data, or accessing outcomes;
- produced a 1,144-row accepted panel with zero timing violations and high real-data coverage;
- recorded both artifacts, audits, manifests, results, and the methodological deviation.

## Acceptance boundary

This run establishes a valid information calendar only. It does not select a state estimator and provides no evidence about monetary-policy transmission.

## Next gate

Execute the four frozen Blueprint V2 benchmarks—PCA plus clustering, dynamic factor, HMM, and change point—using filtered or strictly historical state assignments. Compare prequential performance, stability, interpretability, temporal support, and sensitivity to two versus three states before selecting any primary model.
