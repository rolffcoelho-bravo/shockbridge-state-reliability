# Research decision log

## D001 — Separate replication and extension event universes

**Date:** 2026-10-02  
**Decision:** Scheduled Governing Council events from EA-MPD form the confirmatory replication lane. EA-EMPD speeches form a separate exploratory/extension lane.  
**Reason:** event definitions, treatment interpretation, dependence, and effective sample differ materially.  
**Rejected alternative:** pool all 4,926 rows to advertise a larger sample.  
**Revisit only if:** a formal transportability/pooled estimand is written and preregistered.

## D002 — Freeze the original sample rather than call it stale

**Date:** 2026-10-02  
**Decision:** The primary scheduled-event sample ends on 2025-10-30 by design. Later EA-EMPD events are an external extension.  
**Reason:** a scientific paper needs a reproducible frozen sample; continuously moving endpoints undermine preregistration and final-test integrity.  
**Rejected alternative:** update the primary sample during model development.

## D003 — Compact confirmatory outcome family

**Date:** 2026-10-02  
**Decision:** Primary outcomes are Italy–Germany 10-year spread, STOXX50, and EUR/USD. SX7E and DE2Y are secondary.  
**Reason:** these cover sovereign fragmentation, equity risk, FX transmission, banking, and the short curve while keeping the confirmatory multiplicity family small.  
**Revisit only if:** a documented measurement or identification failure is found before final-block analysis.

## D004 — Fetch-only raw-data release policy

**Date:** 2026-10-02  
**Decision:** Do not bundle ECB workbooks in the repository. Publish retrieval code, hashes, manifests, schemas, and attributed derived displays.  
**Reason:** maximizes reproducibility while respecting authored-workbook and third-party-data boundaries.

## D005 — Separate transmission inference from the reliability holdout

**Date:** 2026-10-02  
**Decision:** Do not use the candidate 47-event final block as the sole primary state-transmission test. Preserve chronological blocks for prospective reliability evaluation. Freeze the transmission design without inspecting outcome magnitudes, then use a separately justified eligible inference sample.  
**Reason:** the synthetic design screen finds only 26.0% power for a 0.5 standardized interaction and 63.7% for a 1.0 interaction at 20% minority prevalence, even with a perfectly observed state.  
**Rejected alternative:** apply the same train/calibration/final split mechanically to causal interaction inference and prospective reliability.  
**Revisit only if:** the observed state panel, an economic-unit smallest effect, and a high-replication dependence-aware simulation establish adequate final-block power.

## D006 — Probability states are primary; hard states are descriptive

**Date:** 2026-10-02  
**Decision:** Use filtered state probabilities in the primary transmission specification and propagate first-stage uncertainty. Report hard labels only for interpretation and support diagnostics.  
**Reason:** in the idealized design, 20% hard-state misclassification attenuates a true 1.0 interaction to 0.436 and reduces true-effect interval coverage to 10.3%. Posterior conditioning restores the coefficient in this known-error benchmark but cannot restore lost power.  
**Rejected alternative:** treat the modal HMM state as observed and run an ordinary interaction regression.  
**Boundary:** plug-in probabilities alone do not account for estimated state-model uncertainty; the final method must refit or draw the state stage inside inference.

## D007 — Exclude CISS from the causal state panel

**Date:** 2026-10-02  
**Decision:** Do not use either New CISS or legacy CISS as a decision-time feature in the primary state model.  
**Reason:** the inspected API history assigns every September 2008 New CISS observation a `VALID_FROM` timestamp of 2026-10-01 and every inspected legacy observation a timestamp of 2025-04-15. The retrieved back history therefore does not establish what value was available at the historical event cutoff.  
**Allowed use:** ex-post descriptive figure or challenger labeled as retrospectively reconstructed.  
**Revisit only if:** a public archived vintage series or reproducible contemporaneous reconstruction is located and passes the same as-of audit.

## D008 — Conservative pre-2015 RTD availability rule

