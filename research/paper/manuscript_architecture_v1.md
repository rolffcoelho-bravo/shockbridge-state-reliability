# Manuscript architecture v1

## Working title

*When a State Is Not Stable Enough: Real-Time Measurement Reliability in
Euro-Area Monetary-Policy Research*

## Article type and evidence status

This is a measurement-reliability and scientific-governance application with a
prospective negative result. It is not a state-dependent transmission paper in
its current evidentiary form. Runs 007–010 use real, official, outcome-blind
state data. Run 011 establishes closest-prior-art boundaries and exact clean
reproduction. Run 012 adds an exact locked-environment reproduction.

## Central research question

Can a real-time euro-area macro state that appears useful under predictive
density tests remain economically and geometrically stable enough across
information histories to authorize downstream state-dependent monetary-policy
analysis?

The registered answer is no for the specific four-feature measurement,
calendar, sample, and validation rule studied here.

## Supporting questions

1. Do discrete, continuous, fixed-loading, or two-dimensional candidates pass
   every prospectively frozen support and stability gate?
2. Is rejection driven by weak factor identification, changing availability, or
   changing multivariate geometry?
3. Does the measurement classification survive a controlled matched-period
   latest official vintage?
4. Can the complete negative result be reproduced exactly from registered code,
   inputs, and dependency locks?

## Candidate contribution statement

The paper contributes an application-specific, auditable validation sequence in
which favorable predictive density does not override unstable economic
geometry; the negative decision survives an ex-post official-vintage
sensitivity; and the outcome firewall prevents a failed state measurement from
being converted into a post-result model rescue.

This is not a claim of a new factor estimator, stability statistic, bootstrap,
break test, model-confidence-set procedure, or vintage method. Contribution
language remains provisional until external review.

## Negative-result estimand

The estimand is whether the registered state measurement is sufficiently stable
across expanding and rolling real-time information histories, and sufficiently
robust to a matched-period official-vintage comparison, to pass the frozen
authorization rule for downstream transmission work.

The authorization rule is conjunctive. Predictive-density gains cannot
compensate for failed support, economic orientation, sign, loading, or subspace
geometry gates. The rule is a prespecified scientific decision policy, not a
formal model-confidence-set test.

## Section plan

### 1. Introduction

- Explain why state measurement must be validated before interaction effects
  are interpreted.
- State the negative result in the first two pages.
- Distinguish predictive usefulness from measurement stability.
- State why stopping before outcome estimation is an empirical contribution to
  credibility rather than an incomplete transmission result.
- Limit the contribution to the registered euro-area application.

Evidence: C08; Runs 006–012; D020, D023, D026, D031, and D033.

### 2. Institutional setting and point-in-time data

- Define the ECB decision-time information set and monthly cutoff rule.
- Describe the four admitted features: HICP year-over-year growth, industrial-
  production year-over-year growth, unemployment, and the deposit-facility
  rate.
- Document first-usable timestamps, staleness, missingness, and the separation
  between point-in-time and latest-vintage values.
- Explain why CISS and the yield-curve challenger are not promoted.
- State the fetch-only and attribution rules for external data.

Evidence: state source registry; state-panel and monthly-panel manifests; Runs
003–005; L017 and L019.

### 3. Prospective validation design

- Define expanding and rolling histories and the prequential density benchmark.
- Present candidate families without implying they estimate a true latent state.
- Explain the support, restart, economic-anchor, sign, loading, and subspace
  gates.
- Explain why the rule is conjunctive and outcomes remain inaccessible after a
  failed gate.
- Separate prespecified criteria from post-result diagnostic work.

Evidence: state-model protocols v1–v3; Runs 006–008; deviation log.

### 4. Candidate-model results

- Report every primary candidate, not only the best density score.
- Show that no primary model passes every gate.
- Report the continuous-factor and two-dimensional redesign results.
- Emphasize the conflict between density gains and economic/geometric stability.

Evidence: state-model comparison, Run 007, and Run 008 manifests and reports.

### 5. Anatomy of measurement instability

- Define principal cosine, normalized projector distance, Gram drift, eigengap,
  and breach episodes as descriptive diagnostics.
- Report all 96/120/144-month full-panel results.
- Separate off-diagonal comovement drift from diagonal availability effects.
- Report weak-identification coincidence and feature-deletion sensitivity.
- Do not label episodes structural breaks or causal regime changes.

Evidence: Run 009 diagnostic and amendment; L014–L016 and L020–L021.

### 6. Matched-period latest-vintage sensitivity

- Explain the fixed observation-period and missingness-mask design.
- State why the contrast is not a pure numerical-revision experiment.
- Report value differences, classification equality, episode overlap, and
  conditional block-bootstrap summaries.
