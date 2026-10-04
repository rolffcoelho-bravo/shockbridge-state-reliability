# Outcome-blind state replay audit

**Run:** `state-replay-v1`

**Date:** 2026-10-02

**Evidence class:** real data, outcome blind

**Decision:** reject as primary estimator; retain as a benchmark

## What was estimated

A two-state diagonal-Gaussian hidden Markov model was refit at every eligible ECB event using only earlier observations. The four inputs are HICP year-on-year inflation, industrial-production year-on-year growth, unemployment, and the deposit-facility rate. All are real, freely retrievable sources admitted by the point-in-time panel contract. The first 40 events are a warm-up, leaving 202 filtered event probabilities.

No event-response outcome was accessed. The target shock was joined only after the replay to measure sign and dose support; it was not used to estimate, label, select, or tune the state model.

## Results

- The HMM improves cumulative prequential log score by 261.49 relative to the prespecified state-independent diagonal Gaussian.
- Global hard counts are 135 and 67; global probability-weighted ESS values are 135.17 and 67.24.
- The states are economically distinguishable. State 0 has lower inflation (1.45%), weaker industrial production (-0.38%), higher unemployment (9.76%), and a lower policy rate (-0.03%). State 1 has higher inflation (3.32%), stronger production (0.66%), lower unemployment (7.21%), and a higher policy rate (2.47%). These descriptions are ex-post labels, not manually imposed regimes.
- Filtered assignments are highly concentrated: mean entropy is 0.0045 and the median is effectively zero.
- Average restart agreement is 0.997, but the minimum is 0.70 on 2008-09-04; 2008-10-02 is also below the frozen 0.85 threshold.
- State 1 has no hard assignments in the middle chronological third and weighted ESS of only 3.10 in that block. Global balance therefore overstates temporal overlap.

## Screening decision

The benchmark fails the frozen minimum-restart-agreement gate. It also raises a separate temporal-support warning not used retroactively as a v1 gate. Transmission outcomes remain sealed. The result cannot support a claim that ECB transmission differs by state.

## Methodological lessons

The event-indexed HMM treats every interval between meetings as one transition even though intervals vary. The long absence of state 1 suggests that the model may partly recover monetary-policy eras rather than a recurring conditioning state. The approved expansion will therefore estimate states on a regular monthly real-time calendar and sample filtered probabilities at event cutoffs. PCA plus clustering, a dynamic-factor benchmark, and a change-point benchmark remain required under Blueprint V2.

## Reproducibility

The exact command, source hashes, implementation hashes, output hashes, gate values, and evidence restrictions are recorded in `state_replay_v1.manifest.yaml`. The probability file is local and Git-ignored but is hash-registered in the local artifact inventory.
