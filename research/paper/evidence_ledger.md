# Scientific paper evidence ledger

This ledger is append-only in substance: superseded findings remain visible with their replacement and reason. No paper claim is allowed without a linked source artifact, code path, experiment record, and robustness status.

## Candidate paper

**Working title:** *When a State Is Not Stable Enough: Real-Time Measurement Reliability in Euro-Area Monetary-Policy Research*

**Core contribution under test:** whether uncertainty about the pre-announcement macro-financial state materially changes estimated heterogeneity in high-frequency monetary-policy transmission, and whether a prospective evidence rule identifies poorly supported state-dependent claims.

## Evidence table

| ID | Candidate claim | Current evidence | Required before manuscript claim | Status |
|---|---|---|---|---|
| C01 | ECB event responses differ by the pre-event state. | Outcome-blind point-in-time panel built for 242 events. Event-indexed HMM fails stability/support. On the regular calendar, none of PCA, dynamic factor, HMM, or change point passes every frozen gate; no response outcomes inspected. | Redesign state representation, freeze an eligible state model or continuous score, overlap, observed-state power, state-independent response baseline, dependence-aware inference, falsifications. | BLOCKED_KILL_GATE |
| C02 | State uncertainty changes the estimated response contrast. | Synthetic design benchmark: hard misclassification attenuates the interaction and probability conditioning restores the coefficient only under an ideal known-error model, while power remains lower. | Probability-weighted, bias-adjusted, and hard-state estimators on frozen data with first-stage uncertainty propagation. | SYNTHETIC_ONLY |
| C03 | A common-unit amplification summary is informative beyond volatility/stress. | Definition in V2. | Frozen scales/weights, denominator floor, uncertainty, benchmark incremental test. | BLOCKED |
| C04 | Prospective reliability diagnostics identify future unsupported/high-loss cases. | Timing guard implemented. | Frozen failure event, matured labels, chronological calibration, matched-participation baselines. | BLOCKED |
| C05 | Speech events improve precision without changing the estimand. | EA-EMPD source audited; paper reports broader event universe. | Separate shock construction, clustering, speaker/event controls, transportability analysis. | EXPLORATORY |
| C06 | The public pipeline is reproducible and fails closed on temporal leakage. | Hashed source registry, 1,210-row candidate state panel, zero temporal violations, strict-boundary/deletion/staleness tests, schema audits and CI. Run 010 reproduces exactly in clean resolved and exact-version-locked Python 3.9 archives. Run 013 adds explicit licenses, a security-clean parentless public root, a verified commit identity, independent live public/private repositories, and an exact seven-skip source-only gate. | Complete a hosted cross-version correction after the first Python 3.12 run exposed a repository-root import defect; then verify a second empirical operating system/runtime and add package-distribution hashes or a validated container. | PUBLIC_RELEASE_LIVE_HOSTED_CI_REQUIRED |
| C07 | A 47-event block cannot serve as the sole primary transmission test under plausible state imbalance. | Prespecified synthetic design grid; at 20% minority prevalence, power is 26.0% for a 0.5 standardized interaction and 63.7% for a 1.0 interaction. | Observed state support, economic-unit SESOI, observed-shock rerun, dependence-aware focused simulation. | DESIGN_SCREEN |
| C08 | Favorable predictive density can coexist with economically consequential instability in a real-time macro state measurement. | Runs 007 and 008 prospectively reject scalar and two-dimensional state representations. Run 009 finds pervasive full-panel geometry failure across 96/120/144-month windows, continuous dated breach episodes, and off-diagonal rather than availability-dominated Gram drift. Run 010 retains every full-panel and deletion-window classification under matched-period latest official ECB RTD values. Run 011 exactly reproduces all four Run 010 outputs in an isolated clean checkout, audits the closest literature, and defines the negative-result estimand and external-validity boundary. | Manuscript-level synthesis, cross-platform reproduction, and external review of incremental contribution; no novelty wording before those checks. | CLEAN_REPRODUCED_POSITIONED_NEGATIVE_EVIDENCE |

## Data evidence

