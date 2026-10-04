# Point-in-time state-source audit and candidate panel

**Audit date:** 2026-10-02  
**Evidence status:** source audit and outcome-blind data engineering; no transmission estimate  
**Event universe:** 242 frozen ABGMR press-release factor dates, 2002-01-03 to 2025-10-30

## Result

The previous “state data not yet joined” limitation is resolved. A candidate long-format panel now contains 1,210 rows: 242 event cutoffs by five features. The automated audit reports zero point-in-time violations and zero duplicate event-feature keys. The build reads only the factor artifact's `date` column; it never parses `target` or any market outcome.

Four features are admitted to the next state-model screening stage: the ECB deposit-facility rate, real-time HICP inflation, real-time industrial-production growth, and the real-time unemployment rate. The 10-year minus 2-year ECB yield-curve slope is retained as a conditional challenger. New and legacy CISS are excluded from causal state construction.

This is a data-readiness result, not evidence of state-dependent transmission. State probabilities, observed support, and empirical power have not yet been estimated.

## Event and release clock

Each event cutoff is the scheduled ECB monetary-policy decision release in Frankfurt local time:

- 13:45 before 21 July 2022;
- 14:15 from 21 July 2022 onward.

The implementation uses the `Europe/Berlin` IANA time zone so daylight-saving offsets are date-specific. Equality is prohibited: a value with `first_usable_timestamp == state_cutoff_timestamp` fails the temporal guard.

## Frozen source definitions

| Feature | Exact source | Transformation and availability | Status | Coverage |
|---|---|---|---|---:|
| HICP inflation | `RTD.M.S0.N.P_C_OV.X` | Year-over-year percent change computed inside each as-of vintage; maximum age 90 days | Admitted | 240/242 |
| Industrial production | `RTD.M.S0.Y.I_XCONS.X` | Year-over-year percent change computed inside each as-of vintage; maximum age 120 days | Admitted | 235/242 |
| Unemployment | `RTD.M.S0.S.L_UNETO.F` | Latest real-time unemployment-rate level; maximum age 120 days | Admitted | 233/242 |
| Policy rate | `FM.D.U2.EUR.4F.KR.DFR.LEV` | Last effective daily rate strictly before the event date | Admitted | 242/242 |
| Yield-curve slope | `YC.B.U2.EUR.4F.G_N_C.SV_C_YM.SR_10Y` minus `...SR_2Y` | Prior base-day spot rates, conservatively treated as published next business day at noon | Conditional challenger | 209/242 |

The 33 missing yield-curve observations all precede the official curve history beginning on 2004-09-06. The challenger is not promoted to the primary lane because the retrieved curve files do not expose observation-level vintage actions. The ECB states that the curves are estimated and released daily at noon with the previous day as the base period, but the present extract alone cannot prove that every historical numerical value is unrevised.

## Real-time macro reconstruction

For 2001–2014, the official ECB archive contains 168 monthly snapshot files. Each snapshot is treated as usable only from 00:00 Frankfurt time on the first day after its named vintage month. This is intentionally conservative because the archive name identifies a month, not a universally auditable intramonth timestamp.

From 2015 onward, the build uses API `VALID_FROM` timestamps. `Replace` actions overwrite the earlier value for the same observation period, and `Delete` actions remove it from the as-of information set. Transformations are computed after reconstructing that information set. Thus a year-over-year rate never combines the current vintage numerator with a later-revised denominator.

The build selects the latest period for which the complete transformation is available. It does not mark a feature missing merely because a newer isolated numerator lacks its 12-month lag. Conversely, it does mark an otherwise available value missing when its observation age exceeds the prespecified staleness limit.

## Anomalies found and controlled

### CISS is not point-in-time admissible

The inspected New CISS series is `CISS.D.U2.Z0Z.4F.EC.SS_CIN.IDX`. Every September 2008 row in the versioned API extract has `VALID_FROM = 2026-10-01T09:15:45+02:00`; the same timestamp appears for the inspected October 2025 history. The legacy series `CISS.D.U2.Z0Z.4F.EC.SS_CI.IDX` assigns the inspected September 2008 rows to `2025-04-15T10:35:53+02:00`.

Those timestamps document post-sample replacement loads, not the values available at the historical meeting. CISS is therefore excluded from the causal state panel. It may be shown only as a retrospectively reconstructed descriptive series unless archived vintages are found.

### Unemployment vintage gap

The chosen unemployment RTD history has no new usable vintage between 2024-03-06 and 2025-07-23. Without a staleness rule, the June 2025 meeting would inherit a January 2024 observation that is 491 days old. The 120-day gate instead produces explicit missing values for nine meetings from 2024-06-06 through 2025-06-05.

### Other explicit missingness

- HICP: two event rows are missing after the 90-day rule.
- Industrial production: seven event rows are missing after the 120-day rule and transformation-completeness check.
- Deposit-facility rate: no missing event rows.
- Yield-curve slope: 33 pre-coverage rows are missing.

No future backfill or cross-series imputation is performed. Missingness and observation age remain available to the next-stage model.

## Provenance and redistribution boundary

Every retained row records the exact event cutoff, observation period, value, unit, first-usable timestamp, vintage ID, source series, source URL, raw-artifact SHA-256, transformation ID, observation age, vintage age, missing flag, and admission status. The source registry is `research/state_sources_v1.yaml`.

Artifact-level reuse was resolved conservatively:

- publicly released ECB statistics may be reused with attribution and disclosure of modifications, but the ECB policy excludes third-party data without originator permission;
- ECB authored workbooks and documentation remain fetch-only;
- the ABGMR factor page documents downloadable vintages and revisions but the inspected material contains no explicit redistribution license.

Accordingly, raw files and the derived event panel remain ignored locally. A public repository can include retrieval code, exact URLs, hashes, transformations, and attributed derived displays. It should not bundle the factor CSV, ECB workbooks, RTD archive, or documentation PDF without a narrower rights confirmation.

## Verification

The build command is:

```bash
state-risk build-state-panel research/state_sources_v1.yaml \
  data/processed/state_panel_v1.csv \
  --audit-output reports/methodology/state_panel_v1.audit.json
```

Quality verification on 2026-10-02:

- Ruff: pass;
- strict mypy: pass;
- 44 unit/integration tests: pass;
- branch-aware coverage: 91%, above the 90% gate;
- panel audit: 242 events, five features, 1,210 rows, zero temporal violations, zero duplicate keys.

## Remaining limitations

The target-factor vintage ending on 2025-10-30 is now explicitly a frozen replication sample, not a claim of being current to the audit date. The official EA-EMPD extension through 2026-03-28 remains a separate research lane and is not pooled into the identification sample.

The state data are now joined, so the earlier statement that no support assessment could begin before joining is superseded. However, a support or empirical-power conclusion still requires the next outcome-blind step: fit candidate state models by historical replay, measure state occupancy, entropy, effective sample size, and chronological-block support, and reconcile those quantities with the economic-unit smallest effect of interest. No transmission outcomes may be opened before that gate is frozen.

## Next-stage recommendation

Run a two-state filtered-probability replay on the four admitted features, with the yield slope as a challenger ablation and missingness handled transparently. Compare at least a simple interpretable benchmark (regularized logistic transition or Gaussian HMM with diagonal covariance) against a state-independent model. Select by pre-outcome criteria only: predictive state likelihood, stability across expanding refits, interpretable feature loadings, entropy, and support. Do not select the state model by transmission coefficient size or significance.
