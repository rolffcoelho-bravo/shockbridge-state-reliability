# Run 009 instability-diagnostic component audit

**Date:** 2026-10-03
**Status:** design and software components complete; exact numerical contract awaits approval
**Transmission outcomes accessed:** none
**Empirical Run 009 execution:** none

## Scientific role

Run 009 is a forensic state-measurement diagnostic after the Run 008 kill gate. It cannot select a replacement state, relax any Run 008 gate, reopen transmission, or make causal claims about monetary regimes. Its purpose is to distinguish pervasive factor-space instability from window-specific estimation behavior and to document why favorable predictive density coexists with unreliable economic state orientation.

## Literature and inferential boundary

Davis and Kahan (1970) justify relating eigenspace rotation to perturbation magnitude and eigengaps. Breitung and Eickmeier (2011) establish the importance of loading instability in factor models. Koo, Wong and Zhong (2025) provide close current prior art for distinguishing factor-variance from loading breaks.

Those econometric break procedures are principally large-factor-model methods. This project has four features. Run 009 therefore uses finite-dimensional descriptive geometry and does not report a high-dimensional structural-break p-value, identify a causal break, or claim that an eigengap ratio is a formal test statistic.

## Implemented components

`src/shockbridge_state_risk/state/instability.py` implements:

- the exact window-standardized Gram matrix underlying the Run 008 PCA estimator;
- principal cosines and normalized projector distance independently of the Run 008 implementation;
- spectral and normalized Frobenius Gram drift;
- absolute and relative second-versus-third eigengaps;
- a descriptive perturbation-to-minimum-eigengap ratio;
- upper-triangle squared-drift attribution, with diagonal missingness-weight effects separated from off-diagonal feature-pair comovement;
- feature-level location, scale, and missingness drift;
- prespecified near-zero versus substantive scalar sign disagreement;
- point-in-time policy-rate sign regimes; and
- consecutive-calendar breach episodes with independent onset and recovery persistence.

The geometry test confirms that the Gram-based principal cosines and projector distance match the existing Run 008 estimator to numerical tolerance.

## Pre-empirical correction

DEV-025 records issues corrected before real-data execution. The initial proposal referred to a correlation matrix. Under missing-at-standardized-mean handling, the estimator actually uses a standardized Gram matrix whose diagonal reflects feature availability. Run 009 now reports diagonal drift as a missingness-weight effect and off-diagonal drift as comovement. Empty and nonconsecutive episode calendars also fail closed. An independent schema check additionally rejected and corrected a malformed bare YAML key before the proposal could be frozen.

## Proposed exact contract

`research/methodology/run_009_instability_diagnostic_proposal_v1.yaml` proposes:

- rolling windows of 96, 120, and 144 months;
- within-window eligible histories plus a common February 2014–October 2025 comparison sample;
- the Run 008 geometry references of second cosine 0.75, its 10th-percentile reference 0.90, projector distance 0.35, and weak anchor capture 0.35;
- a weak relative eigengap cutoff of 0.20;
- a high perturbation-to-gap ratio cutoff of 1.00;
- a weak-identification coincidence flag at a 50% rate among core-breach months;
- a primary episode rule of three consecutive breach months followed by three consecutive stable months, with 1/1 and 6/6 sensitivities;
- point-in-time deposit-facility-rate regimes classified as negative, zero within `1e-12`, or positive;
- a primary substantive sign threshold of 0.25 standardized units, with 0.10 and 0.50 sensitivities; and
- a pervasive-geometry-failure label only if every 96/120/144 window fails both the common-sample second-cosine and projector-tail references.

All classifications are descriptive. They do not change the Run 008 decision.

## Verification

- 115/115 automated tests pass.
- Strict mypy passes over 31 source files.
- Ruff lint and format pass over 100 files.
- Combined line-and-branch coverage is 91.03885804916733%.
- The new instability component has 96.03960396039604% line-and-branch coverage.
- Hostile infinite, constant, dimension-mismatched, non-Boolean, empty, malformed, and nonconsecutive inputs fail closed.
- Only synthetic arrays were processed by the new component.

## Approval boundary

Approval of the exact contract would authorize freezing an outcome-blind Run 009 configuration, implementing and testing its orchestration and complete provenance outputs, and then conducting a separately audited diagnostic execution. It would not authorize state selection or transmission estimation.
