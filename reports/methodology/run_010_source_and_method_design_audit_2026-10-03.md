# Run 010 source and method design audit

**Audit date:** 2026-10-03

**Evidence class:** design and official-source metadata only

**Outcome access:** none

**Empirical Run 010 data downloaded:** no

**Empirical Run 010 executed:** no

## Audit conclusion

Run 010 should be a matched-period latest-vintage sensitivity, not a claim to
isolate pure numerical data revisions. The design preserves every monthly origin,
the observation period selected by the real-time panel, its missingness/staleness
mask, and the unchanged deposit-facility rate. It replaces only the three macro
values with the latest official production version of the same ECB RTD concepts.

This is the cleanest feasible comparison because rebuilding an unconstrained
latest-data panel would mix revisions with newer release availability and a
different ragged edge. It still cannot separate ordinary revisions from rebasing,
seasonal-adjustment, benchmark, or euro-area-composition changes embedded in the
latest official vintage. The protocol therefore prohibits the label “pure
revision effect.”

## Official-source metadata audit

Only `detail=nodata` metadata requests were made. No Run 010 observations were
retrieved or analysed. The inspected fields and rejected direct substitutions are
stored in `data/manifests/run_010_source_metadata_audit_2026-10-03.yaml`.

| Role | Proposed series | Metadata verified | Decision |
|---|---|---|---|
| HICP level | `RTD.M.S0.N.P_C_OV.X` | Monthly, RTD moving euro-area concept, unadjusted overall HICP index; current downstream series is an official HICP index | Admit provisionally |
| Industrial-production level | `RTD.M.S0.Y.I_XCONS.X` | Monthly, RTD moving euro-area concept, working-day and seasonally adjusted, total industry excluding construction, index | Admit provisionally |
| Unemployment rate | `RTD.M.S0.S.L_UNETO.F` | Monthly, RTD moving euro-area concept, seasonally adjusted total unemployment rate, percentage | Admit provisionally |
| Deposit-facility rate | frozen panel value | Exact existing `FM.D.U2.EUR.4F.KR.DFR.LEV` value is copied | Do not redownload or alter |

The portal currently maps the RTD industrial-production and unemployment concepts
to fixed-composition EA21 (`I10`) production series. A direct substitution of the
headline `STBS.M.I10...` or `LFSI.M.I10...` series was rejected: it would silently
change the registered RTD source contract and make the geography change look like
a simple revision. Keeping the RTD keys retains the database's documented moving-
concept interface, while the limitation remains explicit.

The ECB Data Portal API documents `includeHistory=false` as the production version
and `includeHistory=true` as production plus previous versions. The proposed pull
uses `false`, stores the exact HTTP responses locally, and records byte counts,
retrieval timestamps, and SHA-256 hashes before any transformation. The ECB's
published statistics are free to access and reuse with attribution; this project
will nevertheless retain raw responses under its conservative fetch-only public
release policy and will disclose that year-over-year rates are own calculations.

Repeat metadata checks exposed intermittent ECB API read timeouts after earlier
successful certificate-verified responses. This did not change the metadata
finding and no fallback source was used. The proposed retrieval contract therefore
allows at most three audited retries for timeouts, HTTP 429, and HTTP 5xx responses,
with fixed backoff and no insecure TLS or partial-response acceptance.

## Methodological contract

For every nonmissing macro row in `monthly_state_panel_v2.csv`, Run 010 will look
up the latest-vintage level for that row's already selected `observation_period`.
HICP and industrial-production growth will be recomputed from that level and the
level exactly 12 months earlier. Unemployment remains a level. Originally missing
rows remain missing even if the latest vintage could fill them. Any unavailable
required level stops the run; the design requires 100% coverage of originally
observed macro rows.

The comparison then repeats the unchanged Run 009 factor-geometry estimator,
windows (96/120/144 months), common sample (2014-02 through 2025-10), thresholds,
episode rule, and four deletion sensitivities. The primary question is whether the
full panel still fails all three window classifications. No result may select or
rescue a state, relax a threshold, or open transmission outcomes.

Value discrepancies will be reported feature by feature in native units and in
standard deviations frozen from the 2002-01–2011-12 point-in-time development
period. Dependent uncertainty for paired diagnostic summaries is proposed using
1,999 circular moving-block resamples with a 12-month primary block and 24/36-month
sensitivities. These intervals are conditional on the estimated diagnostic paths;
they are not full factor-estimation uncertainty and will not be presented as
confirmatory tests.

## Literature audit

Croushore and Stark (2001) show why estimates and forecast comparisons based on
latest data can differ from what was feasible in real time. Bernanke and Boivin
(2003) provide the closest factor-model counterpoint: in their data-rich monetary-
policy application, the forecasting result did not appear to depend on final
rather than real-time data. These precedents make vintage robustness an empirical
question; neither establishes the answer for this four-variable euro-area state
measurement.

## Threat and anomaly audit

1. **Information-set contamination:** prevented from entering the causal lane by
   the explicit `EX_POST_LATEST_VINTAGE_NOT_DECISION_TIME` label.
2. **Ragged-edge confounding:** prevented by preserving selected observation
   periods and missingness exactly.
3. **Geography/definition confounding:** not fully removable; disclosed and
   bounded by using the same RTD concept keys rather than direct headline-series
   substitution.
4. **Transformation mismatch:** prevented by recomputing both year-over-year
   features from latest levels at `t` and `t-12`.
5. **Silent incomplete joins:** prevented by a 100% required-level coverage gate.
6. **Threshold shopping:** prevented by reusing every Run 009 geometry threshold.
7. **False rescue:** prohibited even if latest data look more stable, because those
   values were unavailable at the historical decision time.
8. **Dependence understatement:** addressed conditionally by the proposed paired
   block-bootstrap summaries, with explicit limitations.

## Storage and execution gate

The exact proposed contract is stored in
`research/methodology/run_010_vintage_robustness_proposal_v1.yaml`. The metadata
audit, literature links, decision record, novelty boundary, and results-register
entry are stored in the canonical project. No Run 010 raw or derived empirical
artifact exists yet.

The next step requires explicit approval of the exact contract. After approval,
the implementation sequence is: build and adversarially test the fetch/validation
and matched-period join; run the full quality suite; freeze a clean pre-execution
checkpoint; retrieve and hash only the three official real series; then execute
the outcome-blind robustness analysis once.
