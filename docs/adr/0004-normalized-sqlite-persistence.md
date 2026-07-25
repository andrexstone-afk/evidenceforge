# ADR 0004: Normalized SQLite persistence with a validated aggregate snapshot

- Status: Accepted
- Date: 2026-07-24

## Context

Phase 3 produces an immutable graph containing a question, PICO fields, terminology
candidates, searches, evidence, ranked membership, draft versions, claim-source links,
LLM run metadata, QA findings, and revision history. Storing only one opaque JSON value
would make those clinically important relationships difficult to inspect. Reconstructing
the exact versioned artifact solely from relational rows would duplicate serialization
logic and make schema evolution unnecessarily fragile during the MVP.

## Decision

Use SQLAlchemy 2.x with SQLite and Alembic. Normalize the core searchable and auditable
relationships into dedicated tables, including claims, source links, QA reports,
findings, and revision changes. Persist the already validated aggregate as a
supplemental lossless snapshot on the brief row and revalidate it whenever it is read.
Write the relational projection and aggregate snapshot in one transaction.

Keep evidence records scoped as retrieval snapshots rather than globally deduplicating
them. The same external identifier may change when a registry record is updated, so
each brief must retain the version it actually used. Limit MVP configuration to
`sqlite:///` URLs; adding another database requires a later compatibility decision.

## Consequences

The API can return the exact reviewed artifact while SQL queries can inspect the
normalized clinical and provenance graph. The snapshot duplicates some data by design,
so future mutations must continue to update both representations transactionally.
Phase 4 exposes create/read/QA/JSON-export contracts; it does not yet run the complete
retrieval and synthesis pipeline from a question or produce Markdown/PDF exports.