- State that latest-vintage data cannot be used as a historical decision-time
  state.

Evidence: Run 010; L017–L019, L022–L024.

### 7. Closest prior art and contribution boundary

- Real-time macroeconomic databases and revision processes.
- Real-time factor estimation and forecasting.
- Loading/subspace instability and large-panel robustness.
- Forecast breakdowns and model-selection uncertainty.
- Clarify that the incremental candidate value is the prospective application
  sequence and outcome-preserving negative decision.

Evidence: literature ledger L001–L026 and the Run 011 prior-art audit.

### 8. Limitations and external validity

- Four features and no large-cross-section factor asymptotics.
- Registered 2002–2025 monthly sample and archive availability.
- Calendar, window, threshold, and feature dependence.
- Conditional rather than full factor-estimation bootstrap uncertainty.
- Ex-post latest vintage combines several possible data-production changes.
- One operating system and Python minor version reproduced the locked bundle.
- No conclusion about transmission, amplification, or general factor failure.

### 9. Reproducibility and data availability

- Describe manifests, SHA-256 checks, immutable run IDs, and deviation history.
- Report exact Run 011 and locked Run 012 reproduction.
- Separate public source code/manifests from fetch-only external artifacts.
- Provide exact environment locks and public CI boundaries.
- State the open-source license and repository URL only after owner approval.

### 10. Conclusion

- Restate that measurement authorization failed before outcomes were opened.
- Explain the value of a credible stopping rule.
- Treat alternative measurement systems and external-validity samples as future
  preregistered research, not retrospective rescue.

## Main tables

| Table | Content | Source | Status |
|---|---|---|---|
| 1 | Data timing, coverage, staleness, and missingness | Runs 003–005 | Existing evidence; paper table required |
| 2 | All primary model gates and decisions | Runs 006–008 | Existing evidence; paper table required |
| 3 | Full-panel geometry by window | Run 009/010 | `run010_table_geometry_v1.csv` ready |
| 4 | Matched-period value differences | Run 010 | `run010_table_value_differences_v1.csv` ready |
| 5 | Conditional paired uncertainty | Run 010 | `run010_table_bootstrap_primary_v1.csv` ready |
| 6 | Reproduction and artifact integrity | Runs 011–012 | Audit summary required |

## Main figures

| Figure | Content | Status |
|---|---|---|
| 1 | Prospective evidence and kill-gate sequence | New diagram required |
| 2 | Full-panel geometry by vintage | `run010_figure_geometry_v1.svg` ready |
| 3 | Persistent breach episodes by vintage | `run010_figure_episodes_v1.svg` ready |
| 4 | Off-diagonal Gram-drift attribution | Existing Run 009 evidence; new deterministic figure required |

Every published ECB-derived table and figure must say “Source: ECB statistics;
authors' calculations” and disclose transformations. Run 011 artifacts remain
immutable; publication captions carry the attribution if it is not embedded in
the underlying SVG.

## Appendix plan

- A. Exact data concepts, series keys, release timing, and source rights.
- B. Complete model grid and prospective gates.
- C. Numerical implementation and deterministic serialization.
- D. Every feature-deletion and block-length sensitivity.
- E. Episode hysteresis and right-censoring amendment.
- F. Reproduction environments, hashes, and artifact manifests.
- G. Complete deviation log and classification-impact table.
- H. Synthetic-only power and measurement-error demonstrations, clearly
  separated from empirical evidence.

## Claim-to-evidence controls

### Currently supportable

- The registered point-in-time panel has no detected temporal violation.
- No candidate state representation passes every frozen authorization gate.
- Full-panel geometry fails at all three registered rolling histories.
- The classification and every deletion-window classification survive the
  matched-period latest vintage.
- Run 010 reproduces exactly in clean and locked isolated environments on the
  audited host.

### Interpretation, not fact

- The validation sequence may be useful as scientific governance for
  state-dependent macroeconomic research.
- Off-diagonal drift is consistent with changing multivariate relationships but
  does not identify their economic cause.

### Prohibited

- State-dependent ECB transmission or amplification is established.
- Revisions causally worsen instability.
- The episodes are structural-break estimates.
- Factor models generally fail.
- The component econometric methods are novel.
- A feature deletion identifies an eligible replacement state.

## Manuscript completion gates

1. Every displayed number is generated from a manifest-bound artifact.
2. Tables 1, 2, and 6 and Figures 1 and 4 are generated deterministically.
3. Every citation has an exact proposition and locator in the literature ledger.
4. Abstract, introduction, and conclusion use the same estimand and boundaries.
5. Data availability and code availability statements match the final public
   export and selected license.
6. At least one independent cross-platform reproduction is recorded or the
   limitation remains prominent.
7. External review challenges the contribution and alternative explanations
   before submission.
