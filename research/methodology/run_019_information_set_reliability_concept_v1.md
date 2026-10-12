# Run 019 information-set reliability concept

**Status:** candidate methodological design; not implemented, estimated, or
claimed as novel
**Evidence boundary:** official-source metadata and focused prior-art audit
only; no candidate observations or transmission outcomes were accessed

## Research problem

Real-time monetary-policy measurement is usually represented by one completed
panel. That representation hides several economically consequential choices:
which source was available, which vintage was visible, what publication lag
was defensible, how a ragged edge was filtered, and which near-duplicate series
were admitted. The earlier four-feature study shows that one such panel can
have favorable predictive density while its economic geometry fails a
prospective reliability gate. Simply adding variables would not resolve that
problem and could worsen it through correlated idiosyncratic noise or channel
imbalance [L037].

Run 019 therefore proposes a different object for a later study: reliability
over a *prespecified set of admissible decision-time information panels*. The
set is created from documented source and timing uncertainty before any state
or transmission result is inspected. It is not a multiverse of convenient
researcher choices.

## Candidate object: the admissible information-set reliability envelope

Let \(\mathcal A_t=\{X_t^{(a)}:a\in A_t\}\) be the frozen set of panels that
could defensibly represent information available at decision time \(t\). Each
index \(a\) fixes a source mapping, vintage or release-lag rule, ragged-edge
treatment, and channel-balanced series manifest. Let

\[
P_{t,k}^{(a)}=V_{t,k}^{(a)}V_{t,k}^{(a)\prime}
\]

be the rotation-invariant projector onto the estimated \(k\)-dimensional state
subspace, and let \(s_t^{(a)}\) denote an economically oriented state summary.
The envelope reports at least four quantities:

1. **subspace diameter**
   \(D_t=\max_{a,b\in A_t}\|P_{t,k}^{(a)}-P_{t,k}^{(b)}\|_2\);
2. **economic-orientation floor**, the minimum channel-anchor alignment across
   admissible panels;
3. **state interval or set**, the range of aligned \(s_t^{(a)}\) values rather
   than one falsely precise score; and
4. **support floor**, the minimum effective event support over admissible
   panels and prespecified policy-shock doses.

A state may be authorized only when every admissible panel passes its internal
measurement gates and the cross-panel envelope is sufficiently narrow. A wide
envelope produces abstention. Thresholds, multiplicity treatment, and any
calibration loss must be frozen and evaluated chronologically in a later
protocol; Run 019 neither chooses them nor claims a guarantee.

## Why this could add monetary-policy research value

Real-time information matters for policy-rule interpretation [L033], and euro-
area output-gap signs and magnitudes can be unreliable in genuine vintages
[L034]. Ragged-edge dynamic factor estimation [L035] and vintage/model
combination [L036] address important parts of the problem, but a policy analyst
also needs to know whether a state conclusion is robust to the *admissible
information set itself*. The proposed envelope would convert that source,
release, and missingness uncertainty into an auditable authorization object.

The policy-facing output would not be “the economy was in state 2.” It would
be one of the following:

- the state is stable across admissible decision-time panels and can proceed
  to outcome-blind support checks;
- the sign is stable but the magnitude is set-valued and must be propagated;
- the economically relevant subspace is source-sensitive, so state-dependent
  transmission is not authorized; or
- historical reconstruction is impossible and the claim must wait for
  prospective snapshots.

This is potentially more useful than forcing a positive state result because
it tells researchers and policy institutions when heterogeneous transmission
claims are measurement-supported and when they are artifacts of information-
set completion.

## Relationship to established work

The components are not new. Real-time monetary-policy analysis, vintage
databases, dynamic factors with arbitrary missingness, factor instability,
subspace perturbation, robust control, model sets, and abstention all have
established literatures [L014–L032, L033–L039]. Distributionally robust PCA
also directly studies worst-case reconstruction over ambiguity sets [L040].

The candidate increment is narrower: define the ambiguity set from auditable
official decision-time source mechanics, evaluate rotation-invariant economic
state geometry across that set, and use the resulting envelope as a firewall
before monetary-policy transmission outcomes are opened. The focused search
did not identify an exact prior implementation of that complete combination,
but absence from this bounded search is not proof of priority. The manuscript
must say “candidate methodological synthesis” until a systematic review and an
executed empirical comparison establish distinct value.

## Falsifiable comparisons for a later run

A future protocol should compare the envelope with:

1. the current four-feature point-in-time gate;
2. one frozen high-dimensional panel treated as if it were uniquely correct;
3. archived-vintage-only panels;
4. release-lag panels with conservative lag perturbations;
5. channel-balanced versus unbalanced series counts; and
6. simple model or vintage averaging.

The method adds value only if it detects consequential information-set
fragility or supplies stable authorization while preserving chronological
coverage. If the envelope merely reproduces a single-panel decision, creates
near-universal abstention, or changes only under implausible scenarios, the
increment is weak and must be reported as such.

## Non-negotiable integrity constraints

- Use real, freely retrievable observations only; no synthetic observation may
  enter an empirical estimate.
- Freeze the source registry, series manifest, transformations, cutoff rules,
  admissible scenarios, thresholds, and comparison metrics before execution.
- Keep all transmission outcomes sealed through measurement authorization.
- Do not select sources, lags, factors, or ambiguity sets for a positive state
  or heterogeneous response.
- Treat current historical values without archived vintages as release-lag
  sensitivities, not genuine point-in-time observations.
- Preserve the original negative result; the high-dimensional study is an
  independently governed extension, not a retrospective rescue.

## Run 019 decision

The concept is methodologically coherent and its official-data foundation is
feasible, but neither novelty nor empirical value is established. The highest-
value next step is a small, frozen, series-level source-history pilot followed
by an owner-approved information-set reliability protocol. Observation-level
retrieval, estimator implementation, and state evaluation remain prohibited
until that approval.
