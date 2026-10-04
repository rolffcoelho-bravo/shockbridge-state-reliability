# Run 008 outcome-blind state-model result

**Execution date:** 2026-10-03
**Data:** real, freely retrievable point-in-time state variables
**Transmission outcomes accessed:** no
**Decision:** kill gate activated; no primary state representation selected

## What was executed

Run 008 used the frozen 286-month panel from January 2002 through October 2025. The scalar loading was estimated once from the January 2002–December 2011 development block and remained byte-identical at every later origin. State evaluation covered January 2012–October 2025. Cross-window gates used 165 origins at which expanding and rolling-120 histories genuinely differed; 61 mechanically shared origins were excluded from those gates.

The run produced 452 subspace rows, 332 fixed-scalar rows, and 452 anchored-two-factor diagnostic rows. It loaded no monetary-policy shock, asset-price response, outcome horizon, or transmission dataset.

## Required two-dimensional subspace decision

Six of twelve frozen subspace gates fail:

| Metric | Estimate | Frozen requirement | Result |
|---|---:|---:|---|
| Minimum second principal cosine | 0.0127 | at least 0.75 | **Fail** |
| Second-cosine 10th percentile | 0.1501 | at least 0.90 | **Fail** |
| Median projector distance | 0.0967 | at most 0.20 | Pass |
| Projector-distance 90th percentile | 0.7153 | at most 0.35 | **Fail** |
| Slack-anchor capture 10th percentile | 0.5568 | at least 0.50 | Pass |
| Policy-minus-inflation capture 10th percentile | 0.2604 | at least 0.50 | **Fail** |
| Slack weak-anchor rate | 0.0000 | at most 0.10 | Pass |
| Policy-minus-inflation weak-anchor rate | 0.6970 | at most 0.10 | **Fail** |
| Slack loading-cosine median | 0.9903 | at least 0.90 | Pass |
| Policy loading-cosine median | 0.9944 | at least 0.90 | Pass |
| Slack loading-cosine 10th percentile | 0.9025 | at least 0.75 | Pass |
| Policy loading-cosine 10th percentile | -0.5386 | at least 0.75 | **Fail** |

The low median projector distance shows that many origins are similar, but the tail instability is severe and persistent. The worst second principal cosine is 0.0127 in December 2019. The fifteen worst origins cluster from August 2019–February 2020 and October 2021–May 2022. The slack direction remains well captured, while the policy-minus-inflation direction is weak at 115 of 165 expanding origins and 37 of 165 rolling origins. This is evidence that the four-feature panel does not deliver a stable two-dimensional economically identified state space under the frozen history sensitivity.

## Fixed-loading scalar decision

Five of six scalar gates pass. The only failure is sign consistency:

| Metric | Estimate | Frozen requirement | Result |
|---|---:|---:|---|
| Pearson correlation | 0.9721 | at least 0.80 | Pass |
| Spearman correlation | 0.9877 | at least 0.80 | Pass |
| Sign disagreement | 0.1394 | at most 0.10 | **Fail** |
| Standardized mean absolute difference | 0.2563 | at most 0.35 | Pass |
| Mean score gain, expanding | 0.5686 | positive | Pass |
| Mean score gain, rolling | 1.1580 | positive | Pass |

There are 23 sign disagreements among 165 distinct origins. They concentrate in October 2017–August 2018 and February–October 2019, with isolated disagreements in May 2017, November 2018, and July 2021. The frozen rule is conjunctive: high correlation and positive density gains cannot compensate for sign instability. The fixed scalar therefore cannot be selected.

## Anchored two-factor diagnostic

The diagnostic does not pass its factorwise stability contract. Factor 1 has Pearson/Spearman correlations of 0.9423/0.9511 and standardized difference 0.3166, but its sign-disagreement rate is 0.1758. Factor 2 performs materially worse: Pearson 0.3233, Spearman 0.2204, sign disagreement 0.2909, and standardized difference 0.7569. Although feature-density gains are positive in both histories, the diagnostic was never eligible for transmission and cannot rescue the required failures.

## Integrity audit

- Independent recomputation from the serialized outputs reproduces all metrics to persisted precision.
- A complete repeat execution is byte-identical for all four outputs.
- Every month-window key is unique and every serialized numerical field is finite.
- Every stored projector is symmetric, idempotent, and rank two to numerical tolerance.
- Every economically aligned basis is orthonormal.
- The minimum eigenvalue of any stored two-factor filtered covariance is 0.0250.
- No incomplete `.part` file remains.
- Output hashes and byte sizes are frozen in `state_model_run008_v1.manifest.yaml`.
- Execution began from clean pre-result commit `c1383ee`.

## Scientific interpretation boundary

Run 008 rejects both the required two-dimensional factor-space stability hypothesis and the fixed-loading scalar as a primary conditioning state. It makes no statement about state-dependent monetary-policy transmission, causal amplification, market predictability, or portfolio performance. Transmission estimation remains unauthorized.

The failure should not be repaired by relaxing the 10% sign gate, discarding unstable dates, choosing the attractive score gains, or promoting the two-factor diagnostic. Those actions would be post-result selection.

## Candidate next improvement — requires approval

The strongest next contribution is not another immediate PCA rescue. A prospective, outcome-blind Run 009 could decompose the instability itself: date the projector and anchor failures, test whether they coincide with prespecified monetary-regime episodes, compare covariance versus mean/scale drift, and evaluate whether the measurement failure is reproducible under prespecified 96- and 144-month windows. This would be explicitly diagnostic and could elevate the paper into a rigorous state-measurement reliability study.

Only after that diagnosis should the project consider a new theory-observed state. Such a state would require a fresh protocol and preferably new temporal or cross-area validation; it cannot be chosen from Run 008 because it looks favorable. Until then, no transmission run is defensible.
