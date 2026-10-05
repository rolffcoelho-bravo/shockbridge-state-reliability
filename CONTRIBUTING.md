# Contributing

Contributions that strengthen correctness, reproducibility, documentation, or
scientific auditability are welcome. This is a research codebase with frozen
evidence boundaries, so empirical conclusions cannot be changed by an ordinary
code contribution.

## Before opening a change

1. Search the existing issues and the
   [deviation log](research/methodology/deviation_log.md).
2. Use the bug form for software defects and the reproducibility form for
   environment, provenance, or evidence-boundary failures.
3. Report suspected security vulnerabilities privately under
   [the security policy](SECURITY.md).
4. Do not upload credentials, personal information, restricted material, or
   raw and processed external datasets.

## Development environment

The locked reference environment is Python 3.9:

```bash
python3.9 -m venv .venv
.venv/bin/python -m pip install -r requirements/build-py39.lock
.venv/bin/python -m pip install -r requirements/dev-py39.lock
.venv/bin/python -m pip install --no-deps -e .
make quality
make test
```

Supported-range checks also run on Python 3.12. Public CI uses Ubuntu 24.04 as
the primary runner and Ubuntu 26.04 as a prospective compatibility lane.

## Research-integrity requirements

- Preserve point-in-time timing and outcome-blind boundaries.
- Never relax a threshold, test, coverage floor, or exclusion merely to obtain
  a favorable result.
- Add or update a prospective protocol before changing an empirical design.
- Record defects and post-result corrections in the deviation and decision
  logs; do not silently rewrite historical evidence.
- Distinguish synthetic software tests from empirical evidence.
- Do not describe descriptive stability results as causal effects.

## Pull requests

Keep changes narrow and explain their scientific effect. Include tests for bug
fixes and hostile inputs where relevant. Confirm that `make quality`, the
appropriate test target, manifest checks, and public/private boundary checks
pass. A pull request that changes empirical artifacts must identify its frozen
protocol, inputs, hashes, and interpretation record.

All contributions are accepted under the repository's existing code and
documentation licenses.
