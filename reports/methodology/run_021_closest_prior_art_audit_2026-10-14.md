# Run 021 closest-prior-art audit

**Audit date:** 2026-10-14
**Candidate:** N06, an admissible information-set reliability envelope for a
monetary-policy conditioning state
**Decision:** candidate methodological synthesis; novelty not established

## Search protocol

The review updated the focused Run 019 audit before full-panel implementation.
It searched primary journal, author, arXiv, NBER, and ECB sources for
combinations of: real-time or vintage data; ragged-edge macroeconomic factors;
dataset or variable selection; factor-loading instability; principal-subspace
error; robust or distributionally robust PCA; model confidence sets; selective
prediction; and monetary-policy information sets. Searches emphasized work
published or revised through 14 October 2026. Secondary summaries were used
only to locate a primary paper and were not treated as evidence.

Inclusion required a direct bearing on at least one discriminating component:
source-vintage uncertainty, panel composition, missing-data factor estimation,
factor-space instability, ambiguity-set estimation, set-valued model
comparison, or prospective authorization. A paper was not classified as
closest merely because it used PCA, a real-time dataset, or abstention.

## Evidence matrix

| Primary source | Established contribution | Consequence for N06 |
|---|---|---|
| Orphanides (2001), *American Economic Review*, doi:10.1257/aer.91.4.964 | Demonstrates that real-time information can materially change historical monetary-policy analysis. | Eliminates any novelty claim for using decision-time rather than revised data. |
| Giannone, Henry, Lalik and Modugno (2010), [ECB Working Paper 1145](https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp1145.pdf) | Constructs the area-wide real-time database and documents policy-concept vintages. | Makes the RTD source and vintage mechanics established infrastructure, not a contribution. |
| Bańbura and Modugno (2014), doi:10.1002/jae.2306 | Estimates dynamic factor models under arbitrary missingness and ragged edges. | The proposed EM factor engine and missing-data handling are established components. |
| Altavilla and Ciccarelli (2007), [ECB Working Paper 846](https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp846.pdf) | Combines model and vintage information for forecast stability and uncertainty. | Requires a vintage/panel-combination benchmark; an envelope cannot be presented as the first treatment of multiple vintages. |
| Boivin and Ng (2006), doi:10.1016/j.jeconom.2005.01.027 | Shows that more macroeconomic series need not improve factor estimates and that dataset composition is consequential. | Directly motivates redundancy and channel-balance controls while defeating a “more data is automatically better” claim. |
| Rünstler (2016), [ECB Working Paper 1893](https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp1893.en.pdf) | Studies data-set design and variable selection for unbalanced euro-area dynamic-factor nowcasts. | Requires an explicit data-selection benchmark and confirms that ten series alone are not a defensible high-dimensional contribution. |
| Breitung and Eickmeier (2011), doi:10.1016/j.jeconom.2010.11.008 | Shows that factor-loading breaks can inflate the estimated factor dimension and develops break tests. | Rank changes and projector drift may reflect structural instability; the envelope cannot be called a new break test. |
| Bates, Plagborg-Møller, Stock and Watson (2013), doi:10.1016/j.jeconom.2013.04.014 | Characterizes principal-component factor consistency under loading instability. | Requires separation of tolerable estimation error from economically material information-set instability. |
| Hansen, Lunde and Nason (2011), doi:10.3982/ECTA5771 | Constructs confidence sets over competing models under a loss comparison. | Provides a set-valued benchmark, but its statistical object is a confidence set for best models, not a source-mechanical ambiguity set or a state-authorization certificate. |
| Xu, Wood and Yang (2026), doi:10.48550/arXiv.2606.10463 | Develops distributionally robust PCA over a calibrated Wasserstein ambiguity set with projector-level theory. | This is the closest robust-subspace comparator. N06 must benchmark against it and cannot borrow its guarantees because the proposed ambiguity set is finite and source-mechanical. |
| Bernstein, Goldberg, Gunther, Kercheval, Lan, Lin and Yao (2026), [arXiv:2609.20550](https://arxiv.org/abs/2609.20550) | Decomposes principal-component error into out-of-subspace and in-subspace components in a high-dimensional factor setting. | Requires explicit estimation-error sensitivity and reinforces that a ten-series panel is a wider multichannel panel, not evidence of high-dimensional asymptotics. |
| Angelopoulos, Bates, Candès, Jordan and Lei (2022), doi:10.48550/arXiv.2110.01052 | Formalizes calibrated risk control with explicit multiplicity handling under stated assumptions. | N06's chronological loss calibration cannot claim finite-sample risk control without implementing and satisfying a suitable formal procedure. |
| Inácio, Cerqueira, Barandas and Soares (2026), doi:10.48550/arXiv.2606.23448 | Applies selective prediction and risk–coverage evaluation to time-series forecasting. | Requires transparent risk–coverage and participation comparisons; abstention itself is not novel. |

## Discriminating assessment

No reviewed paper was found that constructs a finite ambiguity set directly
from official source histories, release calendars, revision exposure,
ragged-edge rules, and economically balanced channel deletions; compares the
resulting latent spaces in both common calendar and common economic-channel
coordinates; and uses that envelope prospectively to authorize a
monetary-policy conditioning state while transmission outcomes remain sealed.
This absence is a search result, not proof of novelty.

The individual ingredients are well established. The potentially defensible
increment is therefore the complete governed sequence and its empirical
discrimination against single-panel, panel-combination, and robust-PCA
benchmarks. The contribution would weaken materially if the scenario set were
chosen after observing state paths, if release-lag approximations were treated
as true vintages, if participation were negligible, or if the envelope did not
improve future internal measurement stability.

## Required novelty tests

1. Compare the envelope with the frozen single augmented panel, an equal-weight
   aligned panel/vintage combination, and a robust-PCA sensitivity.
2. Report useful participation and future internal failure at cutoffs selected
   without evaluation outcomes.
3. Separate source-mechanical disagreement from factor-estimation error and
   fixed-rank sensitivity.
4. Demonstrate invariance to factor rotation, scenario ordering, and exact
   duplicates.
5. Complete independent methodological review and second-platform empirical
   reproduction before upgrading N06.

## Claim disposition

N06 remains `CANDIDATE_METHODOLOGICAL_SYNTHESIS_NOT_CLAIMED`. Run 021 improves
the falsifiability and comparator design but supplies no empirical state,
performance result, causal finding, or novelty proof.
