# Run 009 episode amendment 1 preflight

**Audit date:** 2026-10-03
**Status:** pass; ready for the approved outcome-blind amendment
**Original Run 009 artifacts overwritten:** no
**Transmission outcomes accessed:** no

## Scope

The amendment adds one Boolean field, `open_at_sample_end`, to a versioned copy of the Run 009 episode artifact. It changes no episode start, end, duration, breach count, geometry metric, classification, or decision. The immutable Run 009 v1 diagnostic, episode, audit, manifest, and result report remain unchanged.

The frozen protocol is `research/methodology/run_009_episode_amendment_1_protocol.yaml`, SHA-256 `028e3393d24fd235fe09178b913f108364adae501561580e471f2c0d727af581`. The execution configuration is `experiments/state_instability_run009_v1_amendment_1.yaml`, SHA-256 `7e158eecf835acdddaf74dbbebca58d36dac12e45330b0dfc5352bcdb7cc0e3a`.

## Amendment controls

`src/shockbridge_state_risk/state/run009_amendment.py`:

- binds the original manifest, diagnostic CSV, episode CSV, and audit JSON by SHA-256;
- reconstructs every episode from the 2,115 primary-common-sample breach flags rather than editing the old CSV directly;
- requires all 11 original episode fields to match every immutable v1 row, in order, before adding the censoring field;
- sets `open_at_sample_end` only when no complete recovery sequence occurs before October 2025;
- derives software-test versus empirical evidence labels from the validated configuration;
- rejects altered source manifests, outcome authorization, changed schemas, incomplete variant-window cells, malformed breach flags, hash changes after validation, stale temporary files, and colliding output paths; and
- writes only new amendment paths after both temporary artifacts succeed.

## Preflight defects corrected

The first test implementation hard-coded the empirical 44-row count for synthetic fixtures. This did not affect real data or any Run 009 artifact, but it could misclassify a valid software fixture. Validation now requires exactly 44 source rows only for the production evidence class and requires a positive internally consistent count for software tests.

## Verification

- 124/124 project tests pass.
- Strict mypy passes over 33 source files.
- Ruff lint and format pass over 106 files.
- Combined line-and-branch coverage is 91.35486075516829%.
- Amendment orchestration coverage is 90.97222222222223%.
- The episode component coverage is 97.04433497536945%.
- Repeated synthetic amendment executions are structurally identical.
- Source mutation after validation and mismatches in manifest, schema, row count, breach flags, original values, or output paths fail closed.

## Code identities

- Amendment orchestration SHA-256: `0e453c5ad6ff1c086b382688569e2c4b8195e6e380fa0150012741c3e33692b7`
- Episode component SHA-256: `4a9442c583047d1756d3e8f3b82476cbf0f176fa3eb755cf56aaa9834e7f4973`
- Updated Run 009 future-output schema SHA-256: `897fe6721d0490dc215e90be7c9d6d27fca4bf9f57f84d4837f8ec1c08f3cdeb`
- CLI SHA-256: `dab6685dd2434a8898d1ae9ab3944e3ed530ed1763a3c5034b3352ce265df180`
- Amendment test SHA-256: `10169f03aa731ba74019c7d9df75fe8ef2a75900b5d704ced454a49af2ed5485`

## Preflight decision

The amendment is ready for execution from a clean local Git checkpoint. Successful execution must preserve all 44 original rows and fields exactly, add only the censoring flag, report the open rows explicitly, and leave every Run 009 classification and transmission boundary unchanged.
