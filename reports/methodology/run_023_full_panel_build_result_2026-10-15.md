# Run 023 — Official full-history retrieval and decision-time panel build

## Decision

Accept the conservative Run 023 panel build as a valid outcome-blind
feasibility result. Do not fit the reliability engine, generate scenarios,
select factor rank, evaluate authorization thresholds, or access transmission
outcomes in this run.

## Executed evidence

The accepted retrieval atomically promoted ten exact real, freely accessible
ECB series responses and seven official release-evidence responses. Every
record carries its registered URL, final same-host URL, UTC retrieval time,
byte count, content type, and SHA-256 hash. All 17 completed on their first
attempt in the accepted bundle. Three earlier attempts remain registered as
failures and promoted no partial bundle.

The build generated 274 first-calendar-day origins from January 2003 through
October 2025. P0 contains 1,918 panel-origin-series rows (7 series); P1 contains
2,740 rows (10 series). Both files have zero duplicate keys, non-finite values,
and point-in-time violations. No synthetic empirical observation was used.

For MIR and BSI, the preserved historical index establishes the release date,
while the usable time is the preregistered 10:00:01 Europe/Berlin calendar
convention. It is not a document-level timestamp recovered separately for
every historical release. This distinction does not invalidate the registered
build, but it is a sensitivity boundary for origins falling on a release date.

## Coverage

| Series | Observed origins | Coverage | First usable origin |
|---|---:|---:|---|
| RTD HICP | 271/274 | 98.91% | 2003-04 |
| RTD industrial production | 270/274 | 98.54% | 2003-05 |
| RTD unemployment | 274/274 | 100.00% | 2003-01 |
| Deposit-facility rate | 123/274 | 44.89% | 2015-08 |
| Two-year yield | 179/274 | 65.33% | 2010-12 |
| Ten-minus-two-year spread | 179/274 | 65.33% | 2010-12 |
| USD/EUR monthly change | 274/274 | 100.00% | 2003-01 |
| NFC borrowing cost | 255/274 | 93.07% | 2004-08 |
| Adjusted NFC loans | 102/274 | 37.23% | 2017-05 |
| M3 | 102/274 | 37.23% | 2017-05 |

P0 is fully observed at 123 origins. P1 is fully observed at 102 origins. The
reliability design is ragged-edge by construction, so complete-case counts are
not participation results; later training, minimum-count, staleness, rank, and
scenario gates remain unapplied.

## Corrections and failed attempts

- DEV-085 makes final-host equality and streaming byte limits enforceable.
- DEV-086 registers the official BSI historical release index prospectively.
- DEV-087 separates current-revision selection from decision-time availability.
- DEV-088 binds every stored response and corrects audit-hash semantics.
- DEV-089 handles official RTD Delete and explicit-missing action rows.
- DEV-090 freezes an explicit 180-second response timeout.
- DEV-091 adds at most three timeout-only attempts with recorded provenance.
- DEV-092 corrects the description of historical MIR/BSI timing from an exact
  time to an exact date plus the preregistered 10:00:01 calendar convention.

Retrieval attempt 1 stopped on RTD action-row semantics. Attempts 2 and 3
stopped on two different RTD transport timeouts. Every staging directory was
removed, and no failed attempt transformed observations or built a panel.

## Interpretation boundary

This run establishes that two wider official decision-time panels can be
constructed under the conservative registered clocks. It does not establish a
reliable state, useful authorization rate, high-dimensional asymptotics,
benchmark improvement, methodological novelty, or monetary-policy effect.

## Improvement opportunity requiring approval

The preserved pre-2017 BSI and pre-May-2004 MIR archive entries often use
generic visible titles, but their official link identifiers encode reference
months (for example, `md0404` and `mir0403`). A prospectively frozen parser for
those official identifiers could materially extend P1 coverage without adding
sources or synthetic data. Because that rule became salient after observing
the conservative coverage, it must be implemented only through a versioned,
owner-approved amendment with hostile identifier tests and a complete rebuild.

The same amendment should include a declared MIR/BSI timing sensitivity:
compare the registered 10:00:01 convention with conservative next-day
availability for releases dated on a panel-origin day. This avoids treating a
calendar convention as independently verified historical time and quantifies
whether the choice changes any panel vintage.

A second possible extension is an independently sourced effective-date clock
for the deposit-facility rate. The current full-history `VALID_FROM` contract
does not yield replay coverage before August 2015 even though the economic
series is older. That is a source-contract change, not a bug fix, and should not
be mixed with the archive-identifier amendment.

## Next gate

Recommended next step: approve only the official archive-identifier amendment,
including the timing sensitivity, rebuild P1, compare coverage, vintages, and
hashes against this immutable conservative version, and update manuscript
v1.10. Defer reliability-engine fitting until that decision is closed. The
deposit-rate source-contract extension should remain a separate later decision
so its effect is identifiable.
