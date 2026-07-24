"""Validated Markdown export."""

from evidenceforge.models import CodedBrief


def render_markdown(brief: CodedBrief) -> str:
    lines = [
        "---",
        "brief_type: coded-clinical-question",
        f'question: "{brief.question.replace(chr(34), chr(39))}"',
        f"generated_at: {brief.generated_at.isoformat()}",
        f"prompt_version: {brief.prompt_version}",
        f"llm_provider: {brief.llm_run.provider}",
        f"llm_model: {brief.llm_run.model}",
        "---",
        "",
        "# EvidenceForge coded brief",
        "",
        f"> {brief.disclaimer}",
        "",
        "## Clinical question",
        "",
        brief.question,
        "",
        "## Parsed PICO",
        "",
        f"- Population: {brief.pico.population}",
        f"- Intervention: {brief.pico.intervention}",
        f"- Comparator: {brief.pico.comparator}",
        f"- Outcomes: {', '.join(brief.pico.outcomes)}",
        f"- Missing information: {', '.join(brief.pico.missing_information) or 'None identified'}",
        "",
        "## Ontology mappings",
        "",
    ]
    for mapping in brief.mappings:
        selected = mapping.selected
        code = selected.code if selected else "No validated match"
        label = selected.preferred_label if selected else "Human review required"
        lines.extend(
            [
                f"### {mapping.original_term}",
                "",
                f"- Ontology: {mapping.ontology.value}",
                f"- Selected: `{code}` — {label}",
                f"- Match method: {mapping.match_method}",
                f"- Human review required: {'yes' if mapping.human_review_required else 'no'}",
                f"- Review note: {mapping.review_reason or 'None'}",
                f"- Source: {selected.source_url if selected else 'No source match'}",
                "- Alternatives:",
            ]
        )
        lines.extend(
            f"  - `{candidate.code}` — {candidate.preferred_label}"
            for candidate in mapping.candidates[:3]
        )
        lines.append("")
    lines.extend(
        [
            "## Scope",
            "",
            "This Phase 1 artifact structures the question and validates terminology mappings. "
            "It does not retrieve or synthesize clinical evidence.",
            "",
            "## Generation metadata",
            "",
            f"- Provider: {brief.llm_run.provider}",
            f"- Model: {brief.llm_run.model}",
            f"- Latency: {brief.llm_run.latency_ms:.2f} ms",
            f"- Input tokens: {_reported(brief.llm_run.input_tokens)}",
            f"- Output tokens: {_reported(brief.llm_run.output_tokens)}",
            f"- Retry count: {brief.llm_run.retry_count}",
            "",
        ]
    )
    return "\n".join(lines)


def _reported(value: int | None) -> str:
    return str(value) if value is not None else "not reported"
