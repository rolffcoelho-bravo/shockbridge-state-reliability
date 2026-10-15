# Information-set reliability for decision-time monetary-policy states

**Status:** frozen candidate method before full-panel retrieval or estimation  
**Date:** 2026-10-12  
**Empirical boundary:** real, freely retrievable official observations only;
no synthetic empirical observations; no transmission outcomes

## 1. Problem

A latent monetary-policy state can be stable conditional on one completed
dataset and still be unreliable across other defensible representations of the
information available at the same decision date. Official sources differ in
vintage coverage, publication lag, revision history, missingness, and channel
composition. The relevant object is therefore not a single hindsight-complete
matrix. It is a prospectively defined set of admissible decision-time panels.

Let \(\mathcal A_t\) be the set of panels allowed at origin \(t\). Its members
may differ only along frozen, source-mechanical axes: registered source family,
verifiable vintage or release-lag rule, ragged-edge treatment, and eligible
channel deletion. Scenarios cannot be added or removed after observing a state
path or a transmission outcome.

The method asks whether the economically relevant latent space is sufficiently
similar across \(a\in\mathcal A_t\) to authorize a conditioning state. It does
not require that all input matrices contain the same variables.

## 2. Correction to the earlier projector definition

For panel \(a\), let \(X_a\) have \(T\) common calendar rows and \(N_a\)
series, and let \(L_a\) be an \(N_a\times k_a\) loading matrix. The feature-
space projector \(L_a(L_a'L_a)^{-1}L_a'\) is \(N_a\times N_a\). It cannot be
subtracted from the corresponding projector for panel \(b\) when
\(N_a\ne N_b\), and even equal dimensions would not make the coordinates
comparable if the variables differ. An unqualified cross-panel loading-
projector diameter is therefore undefined.

Run 020 replaces that invalid comparison with two rotation-invariant objects
whose coordinates are shared by construction.

### 2.1 Common-calendar score projector

Let \(F_a\) be the centered \(T\times k_a\) factor-score matrix over exactly
the same 120 monthly dates. Define

\[
H_a=F_a(F_a'F_a)^{\dagger}F_a',
\]

where \(\dagger\) is the Moore--Penrose inverse. Every \(H_a\) is a
\(T\times T\) orthogonal projector in common calendar space, irrespective of
the number or identity of the input series. The primary pairwise distance is

\[
d_{2,H}(a,b)=\lVert H_a-H_b\rVert_2.
\]

The secondary rank-aware distance is

\[
d_{F,H}(a,b)=
\frac{\lVert H_a-H_b\rVert_F}{\sqrt{k_a+k_b}}.
\]

When \(k_a=k_b=k\), the denominator is \(\sqrt{2k}\), matching the original
equal-rank definition. The rank-aware form prevents an undefined normalization
when the frozen factor-count rule selects different ranks.

### 2.2 Common economic-channel loading projector

Fix eight channels before retrieval: prices and expectations; real activity
and labour; policy stance and money markets; sovereign curve and term
structure; bank funding and lending rates; credit and money quantities;
financial conditions and systemic stress; and external value and cross-border
conditions.

For each panel, a frozen \(8\times N_a\) mapping \(B_a\) aggregates sign-
oriented, channel-balanced loadings. Within an available channel, weights sum
to one in absolute value and are scaled by the inverse square root of the
number of retained series; unavailable channels remain explicit zero rows.
Define \(G_a=B_aL_a\), normalize its nonzero columns, and form

\[
Q_a=G_a(G_a'G_a)^{\dagger}G_a'.
\]

Every \(Q_a\) is an \(8\times8\) projector in the same economically labelled
space. The primary distance is \(d_{2,Q}(a,b)=\lVert Q_a-Q_b\rVert_2\).
The mapping does not make two panels economically identical; it makes their
loading geometry mathematically comparable and exposes missing channels.

## 3. Admissible information sets

The initial registered family contains two distinct candidates. P0 uses seven
series spanning five channels. P1 adds three bank-credit and monetary series,
yielding ten series across seven channels. CISS is a timing-classification
control and cannot enter either historical panel because its inspected history
does not establish decision-time replay.

Each retained series must pass exact key, unit, frequency, official-host,
rights-locator, and timing-rule validation. Timing class A uses documented
archived/API history. Timing class B uses a frozen conservative release rule,
with an additional one-month slow-release sensitivity. Timing class C may be
used only after prospective snapshots accumulate. Current data are never
relabeled as historical vintages merely because the provider is official.

The scenario generator crosses the two base panels with registered baseline
and slow class-B timing, observed ragged edges and a complete-case sensitivity,
and leave-one-eligible-channel-out variants. Exact duplicates and scenarios
differing only by duplicate count are removed. No scenario may be selected by
its factor path, authorization rate, or eventual response estimate.

## 4. Estimation contract

At each monthly origin, transformations and expanding standardization use only
available history. Backward filling, later-release backfilling, and synthetic
imputation are prohibited. Series require at least 80 percent training
coverage; an origin requires at least five channels. Exact duplicates collapse,
and correlations above 0.98 within a channel invoke a frozen timing/coverage/
manifest-order tie-break.

The planned estimator is weighted EM principal components with ragged edges.
The factor count is between one and three and is selected by Bai--Ng ICp2 on
the training sample, with lower dimension breaking ties. Channel total weights
are equal so that dense statistical families cannot dominate by series count.
This estimator is not yet implemented or validated.

## 5. Reliability certificate and abstention

For every origin with at least two nondegenerate admissible panels, compute the
maximum pairwise score-projector distance, maximum pairwise channel-projector
distance, minimum frozen-anchor orientation, and the minimum/median/maximum and
interquartile range of aligned state scores. Alignment uses training data only.

An origin is authorized only if every within-panel quality gate and every
cross-panel envelope gate passes. Fewer than two nondegenerate panels implies
abstention. The certificate is a measurement decision, not a causal estimand
or probability that a state is true.

Thresholds are selected on data ending in December 2017, followed by a
12-month embargo. January 2019 through October 2025 is opened once for
evaluation. The loss assigns cost 1 to authorization followed by an internal
geometry breach within 12 months and cost 0.25 to abstention. Ties prefer
higher participation and then smaller distance thresholds. Outcomes of
monetary-policy shocks remain inaccessible throughout selection.

## 6. Validation and falsification

The method must satisfy four invariances before empirical interpretation:

1. requerying identical immutable series produces zero envelope distance;
2. panel order and factor rotation do not change projector distances;
3. adding an exact duplicate does not change channel-balanced results; and
4. all serialized inputs and outputs remain identical under locked
   reproduction.

Evaluation reports participation, information-set fragility, and the matched-
participation difference in future internal breaches relative to a single
augmented panel. A 1,999-draw moving-block bootstrap over evaluation origins
uses 12-month primary blocks and 6, 18, and 24-month sensitivities; simultaneous
intervals use the maximum absolute studentized statistic across the three
primary metrics. The intervals remain conditional on the executed design and
do not create a general finite-sample guarantee.

The study stops if participation is below 10 percent, fewer than two panels are
nondegenerate, the envelope changes only under scenarios lacking timing
evidence, or matched-participation breach risk does not improve. A non-
improvement is retained rather than repaired after inspection.

## 7. Contribution boundary

Principal components, ragged-edge factor estimation, real-time vintage
analysis, projector geometry, robust decision making, and selective
abstention all have established precedents. The candidate contribution is the
application-specific integration of official decision-time source mechanics,
common-space latent geometry, a chronological reliability certificate, and an
outcome firewall for euro-area monetary-policy research. Run 020 corrects the
geometry and establishes source-level feasibility. It does not establish
method novelty, empirical improvement, a high-dimensional state, or state-
dependent transmission.
