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
| C04 | Prospective reliability diagnostics identify future unsupported/high-loss cases. | Run 026 freezes the evidence clock and analytic-class contract; Run 027 then stops execution at 11 result-sensitive semantic gaps before any fit. Two nominal controls are reclassified as algebraic invariances. | Approve and implement the prospective executable amendment; pass hostile tests; lock calibration; execute the sealed evaluation once; report all benchmark, participation, control, interval, and invariance results. | EXECUTABLE_AMENDMENT_APPROVAL_REQUIRED |
| C05 | Speech events improve precision without changing the estimand. | EA-EMPD source audited; paper reports broader event universe. | Separate shock construction, clustering, speaker/event controls, transportability analysis. | EXPLORATORY |
| C06 | The public pipeline is reproducible and fails closed on temporal leakage. | Hashed source registry, 1,210-row candidate state panel, zero temporal violations, strict-boundary/deletion/staleness tests, schema audits and CI. Run 010 reproduces exactly in clean resolved and exact-version-locked Python 3.9 archives. Run 013 adds explicit licenses, a security-clean parentless public root, a verified commit identity, independent live public/private repositories, and a hosted Python 3.9/3.12 matrix passing the exact seven-skip source-only gate. Run 014 adds explicit Ubuntu 24.04 gates, a passing Ubuntu 26.04 compatibility lane, advanced CodeQL with zero open alerts, dependency monitoring, a security policy, and private vulnerability reporting. | Verify the complete empirical bundle on a second operating system/runtime and add package-distribution hashes or a validated container. | PUBLIC_RELEASE_SECURITY_HARDENED |
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
- The Run 013 public candidate has one parentless commit, no flagship blueprint, no prohibited data path, and no known-secret, privacy-path, or supplementary entropy finding. Its verifier binds imports to the exported source, requires exactly seven evidence-bound skips, and validates static analysis, coverage, Git integrity, the recovery bundle, and archive exclusions.
- Publication amendment 1 replaces only the temporary public-commit address with the owner's ID-based GitHub no-reply identity. The tree, message, dates, 215-file surface, and parentless root are unchanged; every local release gate passes again.
- Both independent repositories are live and their first-push remote `main` refs exactly matched the local heads. The first hosted matrix exposed a Python 3.12 repository-root import defect while Python 3.9 passed; publication amendment 2 preserves that failed run and its replacement matrix passes both Python 3.9 and 3.12 under the unchanged test and coverage contract.
- Run 014 replaces the moving primary runner label with Ubuntu 24.04, adds a passing non-blocking Ubuntu 26.04/Python 3.12 lane, and enables advanced CodeQL, weekly dependency updates, dependency alerts, a security policy, secret and push protection, and private vulnerability reporting. Three archive-extraction alerts were corrected in code; one value-redacted audit-writer alert was dismissed as a documented false positive. The final CodeQL dashboard reports zero open and four closed alerts.
- The current canonical test contract contains 225 tests and executes all 225 at 90% branch-aware coverage. The Run 022 public release contains 213 tests, executes 206, and skips exactly seven evidence-bound cases at an 87% floor. Run 022 adds a 19-test deterministic reliability-engine surface at 92% branch-aware engine coverage. Public PR #9 passed all eight branch/review checks; squash commit `3bdfa0c` then passed all four post-merge `main` checks. Passing these software fixtures is not empirical validation.
- `run-022-reliability-engine-implementation-v1` implements the value-free numerical core without network or filesystem access. It retrieves no official full history, builds no wider panel, estimates no empirical state, and accesses no transmission outcome. DEV-079–DEV-082 document and correct prospective coordinate, exact-preservation, input-domain, and numerical-conditioning anomalies before empirical execution.
- `run-023-full-history-panel-build-v1` privately preserves ten real official ECB series responses and seven official timing-evidence pages. Its two processed panels span 274 monthly origins and contain 1,918 P0 plus 2,740 P1 rows with zero duplicate keys, non-finite values, or timing violations. P0/P1 are fully observed at 123/102 origins. No reliability estimator or transmission outcome is accessed.
- Run 023 retains three failed, non-promoted retrieval attempts. DEV-085–DEV-093 document redirect hardening, BSI archive registration, revision-clock separation, complete response binding, RTD action-row semantics, explicit timeouts, bounded timeout-only retries, timing-claim qualification, and cross-runtime provenance normalization.
- The conservative Run 023 release parser maps 108 in-sample explicit MIR reference periods and 104 BSI periods. Generic older archive titles remain unmapped even where official link identifiers appear informative; using those identifiers requires a prospective approved amendment.
- The historical MIR/BSI evidence establishes release dates; the registered 10:00:01 Europe/Berlin usable time is a calendar convention, not an independently recovered timestamp for every historical release. DEV-092 requires this distinction in all claims and reserves a next-day timing sensitivity for a prospective amendment.
- Run 023 public PR #10 was squash-merged at `39aa7ad` after all eight branch/review checks passed; all four independent post-merge `main` checks also passed. The public tree contains implementation, hashes, aggregate audits, and documentation but no raw or processed observations, private manuscript, or private scientific ledgers.
- Run 015 adds reviewer routes, a repository map, contribution guidance, structured bug/reproducibility forms, a scientific pull-request checklist, a concise repository description, and eight research topics. This improves discoverability but does not upgrade any empirical or novelty claim.
- `run-024-archive-identifier-and-timing-sensitivity-v1` reuses the exact 17
  Run 023 official responses and verifies all nine bound inputs before rebuild.
  It performs no network retrieval, reliability fit, scenario evaluation, or
  transmission-outcome access.
