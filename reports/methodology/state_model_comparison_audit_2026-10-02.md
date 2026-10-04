# Outcome-blind state-model comparison audit

**Run:** `state-model-comparison-v1`

**Date:** 2026-10-02

**Decision:** Blueprint kill gate activated; no primary state model selected

## Design

The comparison used the accepted 286-month point-in-time calendar and a 60-month warm-up. It evaluated all four required Blueprint V2 families: PCA plus clustering, dynamic factor, hidden Markov, and causal change point. Each was evaluated with two and three states, expanding and rolling 120-month histories, and six or more frozen initialization restarts. All estimates use only pre-cutoff state information.

No response outcome was accessed and no synthetic observation was used. The design and gates were checkpointed in Git commit `b8463b7` before execution.

## Invalid first attempt and repair

The first execution produced two non-finite change-point log scores at July 2024 because its rolling segment contained no unemployment observation. That execution is invalid and preserved only for audit. The repair uses the same historical-window feature moment whenever a local segment has no observations; it does not impute the empirical panel or modify any state, threshold, or selection gate. The repair is checkpointed in `8615cd1`.

## Primary two-state expanding results

| Model | Cumulative log score | Gain vs single Gaussian | Minimum restart agreement | Global/block support | Screening |
|---|---:|---:|---:|---|---|
| Dynamic factor | -1586.19 | +353.31 | 0.391 | Pass | Fail |
| Hidden Markov | -1629.21 | +310.29 | 0.738 | Fail | Fail |
| Change point | -1685.29 | +254.21 | 0.600 | Fail | Fail |
| PCA plus clustering | -1798.94 | +140.56 | 0.366 | Pass | Fail |

All models improve their family-specific prequential density score over the state-independent diagonal Gaussian, but none passes the frozen 0.85 minimum restart-agreement gate. The likelihoods are constructed on the same standardized observations, yet they remain family-specific approximations; scores are therefore not sufficient for selection.

The dynamic-factor model is the strongest candidate, not an accepted model. Its two-state expanding specification passes every global and chronological support gate and has the best two-state score, but 53 of 226 origins fall below 0.85 restart agreement and the minimum is 0.391.

The HMM is much more stable in typical months: median agreement is 1.0 and only three origins fall below 0.85. Its minimum is 0.738 in September 2008. However, its strong/hot state has only four hard assignments and weighted ESS 4.14 in the middle chronological block, below the frozen five and ten thresholds.

PCA clustering has pervasive initialization instability: 194 of 226 origins fall below 0.85. The change-point candidate has 69 such origins and no assignments to its first state in the middle chronological block.

## Economic interpretation

Across PCA, dynamic-factor, and HMM candidates, the two-state profiles consistently separate:

- a stronger/hotter state with inflation around 2.5%, positive industrial-production growth, unemployment near 8%, and policy rates near 2%;
- a weaker/slacker state with inflation around 1.3–1.5%, negative industrial-production growth, unemployment near 9.8%, and policy rates near 0.3%.

This consistency is descriptive evidence of interpretable macroeconomic separation. It does not overcome initialization or temporal-support failure and does not establish state-dependent monetary-policy transmission.

## Window sensitivity

Expanding-versus-rolling two-state probability correlations are 0.783 for dynamic factor, 0.752 for PCA, 0.673 for HMM, and 0.653 for change point. Corresponding hard-state agreements are 90.3%, 86.3%, 81.4%, and 80.5%. This window sensitivity was reported but was not a frozen numerical gate in v1.

## Decision and research value

No primary state model is selected. Outcomes remain sealed. Choosing the dynamic-factor model merely because it ranks first would violate the frozen selection rule and hide genuine instability.

The next redesign should distinguish poor random starts from disagreement among near-optimal solutions, use exact one-dimensional clustering for the dynamic factor, add a prospective expanding-versus-rolling consistency gate, and test whether an ensemble or continuous factor state is scientifically better supported than discrete regimes.
