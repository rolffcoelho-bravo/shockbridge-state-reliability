# Run 006 — state-model benchmark comparison

**Date:** 2026-10-02

**Milestone:** 2, baseline state engine

**Status:** kill gate activated; redesign required

## Completed

- froze and checkpointed the four required model families before inspecting results;
- evaluated PCA clustering, dynamic factor, HMM, and causal change point on the same point-in-time monthly panel;
- ran two/three-state and expanding/rolling-window sensitivity;
- enforced global counts, weighted ESS, chronological-block support, restart agreement, convergence, and prequential benchmark gates;
- preserved and repaired an invalid first attempt containing two non-finite change-point scores;
- produced 3,616 finite historical predictions in the corrected comparison.

## Finding

No primary two-state expanding candidate passes every frozen gate. Dynamic factor is strongest on predictive score and support, but fails restart stability. HMM is usually initialization-stable but fails middle-block support and its minimum restart agreement. Three-state and rolling variants do not resolve the joint problems.

## Scientific boundary

The state engine remains unfrozen and all transmission outcomes remain sealed. No claim about heterogeneous ECB transmission is authorized.

## Next redesign question

Determine whether the evidence supports a continuous filtered factor more strongly than discrete regimes. For discrete states, evaluate stability only among near-optimal solutions, replace random one-dimensional k-means with exact clustering, and prospectively gate expanding-versus-rolling consistency.
