# Run 009 state-instability diagnostic result

**Result date:** 2026-10-03
**Evidence class:** real point-in-time state data, outcome blind
**State selected:** no
**Transmission authorized:** no

## Result

The prespecified full-panel classification is **pervasive geometry failure**. Expanding-versus-rolling factor spaces fail the joint tail references for every 96-, 120-, and 144-month window. The failure is not classified as prespecified weak identification: fewer than 50% of breach months combine a relative eigengap below 0.20 with a perturbation-to-gap ratio above 1.00 in every full-panel window.

This is a measurement-reliability result. It does not identify a monetary-policy transmission effect, a structural break, or a causal source of instability. It does not alter the Run 008 kill gate or select a state.

## Frozen full-panel classifications

| Rolling history | Second-cosine p10 | Projector-distance p90 | Core-breach rate | Weak-identification coincidence among breaches | Window failure |
|---:|---:|---:|---:|---:|---:|
| 96 months | 0.2192 | 0.7230 | 47.52% | 5.97% | Yes |
| 120 months | 0.1231 | 0.7175 | 36.17% | 17.65% | Yes |
| 144 months | 0.2511 | 0.6947 | 21.28% | 20.00% | Yes |

All three windows fail because the second-cosine 10th percentile is below 0.90 and projector-distance 90th percentile is above 0.35. All weak-identification coincidence rates remain below the frozen 50% flag.

## Persistent episodes

| Rolling history | Primary episode | Duration | Breach months | 1/1 and 6/6 sensitivity |
|---:|---|---:|---:|---|
| 96 months | September 2017–March 2023 | 67 | 67 | Same continuous episode |
| 120 months | March 2019–May 2023 | 51 | 51 | Same continuous episode |
| 144 months | February 2021–July 2023 | 30 | 30 | Same continuous episode |

The episodes are not isolated threshold crossings. Each full-panel episode is continuous and unchanged under the 1/1, 3/3, and 6/6 persistence definitions.

An exploratory calendar observation is that the rolling histories begin in September 2009, March 2009, and February 2009 at their respective episode onsets. That alignment was noticed after Run 009 results and is not a prespecified break estimate. It may motivate a separate prospective diagnostic but cannot be reported as causal evidence.

## Matrix-drift attribution

The diagonal availability component averages only 0.59%, 0.62%, and 0.32% of squared Gram drift for the 96-, 120-, and 144-month comparisons. More than 99% is therefore off-diagonal comovement drift under this descriptive decomposition, not the mechanical diagonal effect of changing feature availability.

Feature pairs involving the deposit-facility rate account for 62.97%, 67.57%, and 72.54% of mean squared Gram drift across the respective windows. The largest individual pair is unemployment–deposit rate at 96 and 120 months; at 144 months, unemployment–deposit rate and industrial-production–deposit rate are similarly important. These are contribution shares, not causal attributions.

Standardization drift is also largest for the deposit-facility rate. Its median absolute location shift is 1.075, 0.538, and 0.310 pooled-standard-deviation units for the 96-, 120-, and 144-month windows. Its median absolute log-scale ratio is 1.266, 0.191, and 0.068. This affects scalar-score comparability but does not mechanically explain window-standardized PCA geometry.

## Leave-one-feature-out sensitivity

| Omitted feature | 96 months | 120 months | 144 months |
|---|---:|---:|---:|
| HICP inflation | Fail | Fail | Fail |
| Industrial production | Fail | Fail | Fail |
| Unemployment | Fail | Pass | Pass |
| Deposit-facility rate | Fail | Pass | Pass |

Removing either unemployment or the deposit-facility rate eliminates the frozen geometry-failure classification at 120 and 144 months, but not at 96 months. Removing HICP or industrial production does not eliminate failure at any window. Because deletion changes both the panel and the two-dimensional subspace inside a three-feature space, this is evidence of sensitivity to the labor-policy block, not identification of a unique driver or a replacement state.

## Scalar-sign materiality

The frozen Run 008 scalar has 23 sign disagreements across 141 common origins, or 16.31%. At the primary 0.25 standardized-unit materiality threshold, only one disagreement is substantive: 0.71% of all origins and 4.35% of sign disagreements. The 0.10 sensitivity gives 17 substantive disagreements (12.06% of origins), while the 0.50 sensitivity gives none.

This qualifies the Run 008 scalar sign-gate failure: most disagreements occur near zero, but the qualification does not retrospectively change the gate or make the scalar eligible.

## Policy-rate regimes

The common sample contains 97 negative-rate, 7 zero-rate, and 37 positive-rate origins in every window. Breach rates differ descriptively across these periods. For example, the 96-month breach rate is 60.82% in negative-rate months and 16.22% in positive-rate months. These regimes are strongly ordered in calendar time and were not randomized; no causal policy-regime interpretation is permitted.

## Integrity and reproducibility

- 2,475 unique variant-window-origin diagnostic rows and 44 episode rows were retained.
- Every variant-window cell has 141 common origins.
- All serialized geometry fields are finite.
- Every full-panel drift-contribution matrix is upper triangular and sums to one, except an exact-zero matrix where permitted.
- Independent recomputation matches every stored percentile, rate, and classification to persisted precision.
- A repeat execution is byte-identical for all three outputs.
- No shock, asset return, response horizon, or transmission-outcome field is present.
- The frozen pre-result code checkpoint is `235323b2a4e422e8316bdcb0698d7a4257f993e6`.

## Limitation discovered after execution

The episode output records duration and breach-month count but does not include an explicit right-censoring flag. One nonprimary deletion sensitivity—the omit-industrial-production, rolling-144, 6/6 rule—has 55 breach months in a 60-month episode because five stable months occur before the sample ends, one short of the six-month recovery rule. The stored values are correct, but an explicit `open_at_sample_end` field would make future outputs less ambiguous. Any correction must be an amendment; the immutable Run 009 v1 artifacts will not be overwritten.

## Decision

Run 009 strengthens the prospective negative measurement result: instability is persistent, pervasive across full-panel window lengths, dominated descriptively by off-diagonal comovement changes, and not concentrated in the prespecified weak-eigengap condition. No state is selected. Transmission remains sealed.