**Date:** 2026-10-02  
**Decision:** Treat each ECB archived monthly RTD snapshot as usable only at 00:00 Frankfurt time on the first day after its named vintage month. Use exact API `VALID_FROM` timestamps from 2015 onward, including delete actions.  
**Reason:** the archive filenames identify the vintage month but not a universally auditable intramonth release time. The month-end rule sacrifices some freshness to avoid optimistic timing assumptions.

## D009 — Freeze source-specific staleness and yield-curve status

**Date:** 2026-10-02  
**Decision:** Cap observation age at 90 days for HICP and 120 days for industrial production and unemployment. Values beyond the cap become explicit missing rows. Retain the ECB 10-year minus 2-year slope as a conditional challenger, not an admitted primary feature.  
**Reason:** the unemployment RTD history has a 2024–2025 vintage gap that would otherwise carry a 15-month-old value into nine meetings. The curve is published daily, but its retrieved historical values lack observation-level vintage history needed to rule out later revisions.

## D010 — Reject the event-indexed HMM as the primary state estimator

**Date:** 2026-10-02

**Decision:** Retain `state-replay-v1` as a reported benchmark, but do not use it as the primary state series. Keep transmission outcomes sealed.

**Reason:** minimum restart agreement is 0.70 against a frozen 0.85 gate. State 1 also has no hard assignments in the middle chronological third, so adequate global counts do not establish recurrent temporal support.
**Rejected alternative:** promote the model because its mean agreement, global ESS, and prequential score are strong.

## D011 — Estimate states on a regular monthly real-time calendar

**Date:** 2026-10-02

**Decision:** Build a point-in-time monthly feature panel, estimate filtered states on the regular calendar, and sample them at exact event cutoffs.

**Reason:** treating every irregular meeting gap as one transition confounds transition dynamics with the ECB meeting calendar and may turn regimes into policy-era indicators.
**Boundary:** no synthetic data, retrospective imputation, smoothing, or outcome-selected feature may enter the empirical state series.

## D012 — Add prospective chronological-block support gates

**Date:** 2026-10-02

**Decision:** From `state-calendar-v2`, require each retained state to have at least five hard assignments and probability-weighted ESS 10 in each of three chronological blocks, in addition to global support.

**Reason:** v1 demonstrated that global balance can hide an absent state over an entire historical block.
**Disclosure:** this decision is post-v1 and must never be described as prespecified for `state-replay-v1`.

## D013 — Preserve immutable run, novelty, and deviation records

**Date:** 2026-10-02

**Decision:** Every executed run must have a frozen configuration, machine audit, manifest, human report, results-register entry, and deviation record. Candidate novelty is tracked separately and cannot be claimed without closest-prior-art support.
**Reason:** manuscript value depends on a traceable chain from idea and design to code, evidence, limitations, and claim status.

## D014 — Use month-start rather than month-end regular checkpoints

**Date:** 2026-10-02

**Decision:** Use 23:59:59 Europe/Berlin time on the first calendar day of each month for the regular state-model training calendar.

**Reason:** under the conservative archive-availability assumption, month-end checkpoints mechanically made otherwise valid macro observations exceed the frozen staleness caps. Month-start checkpoints retain monthly spacing and use only vintages already available.

**Rejected alternative:** relax the 90/120-day staleness limits after inspecting coverage.

**Disclosure:** month-end v1 is retained as a failed feasibility design; this correction occurred before state-model estimation and without outcome access.

## D015 — Activate the state-engine kill gate

**Date:** 2026-10-02

**Decision:** Select no primary state estimator from `state-model-comparison-v1` and keep transmission outcomes sealed.

**Reason:** none of the four primary two-state expanding candidates passes every frozen stability and temporal-support gate. Dynamic factor ranks first on score and support but fails minimum restart agreement.

**Rejected alternative:** choose the highest-scoring candidate and describe its failed stability gate as a secondary caveat.

## D016 — Redesign around continuous factors and near-optimal stability

**Date:** 2026-10-02

**Decision:** Before another discrete-state selection run, evaluate a continuous filtered factor as a primary conditioning variable and redefine restart stability prospectively among near-optimal solutions. Use exact clustering where the latent representation is one-dimensional and add an expanding-versus-rolling consistency gate.

