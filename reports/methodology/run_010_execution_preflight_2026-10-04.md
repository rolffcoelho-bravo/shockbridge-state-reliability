# Run 010 source retrieval and execution preflight

**Audit date:** 2026-10-04  
**Status:** pass; ready for one approved outcome-blind empirical Run 010  
**Empirical Run 010 executed:** no  
**Transmission outcomes accessed:** no  
**Synthetic observations used:** no

## Source retrieval

The approved retrieval command completed as one atomic bundle. Every series was
retrieved from the exact frozen official ECB Data Portal HTTPS URL on its first
attempt; the resolved URL remained HTTPS and identical to the requested URL.
No fallback, direct headline-series substitution, insecure TLS, partial bundle,
or synthetic observation was used.

| Frozen RTD concept | Local raw artifact | Rows of observations | Coverage | SHA-256 |
|---|---|---:|---|---|
| HICP index, `RTD.M.S0.N.P_C_OV.X` | `data/raw/ecb_state/run010_latest_hicp.csv` | 310, 2000-01–2025-10 | 100% of 262 required selected-period/lag levels | `d04f0211cc9ab2a0d0dea254c3d814b17e74366b484c59fb62085f27cf7ce154` |
| Industrial-production index, `RTD.M.S0.Y.I_XCONS.X` | `data/raw/ecb_state/run010_latest_ip.csv` | 308, 2000-01–2025-08 | 100% of 269 required selected-period/lag levels | `48825eaff5ec41c8653f53a97803e4c705f11bc34daff3a54633b8ed84914064` |
| Unemployment rate, `RTD.M.S0.S.L_UNETO.F` | `data/raw/ecb_state/run010_latest_unemployment.csv` | 310, 2000-01–2025-10 | 100% of 218 required selected periods | `db2bac035fdb4c3497a7ced0e08f53626a88d99b925c28834328b6431c580dc0` |

The source manifest is
`data/manifests/run010_latest_sources_v1.yaml`, SHA-256
`6a6b0a8f37637d2680940d827a6bdf88cdadb43e68fb4ec849eb03db647ccf80`.
It records exact request and resolved URLs, response hashes and byte sizes,
UTC retrieval timestamps, and every attempt. The raw response bodies remain
local and Git-ignored under the project's existing fetch-only release policy.

The industrial-production response ends in August 2025, as expected from the
registered RTD concept. This does not create a coverage failure: the frozen
point-in-time panel's September and October 2025 origins selected only periods
already available by their decision-time cutoffs. Run 010 preserves those
selected periods and does not replace them with later periods.

## Exact coverage and panel gates

The read-only preflight joined the 1,144 frozen month-feature rows to the three
latest-vintage series without calculating factor geometry or a classification.
It found:

- 285 observed HICP rows and 240 unique selected periods;
- 274 observed industrial-production rows and 233 unique selected periods;
- 270 observed unemployment rows and 218 unique selected periods;
- no missing required selected-period level;
- no missing required 12-month lag for HICP or industrial production;
- no duplicate or non-finite current observation;
- exact approved frequency, reference area, adjustment, concept, denomination,
  and series key for every response; and
- 100% required-level-and-lag coverage for all three macro features.

Originally missing rows will remain missing even when the latest vintage has a
value. Deposit-facility rows will be copied from the frozen panel and will not be
downloaded or revised.

## Frozen empirical configuration

The empirical configuration is
`experiments/state_vintage_robustness_run010_v1.yaml`, SHA-256
`d749faaa408e7d3602dbf3b0c093ff899fc7c244e04179dbf21cc61698e3e07f`.
It binds:

- approved Run 010 design SHA-256
  `f85116d407019b9386101242e94381fa2973a1e39addfb24e4255653444db457`;
- point-in-time panel SHA-256
  `80d5e5f4b04fb7551bc69d4c4b429271258efad09987d9971551fd4a477f527e`;
- frozen Run 009 diagnostic SHA-256
  `c177cfac7fe553d48ada0509d95d665c9c424aa93d339fa3a96ae69bb6553af4`;
  and
- source-manifest SHA-256
  `6a6b0a8f37637d2680940d827a6bdf88cdadb43e68fb4ec849eb03db647ccf80`.

The loader accepts the configuration only as the real, outcome-blind experiment
with the exact 1999-replication seed/block contract, unchanged Run 009 windows
and thresholds, frozen sample dates, no synthetic observations, and no
transmission authorization.

## Execution decision

All source, schema, provenance, coverage, configuration, software, and storage
gates pass. The next permissible action is the single approved Run 010 empirical
computation from a clean local Git checkpoint. The output must remain an ex-post
matched-period latest-vintage sensitivity and cannot reopen state selection or
transmission.
