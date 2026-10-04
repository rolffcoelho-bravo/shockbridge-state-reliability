# Point-in-time pre-event state panel protocol

**Status:** candidate point-in-time panel built and audited. No latent states or transmission effects have been estimated.

## Unit of analysis

The panel has one information snapshot for each of the 242 frozen target-factor events. Every feature value carries its observation period, first usable timestamp, vintage, source hash, transformation, and age at the event cutoff. The event cutoff is immediately before the scheduled ECB press-release window in Europe/Frankfurt time.

The admissibility condition is strict:

```text
first_usable_timestamp < state_cutoff_timestamp
```

A value dated before an event can still violate this rule if it was released or revised after the event.

## Two source clocks

Market variables use the last fully observed value before the event. An event-day close is prohibited because it contains post-announcement information. Macro variables use the latest public release and vintage available before the event. A later revised observation cannot replace the value that an analyst could have observed at that time.

When an exact release timestamp is unavailable, the source audit must use a conservative availability time and disclose the convention. The project will not infer a precise intraday timestamp from a date-only source.

## Compact feature design

The candidate panel contains four admitted features: deposit-facility rate, HICP year-over-year inflation, industrial-production year-over-year growth, and the unemployment rate. The 10-year minus 2-year ECB yield-curve slope is retained as a conditional challenger because the current API history does not expose observation-level vintages. Each added family needs a distinct economic role and an ablation test. This restriction reduces researcher degrees of freedom and preserves effective sample size.

New and legacy CISS series were audited and excluded from the causal panel: the inspected historical observations carry only post-sample replacement timestamps (2026-10-01 for New CISS and 2025-04-15 for legacy CISS). They may appear in ex-post description but cannot define a decision-time state without an independently archived vintage history.

## Missingness and transformations

Future backfilling is prohibited. Carry-forward is allowed only after a value has been released and only until the next vintage. Maximum observation ages are 90 days for HICP and 120 days for industrial production and unemployment. Stale values become explicit missing rows; they are not silently carried forward. Age at the event cutoff is always retained. Scaling, dimension reduction, and any outlier rule are fit using admissible historical data only.

Raw point-in-time values remain separate from transformed values. The transformation parameters used for each event must be reproducible from the stored as-of history.

## State replay

The state engine must produce filtered probabilities from an expanding or rolling historical replay. Full-sample smoothed probabilities can be used only for ex-post description. Hard state labels are descriptive; the primary transmission design uses state probabilities and propagates state-stage uncertainty by refitting the state model inside a bootstrap or by using posterior draws.

The first candidate is a two-state model. A three-state specification is a sensitivity analysis only if observed support passes the frozen power rule. State labels are aligned across refits using development-period descriptors to prevent label switching from masquerading as a state transition.

## Outcome firewall

State data and state-model screening remain outcome-blind. The only outcome information already used is the recorded schema, units, and missingness coverage from the source audit. No outcome sign, magnitude, interaction, or model fit may influence series admission or the state estimator before the state contract and identification memo are frozen.

The build reads only the `date` field from the target-factor file. The `target` field is deliberately not parsed. The resulting local panel has 1,210 rows (242 events by five features), zero point-in-time violations, and zero duplicate event-feature keys. Its source registry is `research/state_sources_v1.yaml`; the local raw and processed artifacts remain ignored pending artifact-level redistribution decisions.

## Required support report

Before state-estimator selection, report hard counts, probability-weighted effective sample size, posterior entropy, shock sign and dose support, and event leverage for every state and chronological block. A row count alone is insufficient. If the minority state cannot support the smallest economically meaningful interaction after measurement error, simplify the state model or narrow the claim.
