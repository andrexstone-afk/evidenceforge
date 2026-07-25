# API v1

The Phase 4 API persists and retrieves a completed, validated Phase 3 artifact. It is
an ingestion boundary, not yet a question-to-brief orchestration endpoint. Clients must
produce the PICO, service-backed mappings, retrieved evidence, synthesis, and QA graph
before calling `POST /api/v1/briefs`.

Run migrations and start the service:

```bash
uv run alembic upgrade head
uv run evidenceforge serve
```

Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

## Create a brief

```http
POST /api/v1/briefs
Content-Type: application/json
X-Correlation-ID: import-2026-07-24-001

{
  "question": "A population-level clinical question...",
  "pico": { "...": "validated PICO fields" },
  "mappings": [{ "...": "service-returned terminology candidates" }],
  "retrieval": { "...": "PubMed and ClinicalTrials.gov retrieval result" },
  "synthesis_qa": { "...": "drafts, claim-level QA, and revision history" },
  "confirm_no_phi": true
}
```

The nested object shapes are defined in OpenAPI. Evidence identifiers and supporting
passages are checked against the submitted retrieval set, and deterministic QA
findings are recomputed before the transaction begins.

Example response:

```json
{
  "brief_id": "52f80aa8-2604-4f68-906a-66ac5678b7b8",
  "processing_status": "completed",
  "qa_status": "pass",
  "correlation_id": "import-2026-07-24-001",
  "links": {
    "result": "/api/v1/briefs/52f80aa8-2604-4f68-906a-66ac5678b7b8",
    "qa": "/api/v1/briefs/52f80aa8-2604-4f68-906a-66ac5678b7b8/qa",
    "export": "/api/v1/briefs/52f80aa8-2604-4f68-906a-66ac5678b7b8/export"
  }
}
```

## Read surfaces

- `GET /api/v1/briefs/{brief_id}` returns the lossless validated aggregate.
- `GET /api/v1/briefs/{brief_id}/qa` returns the original QA, final QA, and revision.
- `GET /api/v1/briefs/{brief_id}/export?format=json` returns a JSON export envelope.
- `GET /api/v1/health` returns service health without touching the database.

Markdown and PDF export are intentionally deferred to Phase 5.

## Errors and request tracing

Errors use one envelope:

```json
{
  "error": {
    "code": "brief_not_found",
    "message": "The requested brief does not exist.",
    "correlation_id": "import-2026-07-24-001",
    "details": []
  }
}
```

Every response includes `X-Correlation-ID`. A caller-supplied value is accepted only
when it contains 1–128 letters, digits, dots, underscores, or hyphens; otherwise the
service creates a UUID. Validation diagnostics do not reflect submitted values.

The create route requires `confirm_no_phi: true` and applies the same limited
identifier-pattern screen as the CLI. This is defense in depth, not de-identification;
EvidenceForge prohibits PHI input.
