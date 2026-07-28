# Streamlit evidence-review interface

The Phase 5 interface makes the reviewed artifact graph inspectable. It is not a
chatbot, does not accept a clinical question, and does not call terminology, evidence,
or LLM services. It reads completed artifacts through the stable FastAPI v1 contract.

## Run locally

Initialize the database and start the API:

```bash
uv run alembic upgrade head
uv run evidenceforge serve
```

In a second terminal:

```bash
uv run streamlit run streamlit_app/app.py
```

Open `http://127.0.0.1:8501` and enter a persisted brief UUID. The default API origin is
`http://127.0.0.1:8000`. Operators may set a different origin before startup:

```bash
EVIDENCEFORGE_STREAMLIT_API_BASE_URL=https://evidenceforge.example \
  uv run streamlit run streamlit_app/app.py
```

The value must be an HTTP(S) origin without credentials, path, query, or fragment. It is
not exposed as a browser control.

## Review surfaces

The interface separates:

- final QA status, question, synthesis, limitations, uncertainty, and evidence gaps;
- parsed PICO, normalized search terms, ambiguities, and missing information;
- selected terminology codes, service provenance, alternatives, and review flags;
- search provenance, source records, and every transparent ranking component;
- claims, linked source IDs, supporting passages, support classification,
  contradiction state, severity, and deterministic findings;
- original QA, revision changes, and the final reviewed artifact;
- canonical JSON, metatagged Markdown, and reviewed PDF downloads.

Ranking is labeled as an unvalidated retrieval heuristic. A blocked final QA status is
prominent and cannot be shown as passing.

## Failure behavior

The client validates the UUID before requesting data, checks API health, validates
brief and QA responses with Pydantic, verifies export media types, uses bounded
timeouts, and does not follow redirects. User-facing failures never include raw response
bodies or internal exception details. Export bytes are fetched only when the viewer
selects **Prepare JSON, Markdown, and PDF**.

## Testing

`st.testing.v1.AppTest` verifies startup, invalid-ID handling, the reviewed artifact
graph, and download controls without a running server. Mock-transport tests cover the
HTTP client, response validation, media-type validation, connection failures, and
error-detail non-disclosure.
