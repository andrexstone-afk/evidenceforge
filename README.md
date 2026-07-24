# EvidenceForge

EvidenceForge is an open-source research prototype that turns plain-English clinical
questions into structured, ontology-coded, evidence-backed briefs with claim-level
traceability. It is designed to make uncertainty, missing evidence, and model-generated
synthesis visible rather than presenting an opaque answer.

> EvidenceForge is not a medical device, is not for diagnosis, and does not provide
> individualized clinical advice. It does not replace clinical judgment.

## Project status

**Phase 2 — Evidence retrieval in progress.** Phase 1 is complete: the package can parse the documented AMD
question through a deterministic mock provider, retrieve live ICD-10-CM and RxNorm
candidates, preserve alternatives, and export validated Markdown. Phase 2 now has
typed PubMed and ClinicalTrials.gov v2 records, reproducible query builders,
source-isolated async clients, retained search metadata, and transparent heuristic
ranking. Integration into the end-to-end brief, synthesis, and claim-level QA remains
future work.

## Planned pipeline

```mermaid
flowchart LR
    Q[Clinical question] --> P[Structured PICO]
    P --> O[Service-backed ontology mapping]
    O --> R[Evidence retrieval and ranking]
    R --> S[Structured synthesis]
    S --> C[Claim-level QA]
    C --> B[Revised, traceable brief]
```

## Local setup

Prerequisites: Git and [`uv`](https://docs.astral.sh/uv/). `uv` installs the required
Python 3.12 runtime when needed.

```bash
git clone <repository-url>
cd evidenceforge
uv sync --extra dev
uv run evidenceforge version
uv run evidenceforge serve
uv run evidenceforge brief create \
  --question "In adults with neovascular age-related macular degeneration, how does aflibercept compare with ranibizumab for improving visual acuity?" \
  --confirm-no-phi \
  --output amd-coded-brief.md
```

Open `http://127.0.0.1:8000/docs` for API documentation or call
`GET /api/v1/health`.

## Configuration

Copy `.env.example` to `.env` and override only the settings you need. Environment
variables use the `EVIDENCEFORGE_` prefix. Never provide PHI or commit credentials.

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

The default tests are deterministic and do not call live or paid services. The CLI
terminology lookup is live and therefore requires network access.

Set `EVIDENCEFORGE_LLM_PROVIDER=openai` and `EVIDENCEFORGE_OPENAI_API_KEY` to use the
production OpenAI adapter. The default mock provider exists for the AMD example and
tests; it is not a general clinical parser.

The default suite contract-tests the OpenAI request/structured-response boundary without
a paid call. Run a credentialed integration smoke test separately before claiming a
specific model is operational in a deployment. Set
`EVIDENCEFORGE_OPENAI_REASONING_ENABLED=false` for models that do not accept reasoning
options; otherwise choose a supported `EVIDENCEFORGE_OPENAI_REASONING_EFFORT`.

The CLI requires an explicit `--confirm-no-phi` declaration and applies a limited
identifier-pattern screen before any external call. This is defense in depth, not a
guarantee that free text is de-identified. Never enter patient data.

PubMed requests require `EVIDENCEFORGE_NCBI_EMAIL` so the client can send NCBI's
required maintainer contact parameter. `EVIDENCEFORGE_NCBI_API_KEY` is optional. Live
evidence checks are opt-in:

```bash
EVIDENCEFORGE_RUN_LIVE_INTEGRATION=1 uv run pytest tests/integration
```

## Architecture and safety

The package uses an application factory, typed environment settings, and separate API,
CLI, and configuration boundaries. Terminology and evidence clients are async,
allowlisted, and replaceable. See [architecture](docs/architecture.md),
[safety](docs/safety.md), and [security policy](SECURITY.md).

## Roadmap

- Phase 1: CLI question → PICO → live ICD-10-CM/RxNorm mapping → validated Markdown
- Phase 2: PubMed and ClinicalTrials.gov v2 retrieval and transparent ranking
- Phase 3: structured synthesis, claim-source linking, QA, and revision
- Phase 4: normalized persistence and stable API contracts
- Phase 5+: exports, interface, evaluation, and portfolio release

## License and contributing

Licensed under Apache 2.0. See [LICENSE](LICENSE) and
[CONTRIBUTING.md](CONTRIBUTING.md).
