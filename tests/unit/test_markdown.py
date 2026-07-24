from datetime import UTC, datetime

import yaml

from evidenceforge.exporters import render_markdown
from evidenceforge.llm.mock import amd_pico
from evidenceforge.models import CodedBrief, LLMRunMetadata


def test_frontmatter_round_trips_yaml_sensitive_question() -> None:
    question = 'Does "A\\B" improve outcomes?\nSecond line'
    brief = CodedBrief(
        question=question,
        pico=amd_pico(),
        mappings=[],
        llm_run=LLMRunMetadata(
            provider="mock",
            model="fixture",
            latency_ms=0,
        ),
        generated_at=datetime(2026, 7, 24, tzinfo=UTC),
    )

    markdown = render_markdown(brief)
    frontmatter = markdown.split("---", maxsplit=2)[1]

    assert yaml.safe_load(frontmatter)["question"] == question
