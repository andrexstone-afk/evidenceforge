# Security policy

## Reporting

Do not open a public issue for a suspected vulnerability. Use GitHub's
[private vulnerability reporting](https://github.com/andrexstone-afk/evidenceforge/security/advisories/new)
with reproduction details and impact. Never include credentials, secrets, or PHI.
The maintainer will acknowledge the report, coordinate remediation and a disclosure
date in the private advisory, and publish only after a fix is available. If the private
reporting form is unavailable, do not disclose the issue publicly; contact the
maintainer through their GitHub profile to request a private channel.

## Threat model

- Configuration secrets belong only in ignored environment files and must not be logged.
- EvidenceForge does not accept, store, or process PHI.
- Retrieved abstracts, trial records, generated drafts, and reviewer findings are
  untrusted data, never instructions. They remain in user-prompt envelopes and never
  receive system-prompt authority. Reviewer source IDs and passages are validated
  against the retrieved evidence set.
- External clients must restrict requests to documented NLM, NCBI,
  ClinicalTrials.gov, and CMS hosts and apply timeouts, bounded retries, and backoff.
- Database access must be parameterized and boundary input validated with Pydantic.
- Proprietary or restricted terminology data, including CPT, must not be committed.

Supported versions and coordinated-disclosure details will be added before the first
public release.
