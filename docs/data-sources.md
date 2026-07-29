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
- Verified: 2026-07-24 against the official documentation and live AMD query.
  Reverified 2026-07-29 with the exact cardiometabolic condition query; the service
  returned `E11.9` first and `E11.A` as the remission alternative. The same-day
  rare-disease query returned `G70.00` for myasthenia gravis without acute
  exacerbation.

## NLM RxNav — RxNorm

- Official endpoint: `https://rxnav.nlm.nih.gov/REST/approximateTerm.json`
- Authentication: none for RxNorm content
- Relevant fields: RXCUI, name, source, score, rank
- Client behavior: HTTPS host allowlist, the same timeout/retry policy, RXCUI
  deduplication, preservation of service order and alternatives
- Licensing: RxNorm is non-proprietary; NLM does not endorse this project
- Verified: 2026-07-24; live service reported RxNorm version `06-Jul-2026` and API
  version `3.1.354`. Reverified 2026-07-29 with live semaglutide and empagliflozin
  queries; the service returned ingredient RXCUIs `1991302` and `1545653`,
  respectively. Same-day efgartigimod alfa and rozanolixizumab queries returned
  ingredient RXCUIs `2587717` and `2642274`.

No terminology data is redistributed. Tests use small synthetic response-shape fixtures.

## PubMed — NCBI E-utilities

- Official documentation:
  - `https://www.ncbi.nlm.nih.gov/books/NBK25497/`
  - `https://www.ncbi.nlm.nih.gov/books/NBK25499/`
- Fixed HTTPS host: `eutils.ncbi.nlm.nih.gov`
- Endpoints: `esearch.fcgi` for PMID discovery followed by one batched
  `efetch.fcgi` request for PubMed XML citation records
- Authentication: no key is required at the default limit, but every request includes
  the NCBI-required `tool` and maintainer `email` parameters. An optional API key is
  read only from environment-backed settings.
- Published request policy: at most three requests per second without an API key and
  ten per second with a key. The client paces requests at approximately 2.9 or 9.1
  requests per second respectively, batches identifiers, honors bounded
  `Retry-After`, and retries only network failures, 429 responses, and 5xx responses.
- Pagination: ESearch uses a bounded `retstart` and `retmax`; the page's offset,
  requested size, total count, query, filters, and execution time are retained.
- Normalized fields: PMID, title, abstract, authors, journal, publication date,
  publication types, DOI, MeSH terms, languages, retraction/correction flags, and URL.
- Parsing: EFetch XML is parsed with entity-safe `defusedxml`; returned PMIDs must
  exactly match the ESearch identifier batch.
- Copyright: PubMed abstracts may contain copyrighted text. The repository does not
  redistribute downloaded abstracts; committed contract fixtures are synthetic.
- Verified: 2026-07-24 against NCBI documentation updated 2026-03-04. Live execution
  is opt-in and additionally requires `EVIDENCEFORGE_NCBI_EMAIL`.

## ClinicalTrials.gov API v2

- Official documentation:
  - `https://clinicaltrials.gov/data-api/api`
  - `https://clinicaltrials.gov/data-api/about-api/api-migration`
- Fixed HTTPS host and endpoint:
  `https://clinicaltrials.gov/api/v2/studies`
- Authentication: none
- API version: v2 only. EvidenceForge does not call retired classic/v1 query
  endpoints.
- Query and pagination: `query.term`, optional `filter.overallStatus`, bounded
  `pageSize`, opaque `pageToken`, and `nextPageToken`. Search metadata retains the
  exact query, filters, token, total count, requested size, and execution time.
- Normalized fields: NCT ID, title, summary, conditions, interventions, outcomes,
  study type, phase, enrollment, overall status, sponsor, dates, locations,
  last-update date, results availability, and canonical URL.
- Client behavior: conservative sequential pacing, 10-second default timeout, bounded
  retries for network errors, 429 responses, and 5xx responses, plus bounded
  `Retry-After` handling. The official material reviewed did not publish a numeric
  request-rate entitlement, so the client does not assume one.
- Verified: 2026-07-24 against the official API v2 documentation and a live
  credential-free one-record contract check.
