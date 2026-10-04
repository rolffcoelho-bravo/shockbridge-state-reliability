# Run 002 — official ECB source ingestion

**Date:** 2026-10-02  
**Scope:** source recency, rights decision, schema audit, and paper evidence preservation

## Completed

- captured and hashed the official EA-MPD and EA-EMPD workbooks in ignored local storage;
- implemented HTTPS-only atomic retrieval with optional hash enforcement;
- implemented separate structural audits for both workbook formats;
- recorded manifests, source rights policy, timing breaks, outcome coverage, and anomalies;
- verified a 242-event target-factor join with zero missing values in all proposed outcomes;
- established an append-only scientific evidence ledger and decision log;
- replaced the vague “stale dataset” limitation with a frozen replication sample and a separately identified 2026 extension.

## Claims still blocked

- state-dependent causal heterogeneity;
- state-support sufficiency and statistical power;
- any reliability probability;
- any benefit from pooling speech and Governing Council events.

## Next acceptance gate

Build the point-in-time pre-event state panel, record release/vintage timestamps, and run a design-stage power/overlap study before choosing the state estimator or final chronological split.

## Highest-value next improvements

1. Create a simulation calibrated to the observed shock distribution and plausible minority-state prevalence, with state-measurement error explicitly varied.
2. Reconcile the EA-EMPD `Outside_regular_trading_hours` documentation conflict before using the flag in exclusions or controls.

