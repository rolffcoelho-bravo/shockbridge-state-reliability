# Run 004 — outcome-blind event-indexed state replay

**Date:** 2026-10-02

**Milestone:** 2, baseline state engine

**Status:** benchmark completed and rejected as primary

## Completed

- implemented an auditable diagonal-Gaussian HMM with missing-dimension likelihoods, filtered probabilities, expanding refits, label alignment, and deterministic restarts;
- fixed a false first-iteration convergence condition and aligned convergence with the regularized EM objective;
- froze and executed a real-data, outcome-blind configuration before inspecting results;
- compared prequential density performance with a state-independent Gaussian;
- audited state counts, weighted ESS, entropy, chronological support, shock sign/dose support, restart stability, and leverage;
- corrected a screening bug that compared the restart threshold with mean rather than minimum agreement;
- stored code, tests, hashes, audit, manifest, and the ignored derived probability artifact under the canonical project root.

## Decision

Retain `state-replay-v1` as a negative benchmark. It fails minimum restart agreement at two September–October 2008 events. State 1 also disappears from the middle chronological block, so this specification cannot yet demonstrate recurrent state support.

## Outcome firewall

No response magnitude was opened. Shock values were used only after estimation for support diagnostics. State selection and interpretation remain outcome blind.

## Approved expansion

Build a regular-month point-in-time state calendar, add temporal-support gates prospectively, and compare the four Blueprint V2 benchmark families before selecting a primary state estimator. The failed v1 run must remain visible and must not be overwritten.
