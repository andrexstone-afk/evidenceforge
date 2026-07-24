# Architecture

EvidenceForge is organized as independently testable stages. External terminology,
evidence, and LLM providers will sit behind typed interfaces; pipeline services will
depend on those interfaces rather than vendor SDKs.

```mermaid
flowchart TB
    CLI[Typer CLI] --> Pipeline[Pipeline services]
    API[FastAPI API] --> Pipeline
    Pipeline --> Terminology[Terminology client protocols]
    Pipeline --> Evidence[Evidence client protocols]
    Pipeline --> LLM[LLM provider protocol]
    Pipeline --> Store[Repository layer]
    Pipeline --> Export[Exporters]
```

Phase 0 intentionally contains only the delivery boundaries and runtime configuration.
An application factory keeps tests isolated and avoids hidden startup work.