**Reason:** the current minimum across every random start can mix optimizer failure with genuine state non-identification, while the dynamic factor's interpretable continuous signal may be more stable than its discretization.

**Boundary:** this is a post-v1 redesign and must not be presented as prespecified for Run 006.

## D017 — Freeze Run 007 factor and restart stability gates

**Date:** 2026-10-03

**Decision:** Freeze the cross-window, loading, sign-anchor, and HMM objective-gap values in `run_007_threshold_proposal_v1.yaml` before any Run 007 state-panel evaluation. Require every factor/loading gate; predictive score cannot compensate for a failure.

**Reason:** stability and economic orientation are co-primary eligibility conditions, not diagnostics to be relaxed after model results are visible.

**Boundary:** this authorizes the numerical gate definitions, not empirical execution while downstream numerical design fields remain open.

## D018 — Use joint support and propagate first-stage state uncertainty

**Date:** 2026-10-03

**Decision:** Require convex-hull and local-ESS support at both endpoints of every finite-dose contrast. Integrate filtered-state variance exactly in the quadratic primary and refit the state and transmission stages inside dependence-aware bootstrap draws. Retain a penalized cubic tensor spline only as a robustness challenger with an outer-development-frozen basis and chronological tuning.

**Reason:** rectangular ranges can hide unsupported shock-state corners, plug-in state means discard estimated first-stage uncertainty, and an untuned flexible surface creates avoidable researcher degrees of freedom.

**Boundary:** exact support bandwidth/ESS, spline tuning, and bootstrap block parameters remain prospectively approval-gated.

## D019 — Freeze Run 007 downstream numerical controls and authorize the state-only run

**Date:** 2026-10-03

**Decision:** Freeze Gaussian-kernel bandwidth 0.75 and local ESS 20 for the primary joint-support gate, with bandwidth 0.50/1.00 and ESS 15/25 sensitivities. Freeze the one-median-knot cubic tensor spline, penalty grid 0.01/0.10/1/10/100, 120-event initial training block, and 20-event validation blocks. Freeze 1,999 circular moving-block bootstrap replications at block length 6, with lengths 4 and 8 as sensitivities and seed 73129. Authorize only the outcome-blind Run 007 state-model evaluation.

**Reason:** all material downstream tuning values are now fixed before any Run 007 state result or transmission outcome is inspected, closing the remaining researcher-degree-of-freedom gates.

**Boundary:** this decision does not authorize transmission estimation. Outcomes remain sealed unless the continuous factor passes every frozen Run 007 state and loading gate and a later explicit approval is recorded.

## D020 — Activate the Run 007 continuous-factor kill gate

**Date:** 2026-10-03

**Decision:** Select no primary state representation from Run 007 and do not execute transmission estimation.

**Reason:** the continuous factor passes Pearson correlation, Spearman correlation, standardized mean absolute difference, and median loading-cosine gates, but fails four required gates: sign disagreement is 0.1091 against a maximum of 0.10; minimum loading cosine is -0.6002 against a minimum of 0.75; the weaker-window anchor 10th percentile is 0.0932 against a minimum of 0.20; and the weaker-window weak-anchor rate is 0.1091 against a maximum of 0.05. Predictive-density gains cannot compensate under the frozen rule.

**Interpretation:** expanding-window orientation is strong, but the rolling factor undergoes sustained loading rotation and weak economic anchoring, especially around 2018 and 2021–2022. This is evidence against a stable one-dimensional primary conditioning variable, not evidence about shock transmission.

**Boundary:** exact-factor clusters remain descriptive, the HMM remains diagnostic, and no challenger may be promoted using Run 007 results. Any redesign is post-Run 007 and requires a new prospective protocol and explicit approval.

## D021 — Do not claim a complete 2026 state-panel holdout

**Date:** 2026-10-03

**Decision:** Do not extend the primary four-feature validation panel through October 2026 under the current source contract. Preserve the industrial-production definition and 120-day staleness cap.

**Reason:** the official point-in-time HICP, unemployment, and policy-rate sources extend into 2026, but the admitted RTD industrial-production history still ends in August 2025. Replacing it with a revised-data series or carrying it beyond the cap would change the information contract after seeing Run 007.

