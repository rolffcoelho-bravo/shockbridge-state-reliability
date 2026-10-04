# State-support and measurement-error design audit

**Experiment:** `state-support-power-v1`  
**Evidence status:** `SYNTHETIC_DESIGN_ONLY`  
**Result artifact:** `reports/methodology/state_support_power_v1.json`  
**Decision date:** 2026-10-02

## Audit conclusion

The proposed 47-event final block is not a defensible stand-alone sample for the primary state-dependent transmission contrast. In the prespecified simulation, a perfectly observed state with 20% minority prevalence has 26.0% rejection probability for a 0.5 residual-standard-deviation interaction and 63.7% for a 1.0 interaction. The average minority-state count is about nine events. A result from this block would be driven by a few high-leverage observations and could not distinguish a moderate interaction from noise.

The full 242-event replication sample is materially better but not automatically adequate. With 20% minority prevalence and no state error, the estimated power for a 0.5 standardized interaction is 82.3%. With 10% symmetric state misclassification, the probability-state estimator's power falls to 55.7%; with 20% misclassification it falls to 31.3%. This is an optimistic experiment because events and errors are independent and the misclassification process is known.

The design therefore separates two uses of time splits:

- the chronological final block remains essential for prospective reliability and forecast evaluation;
- it will not be the sole sample for the primary transmission interaction;
- the primary transmission estimate may use all eligible events once the state design and identification protocol are frozen without inspecting outcome magnitudes, subject to a formal analysis-sample decision and dependence-aware inference.

## Data-generating process

For event \(i\), the simulation uses

\[
Y_i = \delta X_i S_i + \varepsilon_i,
\]

where \(X_i\) and \(\varepsilon_i\) are independent standard normal variables, \(S_i\) is a Bernoulli minority-state indicator, and \(\delta\) is the interaction in residual-standard-deviation units for a one-standard-deviation shock. The fitted regression includes an intercept, the shock, and the shock-state interaction.

The observed hard state flips the true state with symmetric probability \(q\). The probability-state estimator replaces the hard state with the exact posterior probability \(P(S_i=1\mid W_i)\) implied by the known prevalence and error rate. This is a best-case regression-calibration benchmark, not a model of the errors expected from a fitted HMM.

Each cell uses 300 Monte Carlo replications, HC3 standard errors, and a two-sided 5% approximate Student-\(t\) critical value. The grid contains three sample sizes, four minority prevalences, three error rates, five interaction magnitudes, and three estimators. The largest possible 95% Monte Carlo margin for a reported rejection rate is about 5.7 percentage points. Cells near the 80% rule are screening results and require a focused high-replication rerun.

## Selected results

| Sample and state design | Interaction | Estimator | Rejection rate | Mean estimate | Coverage of true effect | Contrast information |
|---|---:|---|---:|---:|---:|---:|
| 47 events, 20% minority, no error | 0.50 | oracle hard | 26.0% | 0.501 | 91.0% | 7.3 |
| 47 events, 20% minority, no error | 1.00 | oracle hard | 63.7% | 1.027 | 92.3% | 7.4 |
| 242 events, 20% minority, no error | 0.50 | oracle hard | 82.3% | 0.515 | 96.7% | 38.8 |
| 242 events, 20% minority, 10% error | 0.50 | misclassified hard | 55.7% | 0.335 | 83.0% | 46.4 |
| 242 events, 20% minority, 10% error | 0.50 | posterior probability | 55.7% | 0.504 | 96.3% | 20.5 |
| 242 events, 20% minority, 20% error | 0.50 | misclassified hard | 31.3% | 0.221 | 56.3% | 52.5 |
| 242 events, 20% minority, 20% error | 0.50 | posterior probability | 31.3% | 0.501 | 95.3% | 10.2 |
| 242 events, 20% minority, 20% error | 1.00 | misclassified hard | 70.7% | 0.436 | 10.3% | 52.3 |
| 242 events, 20% minority, 20% error | 1.00 | posterior probability | 70.7% | 0.988 | 96.7% | 10.2 |

`Contrast information` is \(\sum_i(z_i-\bar z)^2\). It is the state variation available to identify the interaction after the main shock term is included.

## Why weighted ESS is insufficient

At 20% misclassification in the 242-event, 20%-minority scenario, the probability-state estimator has a mean minimum probability-weighted ESS of 117.7 but only 10.2 units of contrast information. The weights cover many observations because they are diffuse, yet the probabilities do not separate the states strongly. A large weighted ESS can therefore coexist with weak interaction identification.

Every support audit must report both state-specific weighted ESS and centered probability variation. Entropy, shock-dose overlap, leverage, and influence are also required. No state model may pass on row count or ESS alone.

