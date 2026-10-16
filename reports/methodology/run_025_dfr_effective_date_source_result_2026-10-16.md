# Run 025 — Deposit-facility effective dates and source-clock envelope

**Status:** accepted source audit and panel amendment  
**Date:** 16 October 2026  
**Evidence class:** real, freely retrievable official ECB data; no synthetic empirical observations  
**Outcome boundary:** no transmission outcome accessed; no state or reliability model fitted

## Research question

The bound ECB Data Portal response records database-validity metadata for the
deposit-facility-rate series. Run 025 asks whether a separate official source
establishes the economic effective dates prospectively enough to remove the
artificial pre-2015 panel gap without weakening the point-in-time contract.

The protocol was committed before the canonical source retrieval. It binds the
official locator, parser semantics, exact-decimal cross-validation, acceptance
thresholds, four-scenario clock grid, output paths, and claim firewall. The
locator and visible table semantics had been inspected before protocol freeze;
the canonical response bytes, their hash, parsing result, comparison result,
and panel consequences were not known at freeze. The protocol makes this
limited pre-freeze inspection explicit.

## Official sources

- [ECB key interest rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html), whose policy table labels dates “Date (with effect from)” and reports rate levels in percentages per annum.
- [ECB Data Portal deposit-facility-rate series](https://data.ecb.europa.eu/data/datasets/FM/FM.D.U2.EUR.4F.KR.DFR.LEV), retained from Run 023 as the daily comparison path.

The canonical HTML response contains 131,224 bytes and has SHA-256
`fddef164d35d6dcd67adc614234f093435c2fd019af48e97f69c1d41b176066e`.
The response is preserved privately; the public research surface may expose
the locator, metadata, hash, code, and aggregate audit but not redistribute the
source bytes or processed observations.

## Method

For ordered official events \(\{(e_j,r_j)\}_{j=1}^{J}\), the implied daily
rate is

\[
r(d)=r_j \quad \text{when} \quad e_j\le d<e_{j+1}.
\]

The parser must identify exactly one table carrying the required effective-
date, deposit-facility, and unit semantics. It admits only the declared date
and typographic variants, requires a 6 December 2002 baseline, and fails on
ambiguous or conflicting rows. Values remain exact decimals. The API
`VALID_FROM`/`VALID_TO` and action fields reconstruct only the active retained
database snapshot; they do not define the economic policy clock.

The accepted scenario grid is the Cartesian product of:

1. registered versus next-calendar-day MIR/BSI release timing; and
2. official-effective-day versus next-calendar-day DFR timing.

Every scenario rebuilds P0 and P1. Non-DFR rows must remain exactly unchanged,
and the run must stop on duplicate keys, non-finite transformed values,
point-in-time violations, or any source cross-validation failure.

## Results

| Audit quantity | Result |
|---|---:|
| Official effective-date events | 51 |
| Event span | 2002-12-06 to 2025-06-11 |
| Retained API days compared | 8,366 |
| Exact decimal agreements | 8,366 (100%) |
| Conflicting or unmatched API days | 0 |
| Unmatched official events | 0 |
| Bound inputs verified | 8 |
| Clock scenarios / panel files | 4 / 8 |
| Duplicate keys / non-finite values / timing violations | 0 / 0 / 0 |
| Non-DFR rows changed | 0 |

| Panel consequence | Run 024 | Run 025 | Change |
|---|---:|---:|---:|
| DFR observed origins | 123 | 274 | +151 |
| First usable DFR origin | 2015-08 | 2003-01 | −151 months of missingness |
| Fully observed P0 origins | 123 | 179 | +56 |
| Fully observed P1 origins | 123 | 179 | +56 |

All four source-clock scenarios have the same DFR missingness and transformed
values. Effective-day versus next-day DFR timing changes 274 stored usable
timestamps but zero selected observation periods, zero transformed values, and
zero missingness states. This is not a claim that timing is irrelevant: Run
024 found that the MIR/BSI clock changes 23 transformed values, so both archive
clocks remain required. The DFR finding is specifically a monthly-selection
invariance under the registered origin calendar.

The complete-case share rises from 123/274 (44.89%) to 179/274 (65.33%), a
20.44 percentage-point increase. The gain removes a metadata-validity artifact
and leaves the yield-curve start in 2010-12 as the binding complete-case
boundary. It improves the feasibility of the planned empirical comparison but
does not validate the reliability envelope.

## Corrected reporting anomaly

The first uncommitted execution correctly measured 274 timestamp differences
and zero value/missingness differences, but labeled all complete-row
differences as `selection_changes`. That wording could overstate the economic
effect. Before acceptance, the output was regenerated with separate timestamp,
observation-period, and value/missingness fields. The superseded attempt is
preserved in
`reports/methodology/run_025_attempt_1_comparison_label_correction.audit.json`.
The frozen protocol, source bytes, parser rules, panels, and scientific result
were unchanged.

## Scientific interpretation

Run 025 establishes that the pre-2015 DFR gap was an artifact of treating
database-record validity as economic availability. It also establishes that
the official effective-date history is internally exact against every retained
daily API value. This is stronger provenance and a larger outcome-blind sample,
not a positive state or policy result.

No standardization, rank selection, factor estimation, scenario scoring,
authorization, comparator test, high-dimensional result, novelty claim,
transmission estimate, or policy recommendation is authorized by this run.

## Recommended next improvement — approval required

Freeze a Run 026 empirical reliability-envelope protocol over these four
source-clock scenarios before any factor fit. The protocol should convert
source-clock ambiguity into an explicit authorization requirement: a state may
be authorized only when rank, orientation, common-calendar geometry,
common-channel geometry, future internal-failure performance, and useful
participation survive both archive clocks and both DFR clocks. It should retain
the four registered comparators and the transmission-outcome firewall.

This would be the first real-data test of the proposed information-set
reliability synthesis. A separate focused literature update should accompany
the execution before any novelty language is reconsidered.
