# ADR 0003: Separate synthesis, claim QA, revision, and re-review

- Status: Accepted
- Date: 2026-07-24

## Context

A fluent synthesis can contain unsupported claims, fabricated citations, incorrect
numbers, or study-design overstatement even when its structured output is valid.
Letting the synthesis provider approve its own result, or reducing the brief to one
unreviewed text field, would hide those defects.

## Decision

Use immutable structured artifacts and provider-neutral boundaries for synthesis,
independent QA, and revision. Require every substantive claim to carry stable source
IDs and source-preserving passages. Combine a structured reviewer with deterministic
consistency rules, derive aggregate status in code, and block automatic passage when a
critical or high-severity issue remains. Re-review every revision and preserve both
versions plus an exact claim-change log. Bind every QA report to the canonical SHA-256
digest of the draft it reviewed and validate exact claim coverage.

Treat all retrieved evidence, drafts, and reviewer findings as untrusted prompt data.
Reject reviewer citations or passages that cannot be traced to the retrieved set.

## Consequences

The pipeline exposes claim-level support and unresolved defects instead of returning an
opaque answer. More provider calls and structured validation add latency, but the
stages are independently replaceable and deterministic tests require no paid service.
The rules are explicit consistency safeguards, not a validated evidence hierarchy or a
substitute for clinician review.