- `EA_MPD_OFFICIAL`: 315 scheduled event dates, three windows, official source hash recorded.
- `EA_EMPD_OFFICIAL`: 4,926 events through 2026-03-28, official source hash recorded.
- `ABGMR_TARGET_2025_10_30`: 242 target-factor events, exact join to official press-release outcomes.
- Primary joined outcomes have zero missing values across all 242 target-factor events.
- `state-support-power-v1`: 180 synthetic design cells with 300 replications each; no empirical outcome magnitude used.
- `state-panel-v1`: 1,210 outcome-blind rows for 242 target-factor dates and five candidate features; zero point-in-time violations and zero duplicate event-feature keys.
- Admitted feature coverage: HICP 240/242, industrial production 235/242, unemployment 233/242, and deposit-facility rate 242/242.
- Conditional yield-curve challenger coverage: 209/242; the 33 missing events precede the ECB curve history that starts on 2004-09-06.
- New and legacy CISS are excluded from causal state estimation because the inspected historical values are only documented in post-sample replacement vintages.
- `state-replay-v1`: 202 filtered event probabilities after a 40-event warm-up; global hard counts 135/67 and weighted ESS 135.17/67.24.
- The event-indexed HMM is rejected as primary: minimum restart agreement is 0.70 at the 2008-09-04 event and 0.704 at 2008-10-02, below the frozen 0.85 gate.
- Temporal support is uneven: state 1 has zero hard assignments and weighted ESS 3.10 in the middle chronological third. This warning motivated prospective block-level gates; it was not a prespecified v1 gate.
- `monthly-state-panel-v2`: 286 regular month-start cutoffs and 1,144 point-in-time rows with zero timing violations. Coverage is 99.65% HICP, 95.80% industrial production, 94.41% unemployment, and 100% deposit rate.
- The rejected month-end calendar remains registered because its 63.6% HICP and 53.1% industrial-production coverage motivated the outcome-blind calendar correction without relaxing staleness.
- `state-model-comparison-v1`: all 16 model/state-count/window variants were reported. No primary two-state expanding candidate passes all gates, so no state estimator was selected.
- Dynamic factor is the leading redesign candidate, not a finding: it has the best two-state expanding score and passes support gates, but its minimum six-restart agreement is 0.391.
- The Run 007 implementation amendment corrects HMM restart ranking to use the optimized MAP objective. The primary HMM score moves by -0.000083, while its hard counts, minimum restart agreement, failed gates, and the Run 006 no-selection decision remain unchanged. Original artifacts are retained rather than silently regenerated.
- `state-instability-run009-v1`: the full four-feature factor space fails the frozen common-sample geometry classification at all 96-, 120-, and 144-month windows. Primary breach episodes span 2017-09–2023-03, 2019-03–2023-05, and 2021-02–2023-07, respectively.
- Run 009 does not flag prespecified weak identification in any full-panel window. Diagonal availability effects average below 0.7% of squared Gram drift; pairwise comovement changes involving the deposit rate contribute 63.0%–72.5% across windows.
- Leave-one-feature-out results are sensitivity evidence only: omitting unemployment or the deposit rate removes the 120/144-month failure classification, while every deletion still fails at 96 months or more. No deletion result selects a state.
- The Run 008 scalar has a 16.31% raw sign disagreement rate over the Run 009 common sample, but only one disagreement is substantive at the frozen 0.25-unit threshold. This qualification does not revise the prospective Run 008 gate.
- `run-010-vintage-robustness-design-v1`: official no-data metadata confirmed that the three admitted ECB RTD concept keys remained available for a matched-period latest-vintage comparison. The design preserves point-in-time observation periods and missingness, copies policy-rate values exactly, and labels the comparator ex post.
- `state-vintage-robustness-run010-v1`: 1,144 matched rows, 100% required-level/lag coverage, exact point-in-time geometry reproduction, and 4,950 vintage-geometry rows. The latest vintage fails the frozen full-panel classification at 96, 120, and 144 months. Full-panel episode overlap is 0.904–0.981, and every leave-one-feature-out window classification is unchanged. Latest-vintage weak-identification coincidence remains below 50% and average off-diagonal drift share remains above 99% in all windows.
- Run 010 value differences are ex-post matched-period differences, not pure numerical revisions: median absolute changes are 0.0129 percentage points for HICP growth, 0.6192 for industrial-production growth, and 0.1920 for unemployment.
- `run-011-clean-reproduction-v1`: the Run 010 comparison, geometry, episode, and audit artifacts exactly reproduce byte for byte from source commit `02fdfd1` in a new temporary checkout and isolated Python environment. Canonical artifacts remain unchanged, the checkout was removed, and no outcomes or synthetic observations were used.
- Run 011's focused audit establishes that vintage comparisons, factor geometry, loading-instability diagnostics, forecast-breakdown methods, and model-confidence sets are prior art. Candidate paper value is limited to the prospective validation sequence, artifact-level governance, and application-specific negative result.
- `reports/paper/run011/` is the hash-bound descriptive presentation bundle. Its tables and SVG figures contain no transmission outcomes and make no causal-revision or structural-break claim.
- `run-012-locked-reproduction-v1`: exact-version Python 3.9 locks reproduce all four Run 010 hashes from a clean archive after verifying and hydrating the portable local inventory; the full quality suite passes at 90% coverage on the audited macOS host.
- Run 012's frozen source-only simulation executed 137 of 144 tests, required exactly seven disclosed local-evidence skips, and enforced 87% coverage. This historical count does not replace the full locked scientific gate.
- Run 013 selects Apache-2.0 for software and CC BY 4.0 for owner-authored documentation and figures, without relicensing external data or third-party materials.
- The Run 013 public root is parentless and has no flagship blueprint, prohibited data path, known-secret, privacy-path, or supplementary entropy finding. Its verifier binds imports to the exported source, requires exactly seven evidence-bound skips, and validates static analysis, coverage, Git integrity, the recovery bundle, and archive exclusions.
- Both independent repositories are live and their first-push remote `main` refs exactly matched the local heads. The first hosted matrix then exposed a Python 3.12 repository-root import defect while Python 3.9 passed; publication amendment 2 preserves the failed run and repairs that cross-version boundary without changing scientific code or evidence.
- A second empirical operating system/runtime and cryptographically hash-pinned distributions remain open credibility improvements.

## Reporting rules

- distinguish measured facts, estimates, interpretations, and conjectures;
- report all prespecified primary outcomes even when null or sign-inconsistent;
- retain negative results and rejected model classes;
- never describe synthetic or exploratory results as confirmatory evidence;
- cite exact artifact hashes and code commits in tables and figures;
- report effective independent events, not only row counts;
- disclose protocol breaks, exclusions, missingness, and multiplicity families.
