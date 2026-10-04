# Run 007 execution preflight audit

**Audit date:** 2026-10-03  
**Evidence boundary:** real point-in-time state inputs authorized; transmission outcomes sealed  
**Empirical Run 007 status at audit:** not executed

## Frozen execution contract

- Configuration: `experiments/state_model_run007_v1.yaml`
- Configuration SHA-256: `cce1972a3a057943c805f2e3bdac0f909ad996e5b99bf41fcecc885e132d006d`
- Input panel SHA-256: `80d5e5f4b04fb7551bc69d4c4b429271258efad09987d9971551fd4a477f527e`
- Inputs: four real point-in-time monthly features, January 2002 through October 2025
- Histories: expanding and rolling 120 months; 60-month warm-up
- State challengers: exact scalar-factor clustering, full-rank PCA emissions, and diagnostic HMM; two and three states
- Factor eligibility: every frozen cross-window, loading, and sign-anchor gate is required; predictive score cannot compensate for failure
- Outcome firewall: no transmission outcome is loaded or referenced by the Run 007 module

## Corrections made before execution

1. Cross-window stability excludes origins for which expanding and rolling histories are mechanically identical. The gate begins only after the rolling window first truncates; all post-warm-up origins remain in prequential scoring.
2. Exact-factor log scores are explicitly labeled as scalar-factor densities and are not compared with four-feature PCA/HMM densities.
3. Configuration loading now rejects string-valued booleans, malformed grids, missing nested settings, non-finite settings, changed panel hashes, and any departure from the frozen Run 007 values.
4. The panel hash is checked again immediately before estimation to close the load-to-execution integrity gap.
5. Machine audit output records the configuration hash, panel hash, features, windows, state counts, numerical controls, thresholds, score domains, and outcome-firewall status.

The first item is recorded prospectively as DEV-022. No Run 007 state estimate or transmission outcome was inspected before this correction.

## Verification evidence

- `ruff check .`: passed
- `ruff format --check .`: passed
- strict `mypy src`: passed for 28 source files
- unit and integration suite: 101/101 passed
- combined statement-and-branch coverage: 90.44740024183797%
- Run 007 orchestration module coverage: 89%
- exact repeat test: passed
- hostile configuration and hash-change tests: passed
- no-future-information test: passed after an extreme last-month perturbation; every earlier factor row, challenger row, and restart record remained identical
- synthetic data role: confined to software tests; not eligible for empirical output

## Pre-execution judgment

The implementation is eligible to execute the outcome-blind Run 007 state evaluation. This judgment does not authorize joining policy-shock outcomes, market responses, or any other transmission outcome. Promotion of the continuous factor remains conditional on passing every frozen state/loading gate in the empirical audit.
