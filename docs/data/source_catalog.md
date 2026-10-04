# Source and rights catalog

Retrieval permission and redistribution permission are separate decisions. `PENDING` means the artifact may be inspected locally but must not be committed or republished.

| ID | Source | Role | Vintage/update | Retrieval | Redistribution | Audit note |
|---|---|---|---|---|---|---|
| EA_MPD_METHOD | [ECB working paper 2281](https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp2281~3303fd281b.en.pdf) and [appendix](https://www.ecb.europa.eu/pub/pdf/annex/Appendix_Measuring_Euro_Area_Monetary_Policy.pdf) | event-window method and database description | 2019 publication | allowed | cite source | Identification reference; not itself a data artifact. |
| EA_MPD_OFFICIAL | [Official ECB workbook](https://www.ecb.europa.eu/pub/pdf/annex/Dataset_EA-MPD.xlsx) | scheduled Governing Council events and outcomes | workbook updated 2025-11-04 | audited | FETCH_ONLY | 315 unique dates, 46 columns, three windows; source hash in manifest. |
| EA_EMPD_OFFICIAL | [Official ECB extended workbook](https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp3157-annex-EA-EMPD~8b94679d77.en.xlsx) | separate speech/event extension | annex published 2026-06-10 | audited | FETCH_ONLY | 4,926 rows through 2026-03-28; 318 events for each GC window plus 3,972 speech events. |
| ABGMR_FACTORS_PR | [Author factor vintages](https://gragusa.org/factors/) | provisional target shock | inspected 2025-10-30 | observed | PENDING | 242 unique rows, no missing target values, SHA-256 recorded in contract. Page documents a 2014 stale-quote revision. |
| ABGMR_FACTORS_PC | [Author factor vintages](https://gragusa.org/factors/) | timing/FG/QE sensitivity | inspected 2025-10-30 | observed | PENDING | 237 unique rows; QE missing on 138 rows. Not eligible as the first primary shock. |
| EA_MPD_ARCHIVE | [SAFE metadata record](https://fif.safe-frankfurt.de/xmlui/handle/123456789/1642?locale-attribute=en) | possible archived research-data artifact | record inspected 2026-10-01 | observed | VERIFY_FILE_LEVEL | Record displays CC BY-SA 4.0, but the exact attached file and version were not captured in this workspace. |
| ECB_RTD | [ECB Real-Time Database](https://data.ecb.europa.eu/data/datasets/RTD/data-information) | point-in-time macro states | portal update 2026-04-29 | API documented | VERIFY_SERIES_LEVEL | Experimental vintages; post-2015 data are available through ECB web services. Coverage is series-specific. |
| ECB_RTD_LATEST_RUN010_PROPOSED | ECB Data Portal API production versions for `RTD.M.S0.N.P_C_OV.X`, `RTD.M.S0.Y.I_XCONS.X`, and `RTD.M.S0.S.L_UNETO.F` | matched-period ex-post latest-vintage sensitivity | retrieval not yet authorized | free official API access; no-data metadata audited 2026-10-03 | FETCH_ONLY | Same RTD concept keys as the real-time panel. Preserve the original observation-period and missingness mask. Latest values may embed benchmark, seasonal-adjustment, rebasing, and euro-area-composition changes; do not call this a pure revision effect. |

## Audit decision

Do not commit raw event data. The implemented adapter downloads to an ignored directory, records content hashes, audits schemas and fails on unexpected structure or duplicate event keys. The public release policy is fetch-only. Derived tables and figures must cite the ECB and state every transformation. The ECB website permits reuse of directly obtained information subject to attribution and accurate reproduction; the stricter fetch-only rule avoids republishing an authored research workbook while preserving full reproducibility.
