# Run 009 execution preflight audit

**Audit date:** 2026-10-03
**Status:** pass; ready for the approved outcome-blind diagnostic execution
**Empirical Run 009 executed:** no
**Transmission outcomes accessed:** no

## Frozen scope

The user approved the exact Run 009 numerical contract and the four-way leave-one-feature-out sensitivity. The design is marked `APPROVED_AND_FROZEN_FOR_OUTCOME_BLIND_DIAGNOSTIC_EXECUTION`. It binds the registered point-in-time monthly state panel, the failed Run 008 manifest, and the frozen Run 008 scalar output. Run 009 cannot select or rescue a state, revise the Run 008 kill gate, identify a causal instability driver, estimate a large-panel structural-break test, or authorize transmission.

The execution configuration is `experiments/state_instability_run009_v1.yaml` with SHA-256 `2206cc98b815c93c0d85b0d8acca9db91cbdec131c33413d3d2a09f6ea50d022`. It binds design hash `b88a0bd9f945d2662f716cb129bb7aba0279be1b8955e8e4be3475dc9a4b45cf`, panel hash `80d5e5f4b04fb7551bc69d4c4b429271258efad09987d9971551fd4a477f527e`, Run 008 manifest hash `cdddd08dfff175726afccdd8c8e89c6d3bd1addf0db5f711999998b2ffd02237`, and Run 008 fixed-scalar hash `2afdaba561833a16d18bda92cc22534c55b5516cc7f5714b8212ae40c3691d95`.

## Prospective analytical rules

- Compare expanding histories with 96-, 120-, and 144-month rolling histories only after each rolling history first differs from the expanding history.
- Retain all eligible origin rows, but use February 2014–October 2025 as the common primary sample for percentiles, episodes, policy-regime summaries, and classifications.
- Diagnose exact standardized Gram matrices, principal cosines, normalized projector distance, spectral and Frobenius drift, second-versus-third eigengaps, perturbation-to-gap ratios, and upper-triangle drift contributions.
- Define a core breach as second principal cosine below 0.75 or projector distance above 0.35.
- Define a window-specific geometry failure only when common-sample cosine p10 is below 0.90 and projector-distance p90 is above 0.35. Label full-panel failure pervasive only when all three rolling windows fail.
- Define concurrent weak identification as minimum relative eigengap below 0.20 and perturbation-to-gap ratio above 1.00; flag coincidence only at a rate of at least 50% among core-breach months.
- Date primary breach episodes using 3-month onset and 3-month recovery persistence, with 1/1 and 6/6 sensitivities.
- Use the minimum policy-anchor capture across expanding and rolling histories for the weak-anchor diagnostic.
- Use the already-frozen Run 008 expanding and rolling-120 standardized scalar outputs for sign materiality at 0.25, with 0.10 and 0.50 sensitivities.
- Recompute geometry after omitting each feature separately. Deletion results are descriptive sensitivity evidence and cannot receive a causal-driver or state-rescue label.

## Orchestration controls

`src/shockbridge_state_risk/state/run009.py`:

- rechecks every input and design hash at configuration load and immediately before execution;
- hard-binds the production run to the approved design, panel, Run 008 manifest, and scalar hashes;
- verifies that Run 008 selected no state and kept transmission sealed;
- rejects nonconsecutive calendars, incorrect panel boundaries, missing common-sample scalar pairs, malformed upstream evidence, and non-finite data;
- evaluates classifications at full numerical precision and rounds only persisted scalar fields to 12 significant digits;
- produces deterministic origin-level diagnostics, episode records, and a structured audit;
- writes all temporary artifacts successfully before replacing any final output and rejects stale partial artifacts or colliding output paths;
- derives the evidence and synthetic-data labels from the validated execution class, preventing synthetic tests from being mislabeled as real evidence; and
- loads no shock, return, response-horizon, or transmission dataset.

## Pre-empirical anomalies corrected

DEV-026 records defects and underspecification corrected before execution. The first draft summarized thresholds from rounded persisted rows and hard-coded the real-data evidence label in synthetic tests. The design also left the weak-anchor history, primary episode sample, and scalar-sign source implicit. The runner now evaluates full-precision values, distinguishes software-test evidence, and freezes every source and reporting sample prospectively.

## Verification

- 120/120 automated tests pass.
- Run 009 software executions are structurally deterministic, and repeated bundles are byte-identical.
- A later panel change cannot modify diagnostics at or before its origin because each origin uses history ending strictly before that month.
- Hostile authorization, schema, factor-dimension, window, threshold, hash, upstream-manifest, boundary, serialization, and partial-artifact changes fail closed.
- Strict mypy passes over 32 source files.
- Ruff lint and format pass over 102 files.
- Combined line-and-branch coverage is 91.35290938569626%.
- Run 009 orchestration coverage is 93.92712550607287%.
- The instability component coverage is 97.02970297029702%.
- Git diff whitespace validation passes.

## Code identities

- Run 009 orchestration SHA-256: `ec6c0fd80f5d6e1192cdeb0424ef73e7882fc959c653f559a400ff6c3d40e127`
- Instability component SHA-256: `1d062b1840627aebad9fc830efe3ba78064f1ed1593f21d316708ca07d88f388`
- CLI SHA-256: `3a5a5fa8a931c9eb97bba1c4ebf057e7435c488c5a8ba4d9a6ceb851cd95f8d7`
- Run 009 test SHA-256: `5e6c2c09d1095054ee612524cefd7267923d94759466ca012021256d71fa1659`
- CLI test SHA-256: `b779e0c026f246476b728530f30fc98042f27fa8a14cd7dc0a8ee335f6af87cc`

## Preflight decision

The frozen outcome-blind diagnostic runner is ready for an empirical Run 009 from a clean local Git checkpoint. The execution must produce the origin-diagnostic CSV, episode CSV, and audit JSON as one bundle. The empirical result must be interpreted against the frozen descriptive classifications without changing thresholds, selecting a state, or opening transmission.
