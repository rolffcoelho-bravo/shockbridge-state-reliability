# Regular-calendar state-panel audit

**Run:** `monthly-state-panel-v1` and corrective `monthly-state-panel-v2`

**Date:** 2026-10-02

**Evidence class:** real data, outcome blind

## Objective

Construct a regular monthly information calendar so that latent-state transition dynamics are not indexed by irregular ECB meeting gaps. Both versions use the same four admitted real features and the same source hashes, vintage rules, staleness limits, and prohibition on synthetic observations.

## V1 feasibility failure

V1 placed checkpoints at the end of each month. This interacted mechanically with the conservative archive assumption—an archived vintage is usable only from the first day after its named month—and the existing 90/120-day staleness limits. HICP coverage fell to 63.6% and industrial-production coverage to 53.1%.

The result is retained as a failed design. The staleness thresholds were not relaxed after observing coverage.

## V2 correction

V2 places each regular checkpoint at 23:59:59 Europe/Berlin time on the first calendar day of the month. This lets the model use the latest vintage already established as available while keeping monthly spacing and all prior quality gates.

The accepted panel has 286 months, four features, and 1,144 rows. There are no timing violations or duplicate month-feature keys. Coverage is:

- HICP year-on-year: 285/286, or 99.65%;
- industrial production year-on-year: 274/286, or 95.80%;
- unemployment: 270/286, or 94.41%;
- deposit-facility rate: 286/286, or 100%.

Remaining gaps are explicit rather than imputed. The long unemployment gap from June 2024 through July 2025 reflects the already documented RTD vintage discontinuity and will be handled by estimators with native missing-data logic or complete-case sensitivity analysis.

## Decision

Accept `monthly-state-panel-v2` as the input to the outcome-blind Blueprint V2 model comparison. Do not use v1 for model estimation. No transmission outcome or response magnitude has been opened.
