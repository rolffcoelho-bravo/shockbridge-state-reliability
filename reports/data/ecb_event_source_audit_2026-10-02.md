# ECB event-source audit — 2026-10-02

## Decision

Use the original EA-MPD and the extended EA-EMPD as separate evidence lanes.

- **Replication/confirmatory lane:** scheduled Governing Council press-release events, target factor, original EA-MPD outcomes.
- **Extension/exploratory lane:** EA-EMPD speech and communication events. This lane requires its own shock construction, clustering, speaker controls, and identification assumptions.

Pooling the two lanes would inflate the apparent sample and mix different treatments.

## Original EA-MPD

- official ECB workbook update: 4 November 2025;
- 315 unique event dates in each of three event-window sheets;
- coverage: 7 January 1999 to 30 October 2025;
- 46 usable columns;
- no duplicate dates;
- announcement-window definitions change in July 2022;
- official workbook SHA-256: `f417fb861a305e3cbb871a7571c4899ba6bca003d9e087024d2f3f0744426cef`.

The author-maintained press-release target factor has 242 dates from 3 January 2002 to 30 October 2025. All 242 join exactly to the official press-release sheet. There are no missing joined values for DE2Y, DE10Y, IT10Y, FR10Y, ES10Y, STOXX50, SX7E, EUR/USD, EUR/GBP, or EUR/JPY.

## Extended EA-EMPD

- official ECB annex publication: 10 June 2026;
- 4,926 rows and 54 columns;
- coverage: 7 January 1999 to 28 March 2026;
- 318 GC press-release, 318 press-conference, and 318 monetary-event records;
- 2,972 Executive Board and 1,000 ECB President speech records;
- no duplicate composite keys across timestamp, event type, speaker, and title;
- official workbook SHA-256: `b4bdc1b90b9842227e74ff013eb79c71edce5dff9da1d5e02ac75b5d45c5e129`.

## Anomalies retained for the paper

1. The original workbook header is `STOXX50`, while its notes describe `STOXX50E`. The processed schema must use a canonical name and retain the source alias.
2. The EA-EMPD variable `Outside_regular_trading_hours` conflicts with its note, which says a value of one indicates the event window is *inside* regular hours. Do not use this control until verified against the paper/code or the authors.
3. Timestamps are reused legitimately when multiple event definitions share a start time. Uniqueness must use a composite event key, not timestamp alone.
4. The July 2022 communication-time change creates a protocol boundary. It requires a sensitivity indicator and cannot be ignored in stability analysis.
5. EA-EMPD speech events are clustered by speaker, day, and policy cycle; treating 3,972 speeches as independent observations would overstate precision.

## Primary outcome proposal

The confirmatory family contains three outcomes:

1. Italy–Germany 10-year yield-spread change, basis points;
2. STOXX50 change, percentage points;
3. EUR/USD change, percentage points, where positive means euro appreciation.

SX7E and DE2Y are secondary outcomes. This compact hierarchy limits multiplicity while spanning sovereign fragmentation, broad risk assets, currency transmission, banking, and the short sovereign curve.

