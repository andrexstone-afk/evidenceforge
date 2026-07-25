# Reviewed brief exports

Phase 5 renders one validated, persisted synthesis/QA aggregate through a shared export
service. JSON, Markdown, and PDF therefore use the same source object and do not perform
terminology, evidence, or LLM calls during export.

## Canonical document

The versioned export document contains:

- `schema_version`, currently `1.0`;
- metatags for the brief ID, original question, outcomes, evidence sources, QA status,
  generation time, and prompt versions;
- service-selected ICD-10-CM and RxNorm codes only; and
- the complete validated persistence aggregate, including retrieval records, ranking,
  claims, supporting passages, QA reports, and revision history.

`clinical_domains` remains empty until a validated domain field exists in the source
model. The exporter does not infer domains or terminology codes from free text.

## Formats

**JSON** is the lossless machine-readable contract. It serializes the canonical
document with deterministic indentation and a trailing newline.

**Markdown** adds YAML front matter followed by the clinical question, parsed PICO,
final synthesis, claim-to-source traceability, terminology mappings, limitations,
uncertainty, evidence gaps, final QA, revision history, and generation metadata.

**PDF** is a reviewed presentation of the same final artifact. It uses escaped,
self-contained HTML and blocks all external resource fetches. The default WeasyPrint
backend is injectable so contract tests do not require the native renderer; a separate
integration test generates and parses a real PDF.

EvidenceForge exports are research artifacts, not medical advice. The safety
disclaimer is retained in Markdown and PDF.

## API

```http
GET /api/v1/briefs/{brief_id}/export?format=json
GET /api/v1/briefs/{brief_id}/export?format=json&download=true
GET /api/v1/briefs/{brief_id}/export?format=markdown
GET /api/v1/briefs/{brief_id}/export?format=pdf
```

The original `format=json` response keeps the Phase 4 envelope stable. Add
`download=true` for the canonical JSON document; Markdown and PDF are always download
responses. Downloads include `Content-Disposition: attachment`. Invalid identifiers or
formats return the standard `422` envelope; missing briefs return `404`; and an
unavailable PDF renderer returns `503` without exposing native error details.

## CLI

Run migrations first, then provide the persisted brief UUID, format, and output path:

```bash
uv run alembic upgrade head
uv run evidenceforge brief export \
  --brief-id 52f80aa8-2604-4f68-906a-66ac5678b7b8 \
  --format json \
  --output reviewed-brief.json
```

Supported format values are `json`, `markdown`, and `pdf`. Existing files are preserved
unless `--force` is supplied. Successful CLI exports record a generic local-output
marker in `exported_artifacts`; the user-provided path is deliberately not persisted
because path names may contain identifying information.

## PDF runtime

WeasyPrint requires native Pango libraries in addition to the Python package:

```bash
# macOS with Homebrew
brew install pango

# Ubuntu
sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0
```

On Apple Silicon, use
`DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib uv run evidenceforge ...` if the dynamic
loader cannot locate Homebrew libraries. The CI workflow installs the Ubuntu runtime
before executing the default test suite.
