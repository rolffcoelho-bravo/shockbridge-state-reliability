# Public/private boundary

## Public candidates

- empirical contracts and identification memos;
- source adapters that do not embed restricted data or credentials;
- timing, leakage, validation, and challenger interfaces;
- synthetic fixtures and selected legally cleared derived displays;
- measured benchmark results with reproducible configurations.

## Private by default

- proprietary ShockBridge, BR-DTO, or AION methods;
- licensed raw data and non-redistributable derived artifacts;
- commercial feature definitions, signals, calibration, and deployment details;
- credentials, endpoints, and client information.

## Current license decision

The Milestone 0 no-license state was superseded by the owner-approved Run 013
boundary. Software is licensed under Apache-2.0. Owner-authored documentation,
tables, and figures are licensed under CC BY 4.0 unless a narrower source note
applies. Neither license covers external datasets, third-party materials, or
rights the owner does not hold. `LICENSE`, `LICENSE-DOCS.md`, and `NOTICE` are
the controlling repository files. This is a conservative release decision,
not a legal opinion.

## Repository separation

Use two independent repositories rather than changing one repository between
private and public visibility:

| Repository | Recommended name | Purpose |
|---|---|---|
| Public reproducibility surface | `shockbridge-state-reliability` | Sanitized single-commit code, tests, source metadata, aggregate displays, and research documentation. |
| Private canonical archive | `shockbridge-state-reliability-research-archive` | Full scientific history, private blueprints, internal decisions, and IP-bearing research records. |

Private visibility does not authorize redistribution of third-party data and
does not make GitHub an appropriate credential store. Raw and processed
external data remain outside both Git repositories unless exact redistribution
rights are recorded. Sensitive local evidence requires a separate encrypted
backup, not a Git commit.

## Artifact-level data reuse decisions

| Artifact family | Reuse finding | Repository decision |
|---|---|---|
| ECB Data Portal statistics | The ESCB policy permits free reuse of publicly released statistics with source attribution and requires disclosure of transformations. It excludes third-party data unless the originator permits reuse. | Publish series IDs, URLs, hashes, retrieval code, transformations, and attributed derived displays. Do not bundle raw extracts that may contain third-party inputs without a narrower rights review. |
| ECB authored workbooks and RTD documentation | The ECB disclaimer distinguishes statistical information from authored documents and requires explicit permission for republication of authored papers/documents in another publication. | Fetch-only; do not commit the workbooks, archive, or PDF. |
| ABGMR factor vintages hosted at gragusa.org | The download page documents the vintages and revisions but exposes no explicit redistribution license in the inspected material. Public download is not treated as permission to republish. | Fetch-only; commit the URL, SHA-256 hash, and date-only extraction code, but not the factor CSV. |

These are conservative repository decisions, not legal opinions. They can be relaxed only after a license or written permission is recorded for the exact artifact.
