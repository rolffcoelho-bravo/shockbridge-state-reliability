# Run 008 point-in-time source-extension audit

**Audit date:** 2026-10-03
**Outcome access:** none
**Data class:** official ECB source-availability audit

## Question

Can the existing four-feature point-in-time panel be extended from October 2025 through October 2026 to create a genuinely new, complete temporal validation block without changing features or relaxing the frozen staleness rules?

## Official-source findings

The ECB Data Portal documents `includeHistory=true` as the supported API mechanism for retrieving current and previous data versions. The ECB describes the RTD as an experimental research database updated semi-annually and states that vintages from 2015 onward are available through its web services.

Live official API queries and the already registered local artifacts show:

| Feature | Latest observation in registered history | Latest `VALID_FROM` | Extension assessment |
|---|---|---|---|
| HICP index | 2026-08 | 2026-09-09 15:30 CEST | available for an October 2026 cutoff |
| Unemployment | 2026-07 | 2026-09-09 15:30 CEST | available for an October 2026 cutoff |
| Industrial production | 2025-08 | 2025-10-29 15:30 CET | becomes stale under the frozen 120-day rule |
| Deposit facility rate | 2026-10-02 | daily observation | available |

The current API response for the admitted industrial-production key is byte-identical to the registered artifact (`5e2fb7b...`) and still ends in August 2025. Both seasonally adjusted and working-day-only variants of the same RTD concept end at that month. A revised-data STBS series exists later, but substituting it would abandon the registered real-time-vintage contract and change the feature definition.

The first broad API request produced transient HTTP 504 responses; a separately retried, certificate-verified query succeeded. This service behavior affected retrieval latency only. It did not change the returned artifact or lead to data substitution.

## Decision

Do not represent November 2025–October 2026 as a complete new four-feature validation block. Preserve the 120-day industrial-production staleness cap and the existing feature definition. The later months could be used only in a separately approved missing-feature robustness exercise, not as the clean external validation proposed after Run 007.

## Research consequence

Run 008 can still be prospectively specified and outcome-blind, but it is a post-Run 007 redesign evaluated on an already used state-data period. It is not an independent external replication. A truly new validation block requires either future releases of the same RTD series or a prospectively justified vintage-equivalent replacement with an overlap and break audit.

## Sources and local evidence

- ECB Data Portal API documentation: `https://data.ecb.europa.eu/help/api/data`
- ECB RTD information and release policy: `https://data.ecb.europa.eu/data/datasets/RTD/data-information`
- Registered source artifacts and hashes: `research/state_sources_v1.yaml`
- Local source paths: `data/raw/ecb_state/rtd_hicp_history.csv`, `rtd_unemployment_history.csv`, `rtd_ip_history.csv`, and `dfr.csv`
