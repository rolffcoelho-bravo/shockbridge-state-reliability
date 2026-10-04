# Run 013 publication amendment 2 result

**Result date:** 2026-10-04

**Primary status:** `PUBLIC_RELEASE_LIVE_HOSTED_CI_PASSED`

**New empirical estimation:** none

**Transmission outcomes accessed:** no

## Remote publication

The canonical Flagship Project was pushed without force to the private
`shockbridge-state-reliability-research-archive` repository. The sanitized
public checkout was pushed independently to
<https://github.com/rolffcoelho-bravo/shockbridge-state-reliability>.
The first-push remote `main` hashes exactly matched their local heads. The
dedicated Ed25519 authentication key is stored outside the project; Git tracks
neither the private key nor any token.

The public repository retains the audited parentless release root
`8a6469340aed7fd8b2df3a27fcf17ccae08d9df8`. No force push or history rewrite
occurred. The first append-only correction is
`a4d7eb9cfc5a13069fdaa6b38bde8cdc5633ddf0`.

## Hosted failure and correction

GitHub Actions run `37237281845` is preserved as failed release evidence. Its
Python 3.9 job passed, but Python 3.12 collected five errors because direct
execution of the public runner did not ensure that the repository-local
`scripts` package was importable. GitHub also warned that the original exact
action pins targeted deprecated Node.js 20. The rendered repository exposed
stale pre-publication status wording at the same review stage.

The correction explicitly resolves and prepends its repository root before
absolute test discovery, adds a hostile import-path regression test, updates
official action pins to exact Node.js-24-capable commits, refreshes
current-facing publication statements, and updates the tracked public manifest.
It changes no analytical package source, data, method, threshold, result, or
scientific claim boundary.

GitHub Actions run `37237953213` completed successfully in 1 minute 24 seconds.
Both Python 3.9 and Python 3.12 jobs passed. The public contract now discovers
155 tests, skips exactly seven evidence-bound tests, executes 148 tests with no
failure or error, and passes the 87% source-only coverage threshold. Local
strict typing, Ruff, formatting, manifest, privacy, secret, entropy, protected-
data, and release-boundary checks also pass.

## Hosted security

GitHub secret scanning is enabled. Its findings page reports “No secrets
found,” zero open alerts, and zero closed alerts. Security advisories are
enabled. Code scanning, Dependabot alerts, a security policy, and private
vulnerability reporting are not yet enabled; these are optional governance
improvements rather than defects in the registered scientific result.

## Scientific effect

This amendment establishes off-device continuity, public discoverability,
cross-version source-only CI, and hosted secret scanning. It performs no new
empirical estimation and does not modify Runs 001–013, the negative state-
measurement result, the no-state-selection decision, or the transmission kill
gate.
