# Architecture

EvidenceForge is organized as independently testable stages. External terminology,
evidence, and LLM providers sit behind typed interfaces; pipeline services
depend on those interfaces rather than vendor SDKs.

```mermaid
flowchart TB
    CLI[Typer CLI] --> Pipeline[Pipeline services]
    API[FastAPI API] --> Store[Repository layer]
    Pipeline --> Store
    Pipeline --> Terminology[Terminology client protocols]
    Pipeline --> Evidence[Evidence client protocols]
    Pipeline --> LLM[LLM provider protocol]
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

## Synthesis and claim-level QA boundary

```mermaid
flowchart LR
    R[Ranked normalized evidence] --> S[Synthesis provider]
    S --> D[Original structured draft]
    D --> C[Deterministic consistency checks]
    D --> Q[Independent QA provider]
    R --> C
    R --> Q
    C --> G[Code-derived QA status]
    Q --> G
    G -->|non-passing| V[Revision provider]
    V --> A[Revision plus exact claim change log]
    A --> C2[Deterministic re-check]
    A --> Q2[Independent re-review]
    G -->|passing| F[Passing final artifact]
    C2 --> G2[Code-derived post-revision status]
    Q2 --> G2
    G2 -->|passing| F
    G2 -->|needs revision or blocked| B[Returned artifact marked non-passing]
```

The provider calls share a protocol but are separate injected dependencies. Structured
Pydantic models reject malformed outputs, and code—not a model—derives pass, revision,
or blocked status. All versions remain immutable. Questions, evidence, drafts, and QA
findings are serialized as untrusted user-prompt data and never inserted into
system-prompt authority. See [Claim-level synthesis and QA](qa-design.md).

## Persistence and API boundary

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI v1
    participant Guard as Pydantic + safety guards
    participant Repo as Transactional repository
    participant DB as SQLite

    Client->>API: POST completed Phase 3 artifact
    API->>Guard: Validate no-PHI confirmation and question
    Guard->>Guard: Cross-check evidence, passages, and deterministic QA
    Guard->>Repo: Save immutable aggregate
    Repo->>DB: Write normalized graph + lossless snapshot
    DB-->>Repo: Commit
    Repo-->>API: Stable brief UUID
    API-->>Client: 201 + result/QA/export links
    Client->>API: GET brief UUID
    API->>Repo: Parameterized lookup
    Repo->>Guard: Revalidate stored snapshot
    API-->>Client: Validated aggregate
```

The current POST contract ingests a completed artifact; orchestration from a question
through external retrieval and synthesis is a later integration. Core provenance is
normalized while a validated aggregate snapshot preserves exact round-trip fidelity.
See [API v1](api.md), [database design](database.md), and
[ADR 0004](adr/0004-normalized-sqlite-persistence.md).

## Reviewed export boundary

```mermaid
flowchart LR
    API[FastAPI export route] --> ES[Brief export service]
    CLI[Typer export command] --> ES
    ES --> Repo[Validated persisted aggregate]
    Repo --> Doc[Versioned canonical export document]
    Doc --> JSON[Lossless JSON]
    Doc --> MD[Metatagged inert Markdown]
    Doc --> HTML[Escaped self-contained HTML]
    HTML --> PDF[Network-isolated PDF backend]
    ES --> Meta[Export metadata only]
    Meta --> DB[(SQLite)]
```

The API and CLI share one service, so format selection cannot silently change the
underlying reviewed artifact. JSON is lossless; Markdown retains YAML metatags and the
human-readable provenance graph; PDF presents the reviewed subset with source IDs,
supporting passages, terminology provenance, QA, and revision history. PDF rendering
blocks resource fetches. Export bytes are not stored in SQLite, and the CLI does not
persist user-supplied file paths. See [reviewed brief exports](exports.md).
