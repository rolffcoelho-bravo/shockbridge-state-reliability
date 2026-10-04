# Run 010 implementation preflight audit

**Audit date:** 2026-10-04  
**Status:** pass; implementation ready for the separately controlled source-retrieval step  
**Empirical Run 010 executed:** no  
**Latest-vintage observation data retrieved:** no  
**Transmission outcomes accessed:** no

## Frozen scope

The user approved the exact contract in
`research/methodology/run_010_vintage_robustness_proposal_v1.yaml`, SHA-256
`f85116d407019b9386101242e94381fa2973a1e39addfb24e4255653444db457`.
The implementation preserves each point-in-time row key, selected observation
period, original missingness and staleness decision, and deposit-facility value.
It replaces only the three macro values with latest-production values from the
same frozen ECB RTD concepts. HICP and industrial-production growth are
recomputed from latest-vintage levels at the selected period and its exact
12-month lag.

The exercise remains an ex-post matched-period latest-vintage sensitivity. It
cannot be described as a pure numerical-revision experiment, used as a
decision-time state, treated as causal evidence, used to revise the Run 008 or
Run 009 decisions, or used to authorize transmission estimation.

## Software and provenance controls

`src/shockbridge_state_risk/state/run010.py`:

- verifies the frozen design, point-in-time panel, Run 009 diagnostic, source
  manifest, and every source response by SHA-256 and byte length at load time
  and again immediately before computation;
- admits only the three exact approved HTTPS URLs, RTD series keys, dimensions,
  and local filenames, and records the resolved HTTPS URL, retrieval timestamp,
  response hash, size, and complete attempt sequence;
- retries only timeouts and the approved HTTP 429/500/502/503/504 conditions at
  the frozen 0/5/20-second schedule; all other retrieval failures stop without
  substitution;
- rejects schema changes, mixed series, deleted current observations,
  duplicates, non-finite values, missing required selected periods, missing
  year-over-year lags, changed row grids, or changed missingness;
- exactly reproduces every retained Run 009 point-in-time geometry row before
  calculating a latest-vintage result;
- evaluates unchanged 96-, 120-, and 144-month full-panel and four-way
  leave-one-feature-out geometry at full precision;
- uses the frozen 2014-02–2025-10 common origins and the 3/3 episode rule;
- reports paired circular block-bootstrap intervals using the frozen seed,
  replication count, and 12/24/36-month blocks without claiming full estimator
  uncertainty or confirmatory inference; and
- publishes the comparison, geometry, episode, and audit files as one immutable,
  atomic bundle and refuses existing or stale partial outputs.

No shock, return, response-horizon, or transmission dataset is imported or
referenced by the runner.

## Pre-empirical anomalies corrected

DEV-030 records four fail-closed defects found before retrieval or empirical
execution. The initial draft retried all download errors rather than only the
approved conditions, did not re-hash individual source responses immediately
before analysis, did not bind manifest entries to the frozen URL and series key,
and could overwrite existing final artifacts. All four controls are corrected
and covered by hostile tests. No empirical observation or result was produced
by the earlier draft.

## Verification

- 131/131 automated tests pass.
- Dedicated Run 010 tests cover deterministic repeated execution, exact Run 009
  geometry reproduction, exact missingness preservation, required-period and
  source-mutation failures, source-provenance substitution, approved retry and
  terminal-error behavior, CLI routing, atomic publication, and immutable
  outputs.
- Strict mypy passes over 34 source files.
- Ruff lint and format pass over 111 files.
- Combined line-and-branch coverage rounds to 90%; Run 010 orchestration coverage
  is 83%.
- Git diff whitespace validation passes.

## Code identities

- Run 010 orchestration SHA-256: `58dc0c6a9a9fc21d6ae865d7415e6e6cdf25c584773c234f034c369bcf7715db`
- CLI SHA-256: `c43e2fd5affccb174dd1d3f844c601a4fc5eaeb9175e437556273d9a48f53c31`
- Run 010 test SHA-256: `d9f09fa4727facb4a8df2391e63e65bb27b87c42ff182baf2eff248efc378bde`
- CLI test SHA-256: `5437cd2ad4dce8945fa441e0a18d167258a5508c0ea412f31fd87fe2b7430098`
- Makefile SHA-256: `710a21d98dc2927ac7ff00975f3a9a90913255d1de94d1a4304af1af6ce44b1f`

## Preflight decision

The implementation is ready for the approved source-retrieval step from a clean
local Git checkpoint. Retrieval must either publish all three exact, validated,
hash-bound ECB responses with their manifest or publish none. After successful
retrieval, the empirical configuration and a separate execution preflight must
be frozen before the one authorized Run 010 computation.
