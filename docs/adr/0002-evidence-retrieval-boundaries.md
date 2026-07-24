# ADR 0002: Preserve evidence-source boundaries and search provenance

- Status: Accepted
- Date: 2026-07-24

## Context

PubMed and ClinicalTrials.gov expose different query languages, response formats,
pagination mechanisms, and identifiers. Later synthesis and claim-level QA must be able
to reproduce a search and link every claim to a stable normalized source record.

## Decision

Use deterministic source-specific query builders, immutable evidence-query and search
metadata models, one allowlisted async client per source, source-specific normalization,
and transparent deterministic ranking components. Callers provide an explicit ranking
year, which is retained with the result so time-dependent recency scoring is
reproducible. Store partial source dates as strings instead of fabricating day-level
precision. Treat retrieved text as untrusted data.

PubMed retrieval uses ESearch followed by a batched XML EFetch and checks that both
identifier sets match. ClinicalTrials.gov uses API v2 page tokens. Default tests use
synthetic contract fixtures; live checks are opt-in.

## Consequences

Vendor response changes are isolated to contract-tested client adapters. Search
provenance and ranking factors remain inspectable. The extra normalization code is
intentional: later pipeline stages do not depend on raw NCBI or ClinicalTrials.gov
payloads, and no ranking score can be mistaken for a validated evidence hierarchy.
