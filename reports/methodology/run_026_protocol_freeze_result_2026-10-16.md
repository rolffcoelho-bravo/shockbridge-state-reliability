# Run 026 — Information-clock reliability execution protocol freeze

**Status:** accepted protocol and fail-closed preflight; empirical execution pending
**Protocol frozen:** 16 October 2026
**Record finalized:** 17 October 2026
**Evidence class:** exact-byte governance over real, freely retrievable official ECB panels; no synthetic empirical observations
**Outcome boundary:** no reliability fit, evaluation result, transmission outcome, or policy-response outcome accessed

## Research question

Does an outcome-blind reliability certificate built over defensible official
ECB information clocks authorize a nondegenerate macro-financial state at
useful participation, and does it improve future internal measurement
reliability relative to preregistered single-panel and robust comparators?

Run 026 does not answer that question. It freezes the execution contract and
tests whether the exact inputs, information clocks, analytic equivalence
classes, scenario arithmetic, evaluation calendar, comparators, and claim
firewalls are internally consistent before any empirical fit.

## Inputs and preflight

The protocol binds twelve upstream method and evidence artifacts and all eight
Run 025 panel files by exact byte count and SHA-256. The panels contain 18,632
rows in total: four P0 files with 1,918 rows each and four P1 files with 2,740
rows each. The preflight rejects changed bytes, duplicate panel keys,
non-finite observed values, malformed missingness, a changed calendar,
unregistered comparators, a weakened firewall, or an unexpected analytic
class count.

| Preflight quantity | Verified result |
|---|---:|
| Bound upstream inputs | 12 |
| Source-clock provenance labels | 4 |
| Panel files | 8 |
| Panel rows | 18,632 |
| Exact analytic equivalence classes | 3 |
| Registered comparators | 4 |
| Focused contract tests | 11/11 passed |
| Contract-module branch-aware coverage | 90% |
| Evaluation labels matured | Yes |
| Reliability fit performed | No |
| Evaluation results accessed | No |
| Transmission outcomes accessed | No |
| Synthetic empirical observations used | No |

The accepted audit records protocol SHA-256
`78d562c4d2e20529f5609198721c4d2be85694544ca66f62a48132cf29216aeb`.

## Duplicate-neutral information-clock design

The four source-clock labels are indispensable provenance records, but they
are not four independent numerical inputs for each panel. For panel \(a\),
clock \(c\), and origin \(t\), define the analytic path \(x_{a,c,t}\) from
origin, series, selected observation period, transformed value, missingness,
and missing-reason fields. Then

\[
c\sim_a c' \quad\Longleftrightarrow\quad
x_{a,c,t}=x_{a,c',t}\ \text{for every registered origin }t.
\]

Provenance-only fields, including the stored usable timestamp, do not create a
new analytic realization. Under this rule:

1. all four P0 clock-labelled panels form one analytic class;
2. P1 under the registered MIR/BSI clock forms one class across both DFR
   clocks; and
3. P1 under the next-day MIR/BSI clock forms one class across both DFR clocks.

The design retains every label in the output mapping but assigns one
multiplicity weight to each exact analytic class. Clock labels are never
resampled as observations; paired moving-block inference resamples monthly
origins.

## Scenario arithmetic

Before deduplication, the source-labelled generator has

\[
(6+8)\times4\times2\times2=224
\]

paths: six P0 and eight P1 full/leave-one-channel-out families, four clock
labels, two release-lag policies, and two missingness policies. After exact
input-clock deduplication, the ceiling is

\[
(6\times1+8\times2)\times2\times2=88.
\]

The engine must then deduplicate exact origin-specific eligibility masks and
standardized observed matrices. Exact provenance duplicates cannot satisfy the
minimum-two-scenario authorization rule. This prevents timestamp variants from
artificially increasing the ambiguity set while retaining source-clock
traceability.

## Frozen evaluation and comparator contract

The protocol preserves the Run 021 design: 2013–2017 calibration, a full 2018
embargo, one-time January 2019–October 2024 evaluation, a diagnostic tail only
through October 2025, and a twelve-month future internal-failure label. The
four comparators are always abstain, the registered-clock P1 single panel, an
equal-weight combination over unique analytic classes, and robust PCA.
Participation matching is fixed from calibration data only.

Primary success requires at least 10% evaluation participation, at least two
unique nondegenerate analytic scenarios at authorized origins, strictly lower
decision loss than the single-panel comparator, no higher future-failure rate
at calibration-matched participation, authorization invariant across all four
provenance clocks, and no negative-control or invariance failure. Failure of
any condition is a reportable non-improvement, not a license to retune.

## Audit corrections

Two pre-execution defects were corrected and recorded. DEV-102 repaired two
YAML objects that had been nested inside lists; the parser failed before any
fit. DEV-103 resolved the command-line protocol path before relative-path
serialization and added a regression test. Neither correction changed an
input, threshold, panel, comparator, scenario rule, or empirical result.

DEV-104 records the focused-coverage review that raised the contract module
from 81% to 90% branch-aware coverage. The public software tests construct
explicitly labelled synthetic fixtures
only to exercise parsing, integrity, deduplication, and hostile-input paths.
They are not observations, are not stored as empirical artifacts, and carry no
weight in any scientific result.

## Scientific interpretation

Run 026 makes the candidate contribution more precise: an official-clock
ambiguity set must be duplicate neutral, evaluated in common calendar and
economic-channel spaces, judged against registered comparators, and separated
from transmission outcomes by a hard firewall. This is a protocol result only.
It establishes neither empirical reliability nor novelty. Principal
components, ragged-edge EM-PCA, information criteria, projector geometry,
Procrustes alignment, robust PCA, abstention, and block resampling remain
established components.

## Recommended next improvement — approval required

Implement the empirical execution harness against this exact contract. First
run calibration and embargo logic, freeze the selected threshold and
origin-level scenario identity records, and only then open the one-time
reliability evaluation. Preserve all four provenance mappings, fit each unique
analytic path once, retain all negative controls and registered comparators,
and keep transmission outcomes inaccessible. The execution should stop and
report non-improvement if participation or comparator gates fail.