**Boundary:** later months may be considered only in a separately labeled missing-feature robustness analysis. Run 008 will be disclosed as a prospective, outcome-blind redesign on previously used state-data dates, not an independent external replication.

## D022 — Freeze the Run 008 subspace contract and authorize state-only execution

**Date:** 2026-10-03

**Decision:** Freeze every numerical gate in `run_008_subspace_design_proposal_v1.yaml` and authorize implementation, preflight audit, and outcome-blind Run 008 state execution on the registered real point-in-time panel.

**Reason:** Run 007 rejected the ordered first component. Run 008 prospectively distinguishes instability of that loading from instability of the leading two-dimensional factor space, then requires an economically anchored scalar loading frozen in the January 2002–December 2011 development block to pass every stability and predictive-density gate.

**Boundary:** approval does not authorize shocks, asset-price responses, transmission estimation, threshold relaxation, post-result HMM promotion, or treatment of the two-factor diagnostic as downstream eligible. Any failed required gate selects no state and keeps transmission sealed.

## D023 — Activate the Run 008 state-measurement kill gate

**Date:** 2026-10-03

**Decision:** Select no primary state representation from Run 008 and do not execute transmission estimation.

**Reason:** the two-dimensional subspace fails six of twelve required gates, including a minimum second principal cosine of 0.0127, a second-cosine 10th percentile of 0.1501, a projector-distance 90th percentile of 0.7153, and three policy-minus-inflation anchor/loading gates. The fixed scalar passes five of six gates but has a 0.1394 sign-disagreement rate against the frozen 0.10 maximum. The two-factor diagnostic also fails its factorwise stability contract. Positive predictive-density gains cannot compensate under the approved conjunctive rule.

**Interpretation:** the slack direction is comparatively stable, but the second economic direction and the sign of the scalar state are not reliable across expanding and rolling information histories. This is a prospective negative state-measurement result, not evidence about transmission.

**Boundary:** thresholds, failure dates, and diagnostic scores cannot be used to retrofit a passing model. Any further state design or instability decomposition is post-Run 008, must remain outcome blind, and requires a new prospective protocol and explicit approval.

## D024 — Authorize Run 009 design and software diagnostics only

**Date:** 2026-10-03

**Decision:** Authorize the design, literature audit, and synthetic software testing of a prospective Run 009 state-instability decomposition. Do not authorize its empirical execution until the exact numerical contract receives separate approval.

**Reason:** Run 008 demonstrates that favorable density scores coexist with unstable subspace geometry and scalar signs. Diagnosing the source and temporal structure of that conflict can strengthen the scientific contribution without relaxing gates or selecting another favorable model.

**Boundary:** Run 009 is descriptive and outcome blind. It cannot select a state, reopen transmission, report large-panel structural-break p-values for the four-feature panel, infer causal effects of policy regimes, or use diagnostic results to revise the Run 008 decision.

## D025 — Approve and freeze the expanded Run 009 diagnostic contract

**Date:** 2026-10-03

**Decision:** Approve the exact Run 009 numerical contract and the proposed four-way leave-one-feature-out sensitivity for outcome-blind execution on the registered point-in-time state panel.

**Reason:** Omitting each feature in turn can reveal whether the full-panel instability is sensitive to a single measurement series, while preserving the diagnostic purpose of the run.

**Boundary:** Leave-one-feature-out results are descriptive sensitivity evidence. They cannot identify a causal driver, rescue or select a state, alter the Run 008 kill gate, or authorize transmission estimation. The execution must first pass a complete code, provenance, and no-outcome preflight from a clean Git checkpoint.

## D026 — Record pervasive Run 009 measurement instability

**Date:** 2026-10-03

**Decision:** Classify the full-panel factor geometry as pervasively unstable across the frozen 96-, 120-, and 144-month comparisons. Select no state, leave the Run 008 kill gate unchanged, and keep transmission sealed.

**Reason:** Every window fails the joint common-sample cosine and projector-tail references, and each has one long continuous primary breach episode. The prespecified weak-identification coincidence flag is false in all three windows, while more than 99% of average squared Gram drift is off-diagonal. Feature deletion changes longer-window classifications but never supplies a prospectively eligible replacement state.

