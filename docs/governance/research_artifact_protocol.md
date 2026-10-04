# Research artifact and evidence protocol

## Objective

Every scientific result must be recoverable, attributable, and classifiable without relying on chat history or memory. The canonical project root is the sole working directory; Git-tracked records and hash-registered local artifacts jointly form the evidence package.

## Required run bundle

Before execution, assign a versioned run ID and freeze the configuration. After execution, retain:

1. configuration and evidence class;
2. exact command and software implementation paths;
3. input paths, byte sizes, hashes, source URLs, and rights status;
4. output paths, byte sizes, and hashes;
5. audit with every gate, warning, and outcome-firewall status;
6. human-readable interpretation with claim boundaries;
7. results-register entry, decision-log entry, and deviation entry when applicable;
8. tests, static checks, and local Git checkpoint.

Run IDs and output paths are immutable. A correction receives a new version or an explicit amendment; a failed or null run is never overwritten or deleted.

## Evidence classes

- `SYNTHETIC_DESIGN_ONLY`: software or design evidence; no substantive data claim.
- `REAL_DATA_OUTCOME_BLIND`: real pre-treatment data; no response magnitude accessed.
- `EXPLORATORY_REAL_DATA`: real outcomes opened outside a frozen confirmatory design.
- `CONFIRMATORY_REAL_DATA`: eligible only after contract freeze, identification, support, and inference gates.

Synthetic observations may test code and estimators but may never extend, impute, or replace empirical observations.

## Claim chain

Each manuscript claim links to a results-register row, manifest, code checkpoint, source hash, and robustness status. Candidate novelty also links to the novelty and literature ledgers. A causal or predictive statement cannot inherit authority from a descriptive state-model result.

## Storage and recovery

Git tracks code, contracts, manifests, audits, and paper records. Raw and derived data remain local and ignored until redistribution rights are explicit; each is hash-registered with a deterministic recovery path. `make quality`, `make test`, and the local inventory verification are required before a checkpoint.

Local Git is not an off-device backup. Before public release, create a remote after a rights, secrets, history, and reproducibility audit. Until then, loss of the device remains a residual storage risk despite local hashes.
