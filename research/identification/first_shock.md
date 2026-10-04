# Identification memo — first ECB shock candidate

**Memo status:** provisional / causal claim blocked  
**Audit date:** 2026-10-02  
**Candidate:** press-release `target` factor, latest inspected vintage 2025-10-30

## Definition and timing

The candidate factor is derived from high-frequency OIS movements around ECB Governing Council press releases. The EA-MPD appendix describes a press-release window using pre-release and post-release median quotes. The factor source states that the target factor is normalized to have a unit effect on the one-month OIS surprise.

The candidate treatment must remain separate from press-conference `timing`, `fg`, and `qe` factors. Pooling press release and press conference windows would mix distinct information releases and treatment interpretations.

## Inspected evidence

| Artifact | Events | Unique | First | Last | Missing |
|---|---:|---:|---|---|---:|
| press-release target | 242 | 242 | 2002-01-03 | 2025-10-30 | 0 |
| press-conference factors | 237 | 237 | 2002-01-03 | 2025-10-30 | timing 0; fg 0; qe 138 |
| official EA-MPD scheduled-event dates | 315 | 315 | 1999-01-07 | 2025-10-30 | outcome-specific |
| official EA-EMPD extended events | 4,926 | composite key unique | 1999-01-07 | 2026-03-28 | outcome-specific |

There are five press-release dates without matching press-conference rows. The cause must be documented before a combined-window analysis. The QE factor's 99 non-missing observations make it unsuitable as the primary first-shock design without a separate support and selection analysis.

All 242 target-factor dates join to the official EA-MPD press-release sheet. The proposed primary outcomes—Italy–Germany 10-year spread, STOXX50, and EUR/USD—are complete on those dates. This resolves source coverage but does not establish identification or state support.

## Causal assumptions requiring defense

1. Within the narrow window, the factor is driven by the ECB communication rather than concurrent news.
2. The factor separates a policy shock from central-bank information effects well enough for the stated estimand.
3. The pre-event state is predetermined and not estimated with future observations.
4. There is overlap in shock dose across the prespecified state distribution.
5. State measurement error and factor estimation uncertainty do not create spurious heterogeneity.
6. Outcomes are measured on compatible clocks and are not components used mechanically to construct the shock.

## Mandatory falsifications and sensitivities

- flag concurrent scheduled macro or political releases;
- inspect influential events and leave-one-event-out sensitivity;
- compare hard state assignments with probability-weighted state exposure;
- test sign and dose support without data-mined cutoffs;
- use placebo non-event dates only for diagnostics, not as invented shocks;
- report state-independent, observed-stress, and transparent factor-state challengers;
- distinguish information-effect-robust shock variants where available.

## Current conclusion

The official source artifacts, outcome family, units, immediate event horizon, and public fetch-only policy are now fixed. The causal claim remains blocked by concurrent-news exclusions, information-effect sensitivity, pre-event state construction, overlap and power. The extended speech universe is not additional independent evidence for the primary estimand unless its separate identification design succeeds.
