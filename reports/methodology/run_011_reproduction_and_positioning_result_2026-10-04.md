# Run 011 reproduction and paper-positioning result

**Result date:** 2026-10-04  
**Protocol:** `run-011-reproduction-and-positioning-v1`  
**Primary status:** `EXACT_REPRODUCTION_AND_POSITIONING_PASS`  
**Evidence class:** real official ECB state data, outcome blind; literature and reproducibility audit  
**New empirical estimation:** none  
**Transmission outcomes accessed:** no

## Result

Run 010 reproduces byte for byte from the frozen Git commit in a new temporary
checkout and isolated virtual environment. The comparison, geometry, episode,
and audit hashes all exactly equal the registered targets, the canonical files
remain unchanged, and the temporary checkout was removed. A focused
closest-prior-art audit also narrows the defensible contribution: the factor
methods, geometry diagnostics, real-time/latest-vintage contrast, block
resampling, and failure thresholds are not novel. The paper's candidate value is
the prospective validation sequence and its disciplined negative conclusion in
this euro-area application.

The evidence now supports a reproducible measurement-reliability result. It
does not support a transmission, amplification, causal revision, structural
break, general factor-model failure, or novel-estimator claim.

## Exact clean reproduction

The reproducer archived source commit `02fdfd1`, hydrated only the five
registered local inputs after exact SHA-256 validation, created a new virtual
environment, installed the clean checkout, executed the frozen Run 010 command,
and compared every output at byte-hash level.

| Output | Registered and reproduced SHA-256 |
|---|---|
| Comparison CSV | `9044465d54cc51c1a7885c48d7228ba90e52747c814222cde0a0413f56ffb0df` |
| Geometry CSV | `7a639d4b2b9a4bed73ded627961bdd8c08cdfba13889adaab3f652ef6f24be32` |
| Episode CSV | `67dec146bae186bc9e5680be36ec6caf80443bbc3449af99601c4a8c53e5001b` |
| Audit JSON | `6631f7ad8fd2bffc2d1d606e39a187029ea96d5adac61269af4c25f3d6584b81` |

The isolated runtime used Python 3.9.6, NumPy 1.26.4, PyYAML 6.0.3,
openpyxl 3.1.5, certifi 2026.7.22, pip 26.0.1, setuptools 82.0.1, and
wheel 0.48.0. This establishes exact reproduction under one independently
created environment. It is not yet a guarantee against future dependency
resolution changes or a reproduction on a second operating system.

## Closest-prior-art boundary

The literature audit covers eight additional primary sources across euro-area
real-time data, factor instability, real-time factor estimation, revision
processes, forecast breakdowns, and model-selection uncertainty. Its main
implications are:

1. Euro-area vintage comparison and revisions are established research
   objects; Run 010 contributes a controlled application result, not the idea
   of comparing vintages.
2. Principal angles, projector distances, eigengaps, rolling factor geometry,
   and loading-instability analysis are established tools. The project's
   four-feature panel is outside large-cross-section factor asymptotics.
3. Real-time versus revised-data factor robustness is application dependent,
   so Run 010 cannot establish a general law about factor methods.
4. Run 009 episodes are descriptive geometry breaches, not formal forecast
   breakdowns or structural-break estimates; the kill gates are not a model
   confidence set.

Accordingly, the candidate contribution is an artifact-level, prospective
validation sequence showing that favorable predictive density can coexist with
an economically consequential lack of state-measurement stability; the negative
classification survives a matched-period latest official vintage; and the
prospective rule terminates the downstream study without outcome-driven model
rescue. Novelty remains provisional pending manuscript-level synthesis and
external review.

## Paper-ready evidence bundle

`reports/paper/run011/` contains three deterministic CSV tables, two accessible
vector figures, and one provenance record. Every number is generated from the
hash-bound Run 010 audit or episode artifact. The figures were rendered and
visually inspected after XML validation.

- The geometry table reports six full-panel vintage/window summaries.
- The value-difference table reports three feature summaries.
- The primary bootstrap table reports nine conditional paired summaries and
  explicitly denies full factor-uncertainty inference.
- The geometry figure presents the frozen failure references and both vintages.
- The episode figure presents six descriptive full-panel intervals under the
  primary 3/3 rule.

The bundle is machine-independent, deterministic across output directories,
immutable after publication, staged before atomic directory publication, and
tested to remove failed staging directories. Metadata prohibits causal revision,
structural-break, decision-time latest-vintage, and transmission claims.

## Defects found and corrected

- DEV-031 corrected a filename/path mapping error before reproduction began.
- DEV-032 preserved subprocess diagnostics after an isolated install failure.
- DEV-033 upgraded the disposable packaging toolchain and recorded its resolved
  versions before the successful execution.
- DEV-034 removed machine-specific output paths, made bundle publication atomic,
  and corrected a rendered legend/heading collision before registration.
- DEV-035 made every Make target use one configurable project interpreter after
  the final inventory wrapper exposed an implicit activated-shell dependency.

No defect changed an observation, statistic, threshold, classification, or
Run 010 artifact. Failed attempts produced no registered scientific evidence.

## Final verification

- all 73 locally registered artifacts pass path, byte-size, and SHA-256 checks;
- the empirical contract remains deliberately blocked on 11 unresolved
  transmission prerequisites;
- Ruff passes and confirms 121 Python files are formatted;
- strict mypy passes all 34 source files;
- all 137 discovered tests pass; and
- branch-aware coverage is 90%, meeting the frozen project floor.

## Negative-result estimand and external-validity boundary

The estimand is whether the frozen four-feature euro-area state measurement is
sufficiently stable across expanding and rolling information histories, and
robust enough to an ex-post matched-period official-vintage comparison, to pass
the prospectively frozen authorization rule for downstream transmission work.
The observed answer is no for every full-panel window.

The conclusion is bounded to the registered monthly sample, features, release
archive, observation-period choices, missingness mask, geometry definitions,
and 96/120/144-month histories. It does not imply that all latent factors, all
euro-area state measures, other feature panels, or other samples are unstable.

## Decision

Accept Run 011 as an exact clean reproduction and positioning pass. Upgrade C08
to clean-reproduced, literature-positioned negative evidence while retaining
the prohibition on a novelty claim. Preserve every Run 008–010 classification,
select no state, and keep transmission outcomes sealed.

Two material improvements require separate approval: reframe the working title
around measurement reliability rather than an unestimated transmission effect,
and add a fully pinned cross-platform environment/container before public
release. A public GitHub repository is now scientifically relevant, but only
after those release-readiness, licensing, redistribution, and secrets checks.
