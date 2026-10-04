# Run 008 execution preflight audit

**Audit date:** 2026-10-03
**Status:** pass; ready for the approved state-only execution
**Empirical Run 008 executed:** no
**Transmission outcomes accessed:** no

## Frozen scope

The user approved the exact numerical contract in `run_008_subspace_design_proposal_v1.yaml`. The design is now marked `APPROVED_AND_FROZEN_FOR_STATE_ONLY_EXECUTION`, and `state_model_evaluation_protocol_v3.yaml` is frozen. The authorization covers the registered real point-in-time state panel only. It does not cover shock data, response outcomes, transmission estimation, threshold changes, two-factor downstream use, or promotion of any Run 007 challenger.

The execution configuration is `experiments/state_model_run008_v1.yaml` with SHA-256 `5649f7a0c8bd5d0adff7d98998d3f7de04f33a399bf4d5e33c7d9e296788ce44`. It binds the approved design hash `2c43effad56a6135e2b13d7a0287c40da8837e728eb8cfe433bd65f2055e2ee2` and panel hash `80d5e5f4b04fb7551bc69d4c4b429271258efad09987d9971551fd4a477f527e`.

## Orchestration controls

`src/shockbridge_state_risk/state/run008.py`:

- verifies the approved-design and panel hashes both when loading the contract and at execution;
- revalidates the complete frozen empirical contract at execution, preventing a modified in-memory configuration from weakening gates;
- verifies the January 2002–December 2011 development block and January 2012–October 2025 evaluation boundaries;
- freezes the scalar slack loading from the development block and never re-estimates it afterward;
- uses only origin-available histories, with separate expanding and rolling-120 estimates;
- excludes the 61 mechanically shared origins from cross-window gates while retaining eligible observations for prospective scoring;
- evaluates all subspace and scalar gates conjunctively and prohibits score compensation for stability failure;
- reports the anchored two-factor model as diagnostic and explicitly ineligible for transmission;
- loads no shock, asset-price response, outcome horizon, or transmission dataset;
- validates nonempty bundles and distinct output paths before atomic per-artifact writes.

## Pre-empirical anomalies corrected

DEV-024 records three implementation issues found by preflight:

1. repeated LAPACK decompositions could differ at approximately machine precision, preventing byte-stable output despite identical scientific results;
2. the draft output persisted a raw PCA basis whose signs are mathematically unidentified; and
3. the bundle writer did not reject colliding output paths before beginning writes.

Persisted floats are now canonicalized to 12 significant digits, with absolute values below `1e-12` stored as zero. All gates continue to be evaluated at full floating-point precision. The output stores the rotation-invariant projector and economically aligned basis, not the unidentified raw basis. Contract authorization and output paths now fail closed.

## Verification

- 110/110 automated tests pass.
- Exact repeated Run 008 software executions produce identical structured outputs.
- A later state-data change cannot modify any earlier subspace, fixed-factor, or two-factor estimate.
- The development loading is invariant to all post-development changes in the no-future-information test.
- Hostile changes to authorization, outcomes, factor dimension, split, design hash, or schema fields fail closed.
- Strict mypy passes over 30 source files.
- Ruff lint and format pass over 96 files.
- Combined line-and-branch coverage is 90.83023543990086%.
- Run 008 orchestration coverage is 91.05882352941177%.
- Subspace-component coverage is 95.8955223880597%.
- Git diff whitespace validation passes.

## Code identities

- Run 008 orchestration SHA-256: `518d7c5acf44fe7884d053ced100fe78f9f8f0fcf2e07fd43572c435c5c3d2ec`
- Subspace component SHA-256: `12916ee63c787443bf156561161f392fe77adc541e89392e60309bf111c23986`
- CLI SHA-256: `827419ea933cab90d4babfbe52638afc38fd012ae82225279cda83d08a83363b`
- Run 008 test SHA-256: `746144464de1eb588453a7b754c898685d2fb14618581dc2ddcf708f7457fb58`

## Preflight decision

The software and frozen state-only contract are ready for empirical Run 008 from a clean local Git checkpoint. The execution must write the subspace, fixed-scalar, anchored-two-factor, and audit artifacts together. Results must be assessed against the frozen gates without threshold adjustment. Transmission remains sealed regardless of the state result until a later explicit decision.
