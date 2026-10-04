# System architecture — Milestone 0

The foundation has four executable boundaries:

1. the empirical contract states what may be estimated and carries an explicit status;
2. the contract auditor blocks real estimation when required fields are unresolved;
3. the temporal guard rejects information unavailable at the decision origin;
4. the synthetic replay exercises the controls without being mistaken for evidence.

Future modules must depend inward on these controls. No model module may bypass contract readiness or construct its own looser timing rule.

```text
source metadata -> rights gate -> point-in-time records -> feature/model pipeline
                         |                 |
                         v                 v
                  no raw publish      fail on leakage
```

The causal, forecast/reliability, and allocation lanes share validated inputs and experiment metadata but have separate contracts, targets, clocks, and claims.

