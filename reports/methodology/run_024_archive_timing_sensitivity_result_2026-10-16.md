# Run 024 — Archive identifiers and release-time sensitivity

## Decision

Accept the registered-clock and next-day panels as a valid outcome-blind
archive amendment. Use the registered clock as the reference panel and retain
the next-day clock as a mandatory reliability scenario. Do not fit the
reliability engine, select rank, evaluate authorization thresholds, or access
transmission outcomes in this run.

## Evidence and parser boundary

Run 024 reuses the nine exact bound inputs and all seventeen preserved Run 023
official responses. It performs no network retrieval and introduces no
synthetic empirical observation. The entry-local parser admits only exact
legacy MIR and BSI PDF identifiers after query removal, unique two-digit-year
resolution, and a strict requirement that the reference-month end precede the
release date. It does not infer periods from page order, modern identifiers,
annexes, partial matches, or average lags.

All eligible explicit-title overlaps agree with the identifier interpretation:
20/20 for MIR and 17/17 for BSI. Two pre-sample BSI candidates are counted and
excluded because the encoded reference month had not ended on the archive
date. There are no explicit-title/identifier disagreements.

## Coverage result

The in-sample release map grows from 108 to 264 MIR periods and from 104 to 271
BSI periods. Total archive maps contain 274 MIR and 329 BSI periods, including
out-of-sample evidence. P0 is byte-identical to Run 023. P1 retains 2,740 rows.

| Quantity | Run 023 | Run 024 registered | Change |
|---|---:|---:|---:|
| MIR NFC borrowing-cost observed origins | 255 | 261 | +6 |
| BSI adjusted NFC-loan observed origins | 102 | 260 | +158 |
| BSI M3 observed origins | 102 | 272 | +170 |
| Fully observed P1 origins | 102 | 123 | +21 |

The registered amendment changes 513 panel-origin-series keys: 334
missingness statuses, 484 selected observations, and 150 transformed values.
These categories overlap. Both panels retain zero duplicate keys, zero
non-finite values, and zero point-in-time violations.

## Release-time sensitivity

The registered clock combines the official release date with 10:00:01
Europe/Berlin. The conservative alternative uses 00:00:00 on the next calendar
day. Moving all 603 mapped MIR/BSI periods to the next-day clock changes 793
panel keys because stored usable timestamps change, but it changes only 24
selected observations and 23 transformed values. The affected values occur at
23 origin months corresponding to releases dated on the first calendar day.
There is no missingness-status change and no change to the fully observed
origin count in either panel.

The timing choice is therefore not numerically irrelevant: coverage is
invariant, while a small set of selected values changes. Both clocks must be
carried into later reliability evaluation.

## Corrections and failed attempts

- DEV-094 narrowed the identifier grammar before implementation after showing
  that modern MIR identifiers do not have uniform period semantics.
- Attempt 1 stopped on ECB navigation markup before any mapping or output was
  completed. DEV-095 made archive association entry-local and added page-
  chrome regression tests.
- Attempt 2 stopped when two pre-sample BSI filename candidates failed the
  frozen temporal validation. DEV-096 counts and excludes invalid candidates
  while retaining fatal disagreement and conflict checks.

Both failed attempts wrote neither the canonical panel directory nor the
canonical audit. Their machine-readable failure records are retained. The
accepted third attempt used unchanged source bytes, exact path grammars,
timing clocks, sample boundaries, and outcome firewall.

## Interpretation boundary

Run 024 materially strengthens panel feasibility and removes most of the
archive-induced BSI ragged edge. It does not demonstrate that the augmented
panel produces a reliable state, useful authorization, superior benchmark
performance, high-dimensional asymptotics, methodological novelty,
transmission heterogeneity, or monetary-policy value. Those claims require
separate frozen estimation and evaluation gates.

## Improvement opportunity requiring approval

The dominant remaining complete-case constraint is now the deposit-facility
rate, observed at 123/274 origins under the current API-history clock. An
independently sourced, official effective-date history could test whether the
pre-2015 policy-rate gap is a conservative metadata artifact. This must be a
separate source-contract amendment, with official effective dates, exact
hashes, a no-backfill rule, and registered-versus-current-clock comparison.

## Next gate

Recommended next step: approve a narrowly scoped Run 025 deposit-facility-rate
effective-date source audit and panel sensitivity before fitting the
reliability engine. If that source audit cannot produce a defensible free
official clock, retain the Run 024 panels and then prospectively freeze the
first empirical reliability run with both MIR/BSI timing variants.