**Boundary:** The decomposition is descriptive. It does not identify a causal break, a unique feature driver, or a transmission mechanism. The calendar alignment of episode onsets with rolling histories beginning around 2009 is post-result exploratory evidence and requires a new protocol before further analysis.

## D027 — Authorize non-destructive Run 009 episode amendment

**Date:** 2026-10-03

**Decision:** Authorize `state-instability-run009-v1-amendment-1` to add an explicit right-censoring field to a versioned episode artifact reconstructed from the immutable Run 009 diagnostic rows.

**Reason:** Duration and breach-month counts are numerically correct, but one nonprimary sensitivity is open at the sample boundary and should be explicitly labeled for unambiguous reuse.

**Boundary:** The amendment cannot overwrite v1, change any original field, recompute a classification, access outcomes, select a state, or authorize transmission.

## D028 — Accept Run 009 episode amendment 1

**Date:** 2026-10-03

**Decision:** Accept the versioned episode artifact with explicit right-censoring status. Preserve Run 009 v1 unchanged and use the amendment schema for future episode outputs.

**Reason:** All 44 original rows match exactly. The amendment identifies one open, nonprimary sensitivity row and confirms that all full-panel primary episodes are closed.

**Boundary:** No Run 009 result, state-selection decision, or transmission boundary changes.

## D029 — Design Run 010 as a matched-period latest-vintage sensitivity

**Date:** 2026-10-03

**Decision:** Authorize and record the Run 010 source and method design, but require separate approval of the exact numerical contract before source retrieval, implementation, or empirical execution. Preserve every point-in-time origin, selected observation period, missingness/staleness decision, and deposit-facility value; replace only the three macro values from the same official ECB RTD concepts.

**Reason:** Rebuilding a fully revised panel with unconstrained latest observations would confound data revisions with release lags and missingness. Direct substitution of current fixed-composition STBS/LFSI headline series would also confound vintage differences with geography and source-definition changes. The matched-period RTD design minimizes those confounds and makes the remaining limitation explicit.

**Boundary:** Run 010 is an ex-post measurement sensitivity, not a decision-time state, a pure numerical-revision estimate, or a model-rescue exercise. No observations have been downloaded and no empirical Run 010 result exists. Exact source responses, implementation, thresholds, paired block-bootstrap settings, and execution remain approval-gated by `run_010_vintage_robustness_proposal_v1.yaml`.

## D030 — Freeze and authorize the Run 010 exact contract

**Date:** 2026-10-04

**Decision:** Approve the exact matched-period latest-vintage contract, including the three official ECB RTD production series, 100% required-level coverage gate, unchanged Run 009 geometry thresholds and deletion sensitivities, and 1,999-draw paired circular block-bootstrap summaries at 12-month primary and 24/36-month sensitivity blocks. Authorize implementation, audited source retrieval, and one outcome-blind empirical execution after a clean software preflight checkpoint.

**Reason:** The contract changes the macro vintage while holding observation-period selection, missingness, staleness, calendar origins, and the deposit-facility series fixed. This directly tests vintage robustness without opening transmission outcomes or permitting post-result state rescue.

**Boundary:** The comparison remains ex post and cannot be called a pure numerical-revision experiment, a decision-time state, or causal evidence. Any source metadata or coverage mismatch stops execution and requires a new audit rather than substitution.

## D031 — Accept latest-vintage-robust measurement instability

**Date:** 2026-10-04

**Decision:** Accept the prespecified `LATEST_VINTAGE_ROBUST_INSTABILITY` classification. Preserve the Run 008 no-state decision and Run 009 diagnostic, select no state, and keep transmission sealed.

**Reason:** The latest official ECB RTD values pass 100% matched-period level/lag coverage, exactly preserve the original missingness and deposit-rate series, and reproduce every frozen point-in-time geometry row. Under the latest vintage, the unchanged full panel still fails at 96, 120, and 144 months; each window retains one persistent episode, and all 15 leave-one-feature-out window classifications remain unchanged across vintages.

