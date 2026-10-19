# Reproducing the verified evidence

This repository exposes two deliberately separate verification tiers. A passing
public software gate is evidence that the released code is portable; it is not
an empirical reproduction unless the hash-registered evidence artifacts are
also present.

## 1. Public source-only verification

Use Python 3.9 or 3.12 on Ubuntu 24.04 (the hosted matrix) or an equivalent
environment:

```bash
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
make quality
make test-public
```

The prospective public contract discovers 259 tests, executes 248, permits exactly eleven
explicitly labelled evidence-bound skips, and enforces 87% branch-aware
coverage of the released source. An additional Ubuntu 26.04 lane is
prospective compatibility evidence and is not an empirical-reproduction claim.

## 2. Canonical evidence reproduction

The exact verified environment is Python 3.9 with the committed build and
development locks:

```bash
python3.9 -m venv .venv
.venv/bin/python -m pip install -r requirements/build-py39.lock
.venv/bin/python -m pip install -r requirements/dev-py39.lock
.venv/bin/python -m pip install --no-deps -e .
make inventory-audit
make quality
make test
```

This tier requires the locally retained, hash-registered evidence inventory. It
executes all 271 tests and enforces 90% coverage. Run 011 and Run 012 recorded
byte-for-byte equality for all four registered Run 010 outputs in clean and
locked Python 3.9 environments.

## Interpreting expected failures

- Missing raw or processed evidence in a public clone is expected. These files
  are excluded because source rights and the public/private boundary are
  conservative by design.
- `make contract-audit` intentionally exits with status `2` while no registered
  state passes the measurement gate. That status protects the outcome firewall;
  it is not a software defect.
- A test skip is acceptable only when the public runner labels it as
  evidence-bound and the total remains exactly eleven.

## Audit trail

Start with the versioned result reports under `reports/methodology/`, then use
their linked protocols, aggregate audits, and manifests. Artifact metadata,
source URLs, retrieval timestamps, byte sizes, and SHA-256 hashes are retained
in the published manifests; datasets themselves are not redistributed.

If a command produces a different result, open the reproducibility issue form
and include the operating system, Python version, command, exit status, and a
minimal log excerpt. Do not attach protected data, credentials, or full local
paths.
