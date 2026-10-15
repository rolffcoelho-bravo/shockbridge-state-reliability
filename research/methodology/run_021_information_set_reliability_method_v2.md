# Information-set reliability: frozen full-panel implementation contract

**Version:** 2
**Date:** 2026-10-14
**Status:** frozen before implementation, full-history retrieval, or estimation
**Evidence boundary:** protocol design only; real official empirical data will
be used in a later approved run; no synthetic empirical observations and no
transmission outcomes

## 1. Object of inference

At monthly origin (t), let \(\mathcal A_t\) be the finite set of
nondegenerate panels produced by the registered source-mechanical generator.
Its axes are the core versus augmented manifest, registered versus one-month-
slower class-B timing, ragged-edge versus complete-case treatment, and full
versus leave-one-available-channel-out composition. Scenarios are deduplicated
by their exact eligibility mask and standardized observed-matrix hash before
estimation. Neither a factor path nor a later outcome can create, remove, or
weight a scenario.

The target is a measurement authorization decision. It asks whether the latent
space and its economic orientation are sufficiently similar across
\(\mathcal A_t\) to permit a later transmission study. It is not a probability
that a state is true, a causal estimand, or a model confidence set.

## 2. Decision-time construction

An observation is usable only when its registered first-usable timestamp is
strictly earlier than the first-day 23:59:59 Europe/Berlin origin. RTD, policy-
rate, and yield-curve histories use recorded `VALID_FROM` timestamps. The
daily dollar/euro reference rate uses the official same-day publication clock
with a one-hour buffer. MIR and BSI observations require an archived,
reference-period-specific official release timestamp. Their current-history
values remain explicitly revision exposed; a release timestamp does not turn
a revised value into a true vintage. If calendar evidence is absent, the value
is missing.

HICP and industrial production are transformed as within-vintage twelve-month
log differences. Unemployment, the policy rate, and the two-year rate enter in
levels. The curve variable is the ten-year minus two-year rate using values
available under the same origin. The exchange rate is an end-of-month log
change. Bank borrowing costs enter in levels; loans and M3 use their published
annual growth rates. The January 2003 panel therefore requires raw macro data
from January 2002. Backward fill, later-release backfill, interpolation, and
synthetic imputation are prohibited.

## 3. Deterministic ragged-edge factor estimator

For scenario (a), the observed training matrix is standardized with expanding
observed means and sample standard deviations. Series require 80 percent
training coverage, at least 24 observed values, and finite positive scale.
Origins require at least five economic channels.

Channel balance is applied before the singular-value step. If channel (c)
retains \(n_c\) series, registered series \(j\) receives signed weight

\[
w_j=s_j/\sqrt{n_c}, \qquad s_j\in\{-1,1\}.
\]

Thus each represented channel has unit squared weight before estimation.
Missing values are initialized at the observed training mean. For candidate
ranks one through three, deterministic SVD alternates with replacement of only
the missing entries by the low-rank reconstruction. Observed entries never
change. Iteration stops at relative observed-loss change below \(10^{-8}\) or
1,000 iterations; failure to converge makes the scenario nondegenerate false.

Rank minimizes the observed-entry adaptation

\[
ICp2(k)=\log V_k+k\frac{N+T}{NT}\log\!\left(\frac{NT}{N+T}\right),
\]

where \(V_k\) is channel-weighted observed-entry residual sum of squares divided
by observed weight. The rank is also bounded by the observed training rank and
\(N-1\); ties choose the lower rank. This is an explicit ragged-edge adaptation,
not an assertion that textbook balanced-panel Bai--Ng theory applies. Fixed
rank-one and rank-two sensitivities are mandatory.

## 4. Comparable geometry

Over the same 120 calendar rows, centered scores \(F_a\) define

\[
H_a=F_a(F_a'F_a)^\dagger F_a'.
\]

The primary score-space distance is the spectral norm
\(\lVert H_a-H_b\rVert_2\). The secondary distance is

\[
\frac{\lVert H_a-H_b\rVert_F}{\sqrt{k_a+k_b}},
\]

which remains defined when selected ranks differ.

The frozen eight-row map has entry \(s_j/\sqrt{n_c}\) for series (j) in
channel (c) and zero otherwise. With loadings \(L_a\), define \(G_a=B_aL_a\)
and

\[
Q_a=G_a(G_a'G_a)^\dagger G_a'.
\]

The channel-space distance is \(\lVert Q_a-Q_b\rVert_2\). Empty channels remain
zero rows. Factors and scores are aligned using training-only sign alignment or
orthogonal Procrustes. The envelope reports worst pairwise distances, minimum
absolute anchor cosine, and minimum, quartiles, median, and maximum aligned
scores.

## 5. Independent future failure and validation clock

The future-failure label must not be defined by the candidate envelope
thresholds it is intended to evaluate. The reference is the registered
augmented, baseline-timing, ragged-edge panel. At each origin it compares
expanding and 120-month rolling estimates. A one-month reference breach occurs
when score- or channel-projector spectral distance exceeds 0.35, absolute
anchor cosine is below 0.20, fewer than five channels remain, or estimation is
nondegenerate false. The future label equals one if any such breach occurs in
months \(t+1\) through \(t+12\).

Calibration spans January 2013 through December 2017. The 2018 embargo prevents
labels crossing the split. One-time evaluation spans January 2019 through
October 2024; the diagnostic tail through October 2025 matures every twelve-
month label. The prior draft's October 2025 evaluation endpoint was impossible
with an October 2025 diagnostic tail and is superseded before execution.

Thresholds minimize calibration loss with false authorization cost one and
abstention cost 0.25. Comparators are always abstain, the single augmented
panel, equal-weight aligned panel combination, and a robust-PCA sensitivity.
Benchmark cutoffs and participation matching use calibration data only. No
evaluation result may retune a threshold or participation target.

## 6. Success, uncertainty, and stopping

Primary success requires at least 10 percent evaluation participation, at
least two nondegenerate scenarios at authorized origins, lower decision loss
than the single augmented panel, no higher future-failure rate at calibration-
matched participation, and no failed invariance or negative control. Paired
noncircular moving-block intervals use 1,999 draws, twelve-month primary blocks,
and 6-, 18-, and 24-month sensitivities. They condition on selected thresholds
and observed paths and confer no finite-sample guarantee.

Any missing input hash, changed key/unit/frequency/host, unverified MIR or BSI
release month, changed pilot timing class, insufficient scenario support, or
failed success component triggers abstention or a registered non-improvement.
Transmission outcomes remain sealed until a separate authorization decision.

## 7. Contribution boundary

Real-time vintage analysis, ragged-edge factor estimation, dataset selection,
factor-instability diagnostics, projector geometry, robust PCA, model sets,
and selective prediction all have established precedents. The candidate
increment is their outcome-blind integration around an ambiguity set generated
by auditable official information mechanics. That synthesis remains unclaimed
until real-data execution beats the registered comparators at useful coverage,
survives estimation-error sensitivities, and receives independent review.
