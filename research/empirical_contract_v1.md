# Empirical contract v1 — review companion

**Status: BLOCKED, not frozen.** The machine-readable contract is `empirical_contract_v1.yaml`. Its unresolved fields deliberately prevent real-data causal estimation.

## Provisional design decision

The first candidate is the press-release `target` factor derived from the Euro Area Monetary Policy Event-Study Database methodology. It is preferred over the press-conference QE factor for the first baseline because the inspected target file is complete across 242 unique dates, whereas QE is present for only 99 of 237 press-conference dates.

The scheduled-decision replication sample is deliberately frozen at 2025-10-30 rather than described as a live dataset. The official EA-MPD workbook and its hash are now recorded. A separate official EA-EMPD extension, published on 2026-06-10, contains events through 2026-03-28. The extension is a separate research lane because it includes speeches and uses event definitions that cannot be pooled mechanically with Governing Council announcements.

## What is fixed

- euro area is the first region;
- state variables use information available immediately before the announcement;
- filtered state probabilities are required; full-sample smoothed state labels are prohibited;
- event-time and subsequent daily horizons are separate estimands;
- the confirmatory event-time outcomes are the Italy–Germany 10-year spread change, STOXX50 change, and EUR/USD change;
- the target-factor/official-outcome join contains 242 events with no missing values in the selected outcomes;
- the outcome-blind state panel contains 1,210 rows with zero point-in-time violations and zero duplicate event-feature keys;
- exact RTD, policy-rate, and yield-curve series are hash-registered; CISS is excluded because its inspected history is only documented in post-sample replacement vintages;
- macro staleness limits and explicit missingness are frozen before state estimation;
- raw ECB workbooks are fetch-only and excluded from version control; derived displays require attribution and transformation disclosure;
- the state-independent response is the primary challenger;
- a reliability label can enter fitting only after its outcome matures;
- no real-data claim is permitted while the contract status is `BLOCKED`.

## What remains unresolved

- event exclusions and concurrent-news classifications;
- final chronological split dates;
- outcome-blind state-estimator selection and observed probability-weighted support;
- economic-unit smallest effect and power-based minimum support per state;
- task-specific loss/failure threshold.

## Acceptance gate for `FROZEN`

Every required field must be concrete, the source catalog must record retrieval and redistribution separately, the identification memo must have no P0 blocker, and a power simulation must show that the proposed state contrast is estimable at the planned complexity.
