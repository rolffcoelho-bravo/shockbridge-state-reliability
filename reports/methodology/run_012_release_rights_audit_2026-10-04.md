# Run 012 public-release rights and boundary audit

**Audit date:** 2026-10-04  
**Scope:** prospective repository surface; current tracked tree and Git history  
**Legal status:** conservative research governance, not legal advice  
**GitHub repository created:** no  
**License selected:** no

## Conclusion

The current tracked tree contains no detected credential signature, suspicious
credential filename, non-local author identity, or tracked raw/processed data.
Its current files no longer expose a workstation home path. It is not ready to
publish as the existing full Git history: 28 historical blob-pattern findings
retain the former absolute workstation path in the storage map and artifact
inventory. No credential was detected in those historical objects.

The safest publication route is a new, squashed public repository created from
an audited current-tree export. The complete granular history should remain in
the private local repository. Rewriting or deleting local scientific history is
neither necessary nor desirable.

## Source-rights basis

The current ESCB policy permits free reuse of publicly released statistics with
source attribution, while excluding third-party data without originator
permission. The ECB disclaimer additionally requires accurate representation,
ECB attribution, and explicit disclosure when the user modifies information,
including calculations such as growth rates. Authored ECB papers and documents
have a narrower republication rule.

Accordingly, the public repository may distribute source identifiers,
retrieval code, hashes, transformations, and attributed derived displays. Raw
workbooks, archive files, documentation PDFs, and third-party factor files
remain fetch-only under the project's conservative policy.

Official references:

- https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html
- https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html

## Artifact-family decision matrix

| Artifact family | Current-tree status | Proposed public disposition | Required condition |
|---|---|---|---|
| Original Python source and tests | Tracked; no detected credential | Publish | Owner-selected code license |
| Research protocols, decisions, deviations, and claim ledgers | Tracked | Publish | Final content and personal-information review |
| Source manifests and retrieval code | Tracked | Publish | Preserve URLs, hashes, timestamps, and attribution |
| Raw ECB statistics | Ignored/local | Fetch-only | Never add to the initial public tree |
| ECB workbooks, archive ZIP, and RTD documentation PDF | Ignored/local | Fetch-only | Do not republish without narrower rights basis |
| Third-party ABGMR factor CSV | Ignored/local | Fetch-only | Record upstream URL/hash; no redistribution without permission |
| Derived state panels and large empirical diagnostics | Ignored/local | Rebuild locally | Publish schemas, code, configs, hashes, and aggregate results |
| Deterministic Run 011 tables and figures | Tracked | Publish candidate | Add “Source: ECB statistics; authors' calculations” in manuscript captions and disclose transformations |
| Audit JSON and manifests | Tracked | Publish | Confirm no workstation path or nonpublic endpoint |
| Dependency locks and CI | Tracked/candidate | Publish | Keep abstract package metadata separate from exact environment locks |
| Blueprint v1/v2 | Tracked locally | Exclude from first public export pending owner review | They contain broad aspirational and private-boundary material not required to reproduce the reported result |

## Repository-history audit

The immutable machine-readable release audit records the exact tracked-file,
commit, and unique-blob counts at execution time. Results:

- credential signatures: pass in current tree and full history;
- current-tree home-path privacy: pass;
- full-history home-path privacy: fail, with 28 blob-pattern findings limited to
  `PROJECT_STORAGE.md` and the local artifact inventory;
- raw/processed data boundary: pass;
- suspicious key/credential filenames: none;
- public author email identities: none; commits use the local checkpoint identity.

The scan deliberately does not perform generic high-entropy secret detection
and is not a substitute for a hosted-platform secret scanner. Run the platform's
secret protection on the sanitized export before making it public.

## License blocker

No repository license has been selected. Public visibility without a license
would leave reuse rights ambiguous and would weaken the CV/research objective.
License selection is an owner-level decision. The first public export must not
be created until that decision is recorded.

## Release decision

Status: `PUBLICATION_BLOCKED_HISTORY_LICENSE_AND_OWNER_REVIEW`.

The code and evidence surface are suitable candidates for publication after:

1. owner selection of a code/document license strategy;
2. owner approval to exclude blueprint v1/v2 from the first public export;
3. creation of a sanitized squashed export rather than pushing local history;
4. hosted secret scanning of that export; and
5. a final attribution and link check.