## Measurement-error finding

Hard classification produces substantial attenuation and invalid coverage in this experiment. With 20% misclassification and a true 1.0 interaction, the hard-state mean estimate is 0.436 and its interval covers the true effect only 10.3% of the time. The ideal posterior-probability regression recovers a mean of 0.988 and 96.7% coverage, but it cannot recover the information destroyed by uncertain classification; its power remains 70.7%.

This pattern is consistent with the latent-class literature's warning that treating predicted classes as observed can attenuate downstream associations. The final empirical method must propagate first-stage state uncertainty by refitting the state model inside the inference procedure or by using a justified posterior-draw or bias-adjusted estimator. A plug-in probability alone is not sufficient evidence of valid two-stage uncertainty.

## Size instability in sparse states

The rarest 47-event scenarios also show unstable null rejection. At 10% minority prevalence, the oracle estimator has only about 4.6 to 4.8 minority events on average. Across random-seed cells, its null rejection reaches 13.8%. Three of 300 replications are singular in one cell. These screening estimates are imprecise, but they are large enough to reject a design that relies on approximately five minority events.

HC3 was chosen because leverage correction is preferable to unadjusted heteroskedasticity-consistent covariance in small samples, following MacKinnon and White (1985). HC3 does not make a sparse interaction well identified. The empirical study will also require event-dependence handling and a cluster or block bootstrap.

## Grid-based detectable-effect screen

At 20% minority prevalence:

| Sample | State error | Smallest grid effect reaching 80% with oracle state | Smallest grid effect reaching 80% with posterior probability |
|---|---:|---:|---:|
| 47 | 0% | greater than 1.00 | greater than 1.00 |
| 47 | 10% | greater than 1.00 | greater than 1.00 |
| 155 | 0% | 0.75 | 0.75 |
| 155 | 10% | 0.75 | greater than 1.00 |
| 242 | 0% | 0.50 | 0.50 |
| 242 | 10% | 0.50 | 0.75 |
| 242 | 20% | 0.75 | greater than 1.00 |

These are coarse grid results, not continuous minimum detectable effects. Different random seeds across error-rate cells also create Monte Carlo variation in the oracle columns. A focused rerun must use common random numbers and at least 5,000 replications around the final boundary.

## Decisions

1. Do not use the 47-event block as the sole confirmatory transmission sample.
2. Keep a two-state primary design. A three-state confirmatory model is ineligible unless observed support and a new power audit justify it.
3. Use filtered state probabilities as the primary state representation. Hard labels are descriptive.
4. Require both weighted ESS and contrast information. Neither metric alone is a pass condition.
5. Do not freeze a numerical support threshold until the smallest economically meaningful effect is defined in basis points or percentage points for each primary outcome.
6. Preserve the chronological final block for reliability evaluation and other genuinely prospective claims.

## Limitations

- The shock is standard normal rather than calibrated to the observed target-factor distribution.
- Residuals and events are independent; serial dependence, event clustering, common shocks, and influential crisis observations are omitted.
- State errors are symmetric, nondifferential, and known. Fitted latent states will have parameter uncertainty, label instability, and time-varying separation.
- The experiment has one outcome and no multiplicity penalty.
- Standardized effects are not yet mapped to the economic units of the three primary outcomes.
- Three hundred replications are adequate for screening, not a final power determination.

## Literature anchors

- [MacKinnon and White (1985)](https://doi.org/10.1016/0304-4076%2885%2990158-7), “Some heteroskedasticity-consistent covariance matrix estimators with improved finite sample properties,” *Journal of Econometrics* 29(3).
- [Bolck, Croon, and Hagenaars (2004)](https://doi.org/10.1093/pan/mph001), “Estimating Latent Structure Models with Categorical Variables: One-Step Versus Three-Step Estimators,” *Political Analysis* 12(1).
- [Hamilton (1989)](https://doi.org/10.2307/1912559), “A New Approach to the Economic Analysis of Nonstationary Time Series and the Business Cycle,” *Econometrica* 57(2).
- [ECB, “Composite Indicator of Systemic Stress”](https://data.ecb.europa.eu/data/datasets/ciss/data-information), official data and methodology page. The New CISS is daily and updated with the previous day's data; its exact series key and historical availability still require audit.

## Next acceptance gate

Audit the exact official state series and release clocks, build the point-in-time event panel, observe actual state prevalence and contrast information without opening outcome magnitudes, define the smallest economically meaningful interactions, and rerun only the relevant boundary scenarios with the observed shock distribution and at least 5,000 replications.
