# Claim-to-evidence matrix

For every manuscript revision, each substantive statement must be classified:

| Class | Meaning | Minimum support |
|---|---|---|
| FACT | Direct property of a source artifact | source URL, hash, extraction code |
| ESTIMATE | Sample-dependent numerical result | contract, code commit, experiment ID, uncertainty |
| CAUSAL | Potential-outcome or structural interpretation | identification assumptions, falsifications, overlap, inference |
| PREDICTIVE | Prospective out-of-sample performance | chronological protocol, benchmark, untouched block |
| MECHANISM | Economic explanation for a result | competing mechanisms and discriminating tests |
| LIMITATION | Threat or boundary | documented impact and sensitivity where possible |

Claims that do not meet their minimum support remain in the discussion as hypotheses, not findings.

## Current claim boundary after Run 013

- **FACT:** the registered state panel contains 242 events, four admitted features, and no detected timing violations.
- **ESTIMATE:** the event-indexed HMM's prequential score, filtered probabilities, state descriptions, entropy, and support statistics are sample-dependent estimates from an outcome-blind benchmark.
- **LIMITATION:** restart instability at two 2008 events and absence of state 1 in the middle chronological block prevent primary-model selection.
- **ESTIMATE:** Run 009's frozen full-panel geometry classification fails for all three rolling-window lengths, with persistent dated episodes and low prespecified weak-eigengap coincidence.
- **ESTIMATE:** Run 010's matched-period latest official vintage retains all three full-panel failures and every deletion-window classification; the full-panel breach-month overlap is 0.904–0.981.
- **LIMITATION:** Run 010 is ex post and cannot separate numerical revisions from rebasing, benchmarking, seasonal adjustment, or euro-area-composition changes within the RTD concepts.
- **LIMITATION:** feature-deletion and policy-regime differences are descriptive, calendar-dependent, and cannot identify a causal source of instability or an eligible replacement state.
- **FACT:** a clean temporary checkout of source commit `02fdfd1` reproduced all four registered Run 010 outputs at exact SHA-256 equality; canonical artifacts were unchanged and the temporary checkout was removed.
- **LIMITATION:** exact reproduction has been established in one isolated macOS/Python 3.9 environment, not yet across operating systems or a fully pinned long-term release image.
- **FACT:** an exact-version-locked clean archive independently repeats the Run 010 byte-hash reproduction while passing the full quality suite and 90% coverage on the same audited macOS/Python 3.9 platform.
- **LIMITATION:** dependency versions are exact but package distributions are not hash-pinned; no second operating system, container runtime, or Python minor version has reproduced the empirical bundle.
- **LIMITATION:** the public source-only CI intentionally skips seven tests that require local hash-registered evidence and enforces an 87% rather than 90% coverage floor; it is a release-code gate, not the complete scientific reproduction.
- **FACT:** the public repository began from the audited parentless Run 013 root with explicit Apache-2.0/CC BY 4.0 boundaries, no tracked protected data or flagship blueprint, and zero registered known-secret, privacy-path, or supplementary entropy findings. Its identity-only amendment preserved the accepted tree, message, and dates. The independent public and private `main` refs were verified after authenticated non-force pushes.
- **FACT:** the append-only publication correction preserves the failed first hosted run and passes the replacement GitHub Actions matrix on Python 3.9 and 3.12 under the exact seven-skip and 87%-coverage public contract. GitHub secret scanning is enabled and reports no detected secret.
- **LIMITATION:** hosted CI is a source-only release gate rather than a complete empirical reproduction. The local scanner is not exhaustive, and no second-platform full-evidence reproduction has occurred.
- **LIMITATION:** the closest literature establishes the project's component methods. Any incremental contribution is the prospectively governed validation sequence and application-specific negative evidence, not a novel factor estimator, stability statistic, break test, vintage comparison, or model-confidence-set procedure.
- **PROHIBITED CURRENT CLAIM:** no result yet establishes state-dependent ECB transmission, amplification, prospective forecast reliability, or an economic mechanism.

Candidate contribution language is controlled by `novelty_ledger.md`; executed numerical findings are indexed in `results_register.md`.
