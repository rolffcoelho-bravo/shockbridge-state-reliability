# GitHub repository strategy

## Recommendation

Maintain two independent repositories with different histories and purposes.
Do not create one repository privately and later switch it to public. The
public repository should begin from the audited parentless release commit; the
private repository should preserve the canonical scientific history.

### Recommended names

- **Public:** `shockbridge-state-reliability`
- **Private:** `shockbridge-state-reliability-research-archive`

The public name is distinctive, matches the Python project, and is short enough
for a CV link. If a more immediately academic name is preferred, the strongest
alternatives are `euro-area-state-reliability` and
`real-time-macro-state-reliability`. A shorter private alternative is
`shockbridge-state-risk-lab`.

## Public repository

The public repository may contain only the Run 013 sanitized surface:

- source code, tests, dependency controls, and CI;
- source identifiers, URLs, hashes, and retrieval logic;
- research contracts and claim-controlled documentation;
- attributed aggregate tables and figures cleared by the rights matrix; and
- the Apache-2.0, CC BY 4.0, attribution, and citation files.

It must exclude the canonical Git history, flagship blueprints, raw and
processed external data, credentials, client information, commercial signals,
and failed-export private receipts. GitHub's hosted secret scanning and push
protection must be checked after the first authorized push.

## Private repository

The private repository is the canonical off-device Git record for scientific
history and protected intellectual property. It may contain the blueprints and
internal research decisions, but it must still exclude credentials and any
third-party dataset whose terms do not allow repository storage. Large or
restricted local evidence should be backed up separately with encryption and
access control, while its hashes and recovery metadata remain in Git.

GitHub documents that public repositories are visible to everyone and private
repositories are limited to authorized users. It also documents material
consequences when repository visibility changes, including fork and security-
feature behavior. Those constraints are why the two repositories should not be
forks or visibility variants of one another:

- <https://docs.github.com/en/repositories/creating-and-managing-repositories/about-repositories>
- <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility>
- <https://docs.github.com/en/code-security/concepts/secret-security/push-protection>

## Current publication state

The owner selected the recommended names and both independent repositories are
live. The sanitized public root commit uses the owner's ID-based GitHub
no-reply identity and preserves the accepted Run 013 tree. The canonical
private repository preserves the full scientific history while external data
and derived evidence remain ignored and hash-registered. Both first-push remote
`main` refs were verified against their local heads. Subsequent public fixes
must be appended without force, revalidate the manifest and data boundary, and
pass GitHub Actions; hosted security results remain part of every release
review.
