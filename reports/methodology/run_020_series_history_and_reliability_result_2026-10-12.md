# Run 020 series-history pilot and reliability-definition result

**Date:** 2026-10-12
**Decision:** pilot passes; full panel remains unbuilt and unauthorized
**Data boundary:** real, freely retrievable official ECB samples only

## Result

Eleven exact ECB Data Portal series were queried under the frozen pilot, with
`includeHistory=true`, fixed sample dates, a five-megabyte per-series limit,
and no state estimation. The series span all eight registered economic
channels. The validator checked the official host, exact key, frequency, unit,
nonempty observations, history fields, byte size, and SHA-256 hash while
retaining no observation values in the aggregate audit.

The accepted timing classification is:

| Class | Series | Interpretation |
|---|---:|---|
| A -- replay eligible | 6 | Three RTD macro series, the deposit-facility rate, and two yield-curve maturities have the required history timestamps under the frozen rule. |
| B -- release-lag eligible | 4 | The exchange rate and three MIR/BSI series require conservative release-lag treatment. |
| C -- build forward only | 1 | New CISS remains unavailable for historical decision-time replay and is excluded from both panels. |
| D -- ineligible | 0 | No registered panel member failed the amended metadata and timing contract. |

P0 retains all seven declared series and five channels. P1 retains all ten
declared series and seven channels. Both are distinct and pass their frozen
pilot gates. This is a source-and-timing feasibility result only. It does not
show that the resulting factors are nondegenerate, stable, economically
oriented, high dimensional, or useful for monetary-policy transmission.

## Corrections preserved in the record

Attempt 1 failed scientific acceptance because the validator recorded but did
not enforce the frozen unit code. The unemployment response reports `PC`, not
the original manifest's `PC_ACT`; the code was hardened, the metadata-only
manifest amendment was frozen, and the same bytes were re-audited. The maximum
observation-to-version gap was also renamed from release delay to version delay
because later revisions are included.

Attempt 2 passed the scientific gates but serialized absolute host paths. It
was rejected as a nonportable and privacy-unsafe release artifact. The code now
resolves the project root from `pyproject.toml`, emits project-relative POSIX
paths, rejects artifacts outside the canonical project, and re-audits the same
immutable bytes. Neither correction changed a series, query, value, timing
class, panel, threshold, or result.

The full quality gate then exposed insufficient coverage of the new module and
a type-coercion edge case: YAML boolean `true` would satisfy Python's ordinary
integer check for the response-byte limit. The gate was not lowered. The parser
now requires an exact integer type, and end-to-end, mocked-download,
immutability, path-containment, panel-failure, response-schema, and hostile-
manifest cases raise the module to 96% branch-aware coverage. The canonical
suite passes 196 tests at the fixed 90% project floor.

## Methodological correction

The Run 019 concept compared loading projectors that could have different
feature coordinates and dimensions. Such projectors cannot be subtracted.
Run 020 replaces that object with a factor-score projector in a common 120-
month calendar space and a loading projector mapped into a frozen eight-
channel economic space. It also makes the secondary Frobenius normalization
rank aware when two panels select different factor counts. These changes fix
definition errors before implementation; they are not evidence of novelty or
performance.

## Scientific decision

The pilot succeeds narrowly. A later run may freeze a full retrieval and build
protocol for P0 and P1, but no full retrieval, factor estimation, threshold
selection, or transmission analysis is authorized by this result. The next
protocol must preserve exact series identifiers and timing classes, implement
the invariance tests, and keep monetary-policy outcomes sealed through the
one-time chronological evaluation.

## Evidence

- Frozen protocol: `research/methodology/run_020_series_history_and_reliability_protocol_v1.yaml`
- Definition amendment: `research/methodology/run_020_reliability_definition_amendment_2_protocol.yaml`
- Amended manifest: `research/data/run_020_series_pilot_manifest_v1_amendment_1.yaml`
- Accepted aggregate audit: `reports/methodology/run_020_series_history_pilot.audit.json`
- Rejected audits: `reports/methodology/run_020_series_history_pilot_attempt1.audit.json` and `run_020_series_history_pilot_attempt2.audit.json`
- Method definition: `research/methodology/run_020_information_set_reliability_method_v1.md`