**Boundary:** This is ex-post vintage-robust negative measurement evidence, not a pure numerical-revision effect, causal break, decision-time state, eligible model rescue, or transmission result. Conditional block-bootstrap intervals do not provide full factor-estimation inference. Independent reproduction and a focused closest-literature audit remain required before strong contribution or novelty claims.

## D032 — Authorize Run 011 positioning and clean reproduction

**Date:** 2026-10-04

**Decision:** Freeze `run-011-reproduction-and-positioning-v1` to audit the closest primary literature, reproduce Run 010 from a clean Git checkout and isolated runtime, and create paper-ready descriptive tables and figures from registered artifacts.

**Reason:** Run 010 materially strengthens the negative measurement result, but research value now depends more on credible positioning and reproducibility than on another model search. Exact reproduction and explicit closest-prior-art boundaries reduce the risk of overstating novelty or relying on an environment-specific result.

**Boundary:** Run 011 cannot estimate a new state model, change a threshold or classification, access transmission outcomes, promote the latest vintage to decision-time use, or make a causal revision claim. Any new empirical sensitivity requires a separate prospective protocol and approval.

## D033 — Accept exact reproduction and literature-positioned negative evidence

**Date:** 2026-10-04

**Decision:** Accept Run 011 as an exact clean-reproduction and paper-positioning pass. Upgrade C08 to clean-reproduced, literature-positioned negative evidence; preserve all Run 008–010 classifications, select no state, and keep transmission outcomes sealed.

**Reason:** A new temporary checkout of source commit `02fdfd1` in an isolated environment reproduces the comparison, geometry, episode, and audit outputs at exact SHA-256 equality. The closest-prior-art audit shows that the component methods are established and narrows candidate value to the prospective validation/governance sequence and its euro-area negative result. The deterministic paper bundle traces every displayed statistic to registered evidence.

**Boundary:** Exact reproduction has been demonstrated in one isolated environment, not yet across operating systems or a fully pinned release image. No factor method, stability diagnostic, vintage comparison, break test, model-confidence-set procedure, causal revision effect, transmission result, or novelty claim is authorized. Title reframing, release-environment pinning, and public-repository creation require their own approved implementation step.

## D034 — Reframe the paper and authorize Run 012 release preparation

**Date:** 2026-10-04

**Decision:** Adopt the working title *When a State Is Not Stable Enough: Real-Time Measurement Reliability in Euro-Area Monetary-Policy Research* and freeze `run-012-public-release-and-manuscript-v1`. Authorize dependency pinning, available-runtime reproduction, secrets and redistribution audits, README correction, and a claim-controlled manuscript architecture.

**Reason:** Run 011 establishes a clean-reproduced negative measurement result but no transmission estimate. The prior title foregrounded an unestimated amplification result. Release preparation now provides more scientific and professional value than another model search, provided the public surface accurately exposes the negative result and its boundaries.

**Boundary:** This decision does not authorize a GitHub repository, remote, open-source license, raw or processed data publication, external-validity estimation, model rescue, or transmission analysis. License and public-history choices remain owner decisions after the Run 012 audit.

## D035 — Accept locked reproduction and retain the publication gate

**Date:** 2026-10-04

**Decision:** Accept the Run 012 title, manuscript architecture, exact-version Python 3.9 lock, same-host exact reproduction, portable inventory, rights matrix, and public-CI boundary. Keep public repository creation blocked until the owner selects a license strategy, approves the first-export blueprint boundary, and authorizes a sanitized squashed export.

**Reason:** The locked clean archive reproduces all four Run 010 hashes, runs the complete frozen-commit test suite at 90% coverage, and leaves canonical outputs unchanged. The current tree has no detected credential signature or tracked raw/processed data. Existing local history contains workstation-path metadata, no license is selected, and no second runtime is available.

**Boundary:** This decision does not authorize GitHub creation, history rewriting, license selection, blueprint publication, raw/processed data distribution, external-validity estimation, state-model rescue, or transmission analysis. Exact version pins are not a cryptographic package lock, and same-host reproduction is not cross-platform evidence.
