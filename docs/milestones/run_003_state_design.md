# Run 003 — state-panel contract and power audit

**Date:** 2026-10-02  
**Evidence status:** synthetic design evidence only

## Completed

- wrote a point-in-time state-panel contract with exact event-cutoff, vintage, provenance, transformation, missingness, and staleness requirements;
- established an outcome firewall so state-series and estimator selection cannot use event-response magnitudes;
- implemented a deterministic interaction-power simulator with HC3 inference, hard-state misclassification, posterior probability conditioning, weighted ESS, and centered contrast information;
- ran 180 prespecified design cells across 47, 155, and 242 events, four minority-state prevalences, three state-error rates, and five standardized interactions;
- added an executable CLI, frozen experiment configuration, machine-readable result artifact, tests, and a literature ledger;
- separated the transmission-inference sample decision from the prospective reliability holdout decision.

## Main design result

The 47-event block cannot be the sole primary transmission sample. With a perfectly measured 20% minority state, estimated power is 26.0% for a 0.5 standardized interaction and 63.7% for a 1.0 interaction. The average minority-state count is approximately nine.

The full 242-event sample reaches 82.3% screening power for a 0.5 interaction with a perfect 20% minority state. Ten percent symmetric state error reduces the probability-state result to 55.7%; 20% error reduces it to 31.3%. Probability conditioning removes attenuation in the ideal known-error simulation but does not restore information.

## Methodological correction

Probability-weighted ESS is not a sufficient support statistic. Diffuse probabilities can give a high ESS while providing little cross-state variation. The empirical support gate now requires centered probability contrast information, entropy, shock-dose overlap, leverage, and influence in addition to counts and ESS.

## Claims still blocked

- the primary state estimator and exact state series;
- any empirical state-dependent response;
- a numerical minimum-support rule in the absence of an economic-unit smallest effect;
- a final transmission inference sample;
- task-specific reliability labels and probabilities.

## Next acceptance gate

Audit exact official series and their release clocks, construct the 242-event point-in-time state panel, and measure observed coverage and state separation without opening outcome magnitudes. Then define outcome-specific smallest effects and rerun the narrow power boundary with the observed shock distribution, dependence, and at least 5,000 replications.
