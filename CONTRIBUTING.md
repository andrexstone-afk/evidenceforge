# Contributing

Use Python 3.12 and `uv`. Keep changes focused, typed, and tested. Default tests must
not call live or paid services.

Before proposing a change:

1. Run `uv sync --extra dev`.
2. Run Ruff lint and format checks, mypy, and pytest.
3. Review secrets/PHI, prompt-injection, outbound-request, licensing, regression, and
   clinical-claim risks relevant to the change.
4. Commit and push a coherent architectural checkpoint to the draft PR.
5. Resolve CodeRabbit's comprehensive or incremental findings before starting the next
   dependent phase. Avoid noisy tiny review commits.
6. At final PR completion, request `@coderabbitai full review` and resolve all Critical
   and High findings.

Never add real patient data, credentials, invented citations, model-generated ontology
codes, proprietary terminology datasets, or untraceable medical claims.
