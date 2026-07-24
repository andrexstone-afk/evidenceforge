# ADR 0001: Establish delivery boundaries before clinical workflow code

- Status: Accepted
- Date: 2026-07-24

## Context

EvidenceForge is a new repository. Clinical correctness depends on keeping delivery,
configuration, provider, pipeline, and persistence concerns replaceable and testable.

## Decision

Start with a `src`-layout Python 3.12 package, a FastAPI application factory, a Typer
CLI, typed environment settings, structured logging, deterministic tests, and locked
`uv` dependencies. Add clinical stages only as complete vertical slices.

## Consequences

The repository runs and validates before clinical behavior exists. Phase 1 can add
provider protocols and the coded-brief workflow without coupling them to the API.

