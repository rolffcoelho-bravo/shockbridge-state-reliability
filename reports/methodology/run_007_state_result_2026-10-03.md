# Run 007 outcome-blind state-model result

**Execution date:** 2026-10-03  
**Data:** real, freely retrievable point-in-time state variables  
**Transmission outcomes accessed:** no  
**Decision:** kill gate activated; no primary state representation selected

## What was executed

Run 007 used the frozen 286-month panel from January 2002 through October 2025. Each of 226 forecast origins per history window was estimated without future observations. The run produced 452 continuous-factor rows, 2,712 challenger rows, and 27,120 complete restart/sensitivity records. Expanding and rolling histories that were still mechanically identical were retained for predictive scoring but excluded from the cross-window stability gate, leaving 165 genuinely distinct paired origins.

The empirical run used no synthetic observations. Synthetic arrays remained confined to software tests. No shock series, asset-price response, outcome horizon, or transmission outcome was loaded.

## Frozen factor decision

Every one of the eight frozen gates was required. Four pass and four fail:

| Metric | Estimate | Frozen requirement | Result |
|---|---:|---:|---|
| Pearson correlation | 0.8962 | at least 0.80 | Pass |
| Spearman correlation | 0.8713 | at least 0.80 | Pass |
| Sign disagreement | 0.1091 | at most 0.10 | **Fail** |
| Standardized mean absolute difference | 0.2975 | at most 0.35 | Pass |
| Median loading cosine | 0.9873 | at least 0.90 | Pass |
| Minimum loading cosine | -0.6002 | at least 0.75 | **Fail** |
| Weaker-window anchor 10th percentile | 0.0932 | at least 0.20 | **Fail** |
| Weaker-window weak-anchor rate | 0.1091 | at most 0.05 | **Fail** |

The expanding factor has a strong anchor throughout: its anchor 10th percentile is 0.7131 and it has no weak-anchor origins. The rolling factor has 18 weak-anchor origins out of 165, a minimum anchor of 0.0010, and an anchor 10th percentile of 0.0932. There are 18 sign disagreements, concentrated from February–November 2018, February 2019, and March–September 2021. Thirty-eight origins fall below the 0.75 loading-cosine gate. The worst loading disagreement occurs in March 2021 and persists across subsequent months, so the minimum-cosine failure is not an isolated numerical point.

This pattern is consistent with a rolling first principal component whose economic orientation becomes weak and whose loading vector rotates materially relative to the expanding estimate. It does not establish a structural break or its cause; that would require a separately designed analysis.

## Predictive and challenger evidence

The continuous factor improves cumulative joint feature density over the diagonal-Gaussian benchmark by 288.37 log-score units in the expanding window and 191.08 in the rolling window. Under the frozen protocol, these gains cannot compensate for a stability failure.

The diagnostic HMM converges at every reported origin. Its three-state cumulative feature log score is -1481.42 expanding and -1585.65 rolling, compared with -1651.14 and -1971.94 for the continuous factor. These results do not authorize promotion: the HMM was declared diagnostic, and selecting it after seeing Run 007 would be post-result model choice. Objective-weighted restart agreement remains high, but all-start agreement can be materially lower.

PCA challengers show weak restart reliability at some origins: minimum aligned agreement ranges from 0.1417 to 0.3606 across state-count/window variants. Exact scalar-factor clusters are deterministic and descriptive. Their scalar-factor density is not dimensionally comparable with the four-feature factor, PCA, or HMM densities.

## Integrity audit

- All 3,164 empirical estimate rows are finite.
- Maximum state-probability sum error is `6.44e-15`.
- Expected provenance counts are exact: 18,080 PCA restart records, 5,424 HMM restart records, and 3,616 HMM objective-gap records.
- The independent recomputation matches every reported stability metric and gate.
- Output hashes and byte sizes are frozen in `state_model_run007_v1.manifest.yaml`.
- No `.part` file remains.
- The run began from clean local commit `d6979df83592f8bc822bff69d2361d51074d5862`.

## Scientific interpretation boundary

Run 007 rejects the proposed one-dimensional continuous factor as a stable primary conditioning variable. It makes no statement about state-dependent shock transmission, causal amplification, market predictability, portfolio performance, or economic mechanisms. Transmission estimation remains unauthorized.

## Candidate next improvement — requires approval

The most defensible next step is a new outcome-blind Run 008, not a threshold relaxation. It would first test whether the unstable one-dimensional loading is actually a stable two-dimensional factor subspace using principal angles and Procrustes alignment. It would then compare a prospectively fixed-loading, economically anchored factor against a sign-restricted two-factor representation, with all gates frozen before execution. A current extension of the free point-in-time panel should be built first so post-October-2025 observations can serve as a genuinely new temporal validation block where source availability permits.

This improvement could recover stable state information without choosing the attractive Run 007 HMM post hoc. The tradeoff is that a two-dimensional state substantially increases downstream support and power demands; it should proceed only if state-only stability evidence is strong.