- The Run 024 parser admits only exact legacy PDF identifiers after entry-local
  association and temporal validation. It cross-validates 20/20 MIR and 17/17
  BSI explicit-title overlaps with zero disagreement and rejects two pre-sample
  BSI candidates whose encoded months had not ended by the release date.
- In-sample release coverage expands from 108 to 264 MIR periods and from 104
  to 271 BSI periods. P1 observed origins become 261 for MIR borrowing costs,
  260 for adjusted NFC loans, and 272 for M3; fully observed P1 origins rise
  from 102 to 123. P0 remains byte-identical to Run 023.
- The next-day timing sensitivity changes 24 selected observations and 23
  transformed values across 23 origin months, but changes no missingness status
  and no fully observed-origin count. Both clocks remain required scenarios.
- Run 024 attempts 1 and 2 stopped before canonical output. DEV-095 and DEV-096
  preserve the parser corrections and machine-readable failed-attempt records.
- Run 024 public PR #11 was squash-merged at `80ce90c` after all eight
  branch/review checks and all four post-merge `main` jobs passed. The public
  tree contains no protected observation or private-ledger path.
- Run 025 preserves a canonical official ECB key-rate response whose table
  explicitly reports dates “with effect from.” Its 51 eligible events reproduce
  all 8,366 retained daily DFR API values exactly, with zero conflicts or
  unmatched records.
- Replacing database-record validity with the official DFR effective-date
  clock expands observed DFR origins from 123 to 274 and fully observed P0/P1
  origins from 123/123 to 179/179. All four archive × DFR clock scenarios have
  zero duplicate keys, non-finite values, point-in-time violations, or changed
  non-DFR rows.
- The Run 025 DFR next-day sensitivity changes 274 usable timestamps but zero
  monthly selected observation periods, transformed values, or missingness
  states. This is monthly-calendar invariance, not daily or intraday invariance.
- DEV-100 preserves and corrects the first uncommitted audit's ambiguous
  `selection_changes` label before scientific acceptance.
- Run 025 public PR #12 was squash-merged at `72211d2` after all eight
  branch/review checks passed; all four independent post-merge `main` jobs also
  passed. The current public tree contains no raw or processed observation,
  private manuscript, blueprint, or private scientific-ledger path.
- Run 026 freezes, but does not execute, the first real-data reliability
  evaluation. Its fail-closed preflight verifies 12 exact upstream inputs, 8
  panel files, 18,632 rows, 4 comparators, the mature evaluation calendar, and
  the evaluation and transmission firewalls.
- The four source-clock provenance labels contain only three unique analytic
  value-and-missingness paths: one P0 class and two P1 classes separated by the
  MIR/BSI clock. DFR effective-day and next-day labels remain auditable but do
  not receive independent multiplicity weight.
- The Run 026 provenance-labelled scenario ceiling is 224. Exact input-clock
  deduplication lowers the analytic ceiling to 88 before origin-specific
  eligibility-mask and standardized-matrix deduplication. Clock labels are not
  resampled as observations.
- Run 026 fits no state or reliability scenario and opens no evaluation or
  transmission outcome. Its protocol discipline is not evidence of benchmark
  advantage, useful participation, novelty, or monetary-policy value.
- Run 026 public PR #15 was squash-merged at `10a29f9` after all eight
  branch/review checks passed; all four independent post-merge `main` jobs also
  passed. The released tree contains the protocol, software, hashes, and
  aggregate evidence but no raw or processed observation, private manuscript,
  blueprint, or private scientific-ledger path.
- A second empirical operating system/runtime and cryptographically hash-pinned distributions remain open credibility improvements.

## Run 028 outcome-blind implementation evidence

- Owner approval binds the exact 11,887-byte Run 027 amendment proposal at
  SHA-256 `cda763f5102d6491dfce4d3b0687cf5729089e156cf2cac59be716fb04655899`
  and authorizes implementation and hostile software tests only.
- The execution harness exposes an explicit implementation surface for every
  gap XG-01 through XG-11 and imports no transmission or outcome module.
- Fifteen focused hostile tests pass across exact-grid construction,
  slow-release timing, score recovery, redundancy, rank-invariant orientation,
  history gates, robust PCA, comparator cutoffs, controls, bootstrap replay,
  and immutable access-state transitions.
- The immutable audit reports `IMPLEMENTATION_GATE_PASSED` against unchanged
  Run 026 protocol SHA-256
  `78d562c4d2e20529f5609198721c4d2be85694544ca66f62a48132cf29216aeb`.
- No official value entered an estimator. No calibration, evaluation, or
  transmission result was accessed. Software fixtures remain non-empirical.
- Passing this gate establishes executable completeness, not performance,
  participation, novelty, a reliable state, or policy value.

## Run 029 Stage-A orchestration-readiness evidence

- Owner approval authorizes Stage A only subject to a passing readiness gate.
- The readiness audit inspects five methodology/source files and no empirical
  data path; it records no official fit or calibration, evaluation, or
  transmission access.
- Six gaps can change empirical results and three concern lock completeness and
  leakage-resistant auditability.
- The current B3 SVD step uses zero outside the observed set, so the code does
  not yet solve the registered observed-entry problem.
- Four hostile readiness tests pass, including tampered-binding failure and
  immutable audit serialization.
- The Run 029 amendment is prospective and unapproved. Its B2/B3 equations and
  complete orchestration have no evidentiary status until approved,
  implemented, and hostile-tested.

## Reporting rules

- distinguish measured facts, estimates, interpretations, and conjectures;
- report all prespecified primary outcomes even when null or sign-inconsistent;
- retain negative results and rejected model classes;
- never describe synthetic or exploratory results as confirmatory evidence;
- cite exact artifact hashes and code commits in tables and figures;
- report effective independent events, not only row counts;
- disclose protocol breaks, exclusions, missingness, and multiplicity families.
