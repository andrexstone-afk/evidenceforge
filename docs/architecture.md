# Architecture

EvidenceForge is organized as independently testable stages. External terminology,
evidence, and LLM providers sit behind typed interfaces; pipeline services
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

## Evidence retrieval boundary

```mermaid
flowchart LR
    P[PICO] --> Q[Deterministic query builders]
    Q --> M[Inspectible EvidenceQuery]
    M --> RP[Provider-neutral retrieval pipeline]
    RP --> PM[Allowlisted PubMed client]
    RP --> CT[Allowlisted ClinicalTrials.gov v2 client]
    PM --> N[Normalized evidence records]
    CT --> N
    N --> R[Transparent heuristic ranking]
    R --> RC[Score plus component factors]
```

Query construction is deterministic and has no hidden network access. Source clients
own vendor response validation and normalization. Downstream stages consume only
normalized records and retained search metadata. Ranking is explicitly labeled as an
unvalidated retrieval heuristic; it does not claim to be a clinical evidence hierarchy.
Its caller-supplied reference year is retained with the result for reproducibility.
