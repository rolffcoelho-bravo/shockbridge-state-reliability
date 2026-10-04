# Run 007 preflight code and method audit

**Date:** 2026-10-02  
**Evidence class:** real-data outcome-blind implementation audit  
**Outcome firewall:** intact  
**Run 006 artifacts:** preserved unchanged

## Scope

The audit reviewed the outcome-blind state engine before the approved continuous-factor redesign. It covered HMM fitting and restart selection, matrix ingestion, configuration validation, determinism, point-in-time replay, numerical missingness behavior, and repository quality gates. No monetary-policy response outcome was accessed.

## Corrected defects

1. HMM EM used a transition-regularized MAP objective while restart selection used raw likelihood. The fit now stores both quantities, selects the restart by the optimized MAP objective, and retains raw likelihood for predictive scoring.
2. The event and monthly loaders checked duplicate IDs only after dictionary collapse. They now reject duplicate event/month-feature keys, incomplete requested grids, malformed missingness flags, inconsistent cutoffs, non-finite values, and naive monthly timestamps.
3. HMM initialization could create NaN state moments when an initialization cluster contained no observation for one feature. It now uses the same historical-window feature moments as a local fallback and rejects infinity rather than treating it as missing.
4. Comparison configurations could contain duplicated models or windows while passing set-equality checks. Grid uniqueness, flag types, optimization ranges, screening ranges, and primary-grid membership now fail closed.

These are implementation and integrity corrections. They do not modify the state variables, sample, thresholds, windows, outcomes, or estimand.

## Run 006 impact replay

The full frozen comparison was replayed in memory against the preserved CSV. Of 904 HMM rows, 678 differ under exact string comparison because a different MAP-preferred restart can be selected or floating values change at machine precision.

For the primary two-state expanding HMM:

| Quantity | Preserved v1 | Corrected implementation |
|---|---:|---:|
| cumulative log predictive score | -1629.210176515 | -1629.210259151 |
| score gain vs single Gaussian | 310.293765738 | 310.293683102 |
| minimum restart agreement | 0.7375 | 0.7375 |
| hard state counts | 74 / 152 | 74 / 152 |
| screening pass | No | No |

The same gates fail: middle-block hard count, middle-block weighted ESS, and restart agreement. Therefore the Run 006 kill gate and outcome seal remain scientifically unchanged. The original output, audit, and manifest remain immutable; the corrected selector applies prospectively.

## Adversarial checks added

- two executions of the complete comparison fixture must be exactly equal;
- an extreme mutation to the last month cannot alter any earlier estimate;
- raw duplicate or deleted feature keys must fail before matrix construction;
- cluster-local all-missing HMM features must retain finite parameters;
- infinite HMM inputs must fail closed;
- duplicated grid entries and invalid numerical settings must fail during configuration loading.

All synthetic arrays used by these tests are software fixtures only and do not enter empirical estimates.

## Verification

- 68 automated tests: pass;
- Ruff lint and format: pass;
- strict mypy over 19 source files: pass;
- branch coverage: 90%, meeting the frozen threshold;
- local artifact inventory: 22/22 hashes verified;
- empirical contract: correctly remains blocked by 11 unresolved scientific fields, including the state estimator and evaluation blocks.

## Scientific boundary

No state estimator has been selected and no transmission claim is licensed. Decision D016 remains the authorized next design: evaluate a continuous filtered factor, exact one-dimensional clustering, near-optimal stability, and a prospective expanding-versus-rolling consistency rule before outcomes are opened.
