# Point-in-time timing policy

Every modeled observation needs distinct timestamps for the economic observation, public release, first usable availability, ingestion, vintage, and decision. The binding test is:

```text
first_usable_timestamp <= decision_timestamp
```

For the transmission lane, `decision_timestamp` is the last admissible instant before the ECB announcement window. For a forecast, it is the forecast origin. For an allocation, it is the actual tradable decision time after execution lag. These clocks must not be merged.

State estimation uses expanding- or rolling-window fitted transformations and filtered probabilities. A full-sample scaler, factor loading, HMM smoother, revised macro value, event-window return, or unresolved future label is inadmissible.

Reliability outcomes enter the meta-model only when their horizon has matured and the realized value would have been observable. The guard in `shockbridge_state_risk.temporal` fails closed on future availability.

