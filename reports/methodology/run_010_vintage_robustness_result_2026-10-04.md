# Run 010 matched-period latest-vintage robustness result

**Result date:** 2026-10-04  
**Evidence class:** real official ECB state data, outcome blind, ex-post latest vintage  
**Primary classification:** `LATEST_VINTAGE_ROBUST_INSTABILITY`  
**State selected:** no  
**Transmission authorized:** no

## Result

The Run 009 full-panel instability conclusion survives replacement of the three
point-in-time macro values with the latest official ECB RTD vintage while the
calendar origins, selected observation periods, original missingness/staleness
decisions, and deposit-facility series remain fixed. All 96-, 120-, and
144-month windows fail the unchanged joint geometry classification under both
vintages.

This rules out one important explanation for the Run 009 result: the negative
measurement conclusion is not an artifact of the stored point-in-time numerical
values alone. It does not validate the latest-vintage panel as a decision-time
state, estimate a causal effect of data revisions, identify a structural break,
or reopen the Run 008 state-selection gate.

## Full-panel geometry

| Rolling history | Vintage | Second-cosine p10 | Projector-distance p90 | Core-breach rate | Weak-identification coincidence | Failure |
|---:|---|---:|---:|---:|---:|---:|
| 96 | Point in time | 0.2192 | 0.7230 | 47.52% | 5.97% | Yes |
| 96 | Latest | 0.1702 | 0.7357 | 51.06% | 5.56% | Yes |
| 120 | Point in time | 0.1231 | 0.7175 | 36.17% | 17.65% | Yes |
| 120 | Latest | 0.0916 | 0.7194 | 36.88% | 23.08% | Yes |
| 144 | Point in time | 0.2511 | 0.6947 | 21.28% | 20.00% | Yes |
| 144 | Latest | 0.1896 | 0.7038 | 21.99% | 16.13% | Yes |

Relative to point-in-time values, the latest vintage lowers the second-cosine
10th percentile by 0.0490, 0.0315, and 0.0615 and raises the projector-distance
90th percentile by 0.0127, 0.0019, and 0.0091 for the 96-, 120-, and 144-month
windows. Core-breach rates rise by 3.55, 0.71, and 0.71 percentage points.
These are paired descriptive differences, not causal revision effects.

More than 99% of average squared Gram drift remains off diagonal in every
full-panel latest-vintage window. The prespecified weak-identification
coincidence rate stays below the 50% flag in every window. The vintage result
therefore reinforces the Run 009 interpretation that the failure reflects
unstable multivariate geometry rather than only missingness diagonals or the
specified weak-eigengap condition.

## Conditional dependent-summary uncertainty

The frozen paired circular block bootstrap gives the following 95% percentile
intervals at the primary 12-month block length:

| Window | Δ cosine p10 | Δ projector p90 | Δ breach rate |
|---:|---:|---:|---:|
| 96 | [-0.0884, 0.0096] | [-0.0128, 0.0342] | [-1.42, 12.09] pp |
| 120 | [-0.1519, 0.0156] | [-0.0033, 0.0263] | [0.00, 2.13] pp |
| 144 | [-0.4901, -0.0060] | [0.0002, 0.2511] | [0.00, 2.13] pp |

At 144 months, the primary-block intervals exclude zero in the direction of
lower cosine and higher projector distance. The 24- and 36-month sensitivity
intervals slightly cross zero for those statistics, so this cannot support a
strong inferential claim that the latest vintage worsens instability. The
bootstrap conditions on the fitted diagnostic sequences; it does not propagate
full factor-estimation or source-vintage uncertainty and supplies no p-values.
The robust classification itself does not depend on these intervals.

## Magnitude of matched-period value differences

| Feature | Rows | Median absolute difference | 90th percentile | RMSE | Pearson | Spearman | Median difference / development SD |
|---|---:|---:|---:|---:|---:|---:|---:|
| HICP year-over-year | 285 | 0.0129 pp | 0.0620 pp | 0.0546 pp | 0.9996 | 0.9984 | 0.0158 |
| Industrial production year-over-year | 274 | 0.6192 pp | 1.5108 pp | 0.9747 pp | 0.9868 | 0.9668 | 0.1005 |
| Unemployment rate | 270 | 0.1920 pp | 0.6105 pp | 0.3411 pp | 0.9879 | 0.9853 | 0.2041 |

HICP differences are small in this matched sample. Industrial production and
unemployment show materially larger ex-post differences, yet their rank and
linear correlations remain high. The latest RTD concepts may include rebasing,
benchmark, seasonal-adjustment, and euro-area-composition changes, so these
quantities must not be labeled pure numerical revisions.

## Persistent episodes

| Window | Point-in-time episode | Latest-vintage episode | Breach-month Jaccard |
|---:|---|---|---:|
| 96 | 2017-09–2023-03 | 2017-03–2023-02 | 0.9041 |
| 120 | 2019-03–2023-05 | 2019-02–2023-05 | 0.9808 |
| 144 | 2021-02–2023-07 | 2021-01–2023-07 | 0.9677 |

Each full-panel window retains one closed primary episode. The latest-vintage
episode begins six months earlier at 96 months and one month earlier at 120 and
144 months. These shifts are descriptive; the dated episodes are not estimated
causal break dates.

## Leave-one-feature-out sensitivity

The window-level classifications are identical across vintages for all 15
variant-window cells:

| Omitted feature | 96 months | 120 months | 144 months |
|---|---:|---:|---:|
| HICP inflation | Fail | Fail | Fail |
| Industrial production | Fail | Fail | Fail |
| Unemployment | Fail | Pass | Pass |
| Deposit-facility rate | Fail | Pass | Pass |

This preserves the Run 009 sensitivity pattern: deleting unemployment or the
deposit rate removes the 120/144-month classification but not the 96-month
failure. Deletion changes the measured system and does not identify a causal
driver or eligible replacement state.

## Integrity and reproducibility

- 1,144 unique month-feature comparison rows retain the required
  `EX_POST_LATEST_VINTAGE_NOT_DECISION_TIME` label.
- The original missingness mask is exact: one HICP, 12 industrial-production,
  and 16 unemployment rows remain missing.
- All 286 deposit-facility rows have exactly zero vintage difference.
- All 829 originally observed macro rows have finite matched-period differences.
- 4,950 unique vintage-variant-window-month geometry rows are present: 2,475
  point-in-time and 2,475 latest-vintage rows.
- Every point-in-time geometry metric and breach flag reproduces the frozen Run
  009 artifact within the prospective numerical tolerance.
- All required latest levels and 12-month lags have 100% coverage.
- No shock, return, response horizon, transmission outcome, or synthetic
  observation was accessed.
- The pre-result local Git checkpoint is `5e6e52e`.

## Limitations

The latest vintage is an ex-post production view and is unavailable at the
historical decision times. The comparison controls observation-period selection
and missingness but cannot isolate numerical revisions from rebasing,
benchmarking, seasonal-adjustment, or changing euro-area composition within the
RTD concept. The four-feature panel does not support high-dimensional break
asymptotics, and the block-bootstrap intervals are conditional diagnostic
summaries rather than confirmatory factor-model inference. Independent
reproduction and a focused comparison with the closest real-time
factor-stability literature remain necessary before strong contribution or
novelty language.

## Decision

Accept the prespecified `LATEST_VINTAGE_ROBUST_INSTABILITY` classification.
Preserve the Run 008 no-state decision and the Run 009 diagnostic unchanged.
Select no state and keep transmission sealed.
