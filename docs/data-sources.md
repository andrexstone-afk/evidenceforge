# Data sources

## NLM Clinical Tables — ICD-10-CM

- Official endpoint: `https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search`
- Authentication: none
- Relevant fields: `code`, `name`; the response is a positional JSON array
- Client behavior: HTTPS host allowlist, 10-second default timeout, two bounded retries
  with exponential backoff or bounded `Retry-After` handling for network errors, 429
  responses, and 5xx responses; malformed JSON becomes a domain-specific error
- Limits: `count` supports up to 500; total retrieval is limited to 7,500
- Licensing: public NLM service; do not infer codes absent from its response
- Verified: 2026-07-24 against the official documentation and live AMD query

## NLM RxNav — RxNorm

- Official endpoint: `https://rxnav.nlm.nih.gov/REST/approximateTerm.json`
- Authentication: none for RxNorm content
- Relevant fields: RXCUI, name, source, score, rank
- Client behavior: HTTPS host allowlist, the same timeout/retry policy, RXCUI
  deduplication, preservation of service order and alternatives
- Licensing: RxNorm is non-proprietary; NLM does not endorse this project
- Verified: 2026-07-24; live service reported RxNorm version `06-Jul-2026` and API
  version `3.1.354`

No terminology data is redistributed. Tests use small synthetic response-shape fixtures.
