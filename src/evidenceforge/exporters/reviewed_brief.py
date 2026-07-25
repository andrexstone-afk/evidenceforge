"""JSON and Markdown rendering for canonical reviewed-brief exports."""

import json
import re
from html import escape as escape_html

import yaml

from evidenceforge.exporters.models import BriefExportDocument


def render_export_json(document: BriefExportDocument) -> str:
    """Render deterministic, newline-terminated canonical JSON."""

    return (
        json.dumps(
            document.model_dump(mode="json", exclude_none=True),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def render_export_markdown(document: BriefExportDocument) -> str:
    """Render a traceable reviewed brief with YAML metatags."""

    aggregate = document.aggregate
    result = aggregate.synthesis_qa
    draft = result.final_draft
    frontmatter = yaml.safe_dump(
        document.metatags.model_dump(mode="json", exclude_none=True),
        sort_keys=False,
        allow_unicode=True,
    ).strip()
    lines = [
        "---",
        *frontmatter.splitlines(),
        "---",
        "",
        "# EvidenceForge reviewed evidence brief",
        "",
        f"> {_markdown_text(result.disclaimer)}",
        "",
        f"**QA status:** `{result.final_qa.status.value}`",
        "",
        "## Clinical question",
        "",
        _markdown_text(aggregate.question),
        "",
        "## Parsed PICO",
        "",
        f"- Population: {_markdown_text(aggregate.pico.population)}",
        f"- Condition: {_markdown_text(aggregate.pico.condition)}",
        f"- Intervention: {_markdown_text(aggregate.pico.intervention)}",
        f"- Comparator: {_markdown_text(aggregate.pico.comparator)}",
        f"- Outcomes: {_markdown_join(aggregate.pico.outcomes)}",
        f"- Time horizon: {_markdown_text(aggregate.pico.time_horizon or 'Not specified')}",
        f"- Study context: {_markdown_text(aggregate.pico.study_context or 'Not specified')}",
        f"- Ambiguities: {_markdown_join(aggregate.pico.ambiguities) or 'None recorded'}",
        (
            "- Missing information: "
            f"{_markdown_join(aggregate.pico.missing_information) or 'None recorded'}"
        ),
        "",
        "## Final synthesis",
        "",
        "### Executive answer",
        "",
        _markdown_text(draft.executive_answer),
        "",
        "### Evidence summary",
        "",
        _markdown_text(draft.evidence_summary),
        "",
        "### Claims and supporting evidence",
        "",
    ]
    for claim in draft.claims:
        lines.extend(
            [
                f"#### {claim.claim_id} - {claim.claim_type.value}",
                "",
                _markdown_text(claim.text),
                "",
                f"- Linked sources: {_markdown_join(claim.linked_source_ids) or 'None'}",
            ]
        )
        for passage in claim.supporting_passages:
            location = f" ({_markdown_text(passage.location)})" if passage.location else ""
            lines.append(f"  - `{passage.source_id}`{location}: {_markdown_text(passage.text)}")
        lines.append("")

    lines.extend(["## Retrieved evidence", ""])
    ranking = {item.record_id: item for item in aggregate.retrieval.ranking}
    evidence = [("PubMed", record) for record in aggregate.retrieval.pubmed.records] + [
        ("ClinicalTrials.gov", record) for record in aggregate.retrieval.clinical_trials.records
    ]
    for source, record in evidence:
        ranked = ranking.get(record.record_id)
        rank_text = (
            f" Ranking score: {ranked.score:.3f} ({ranked.method})." if ranked is not None else ""
        )
        lines.extend(
            [
                f"### {record.record_id} - {_markdown_text(record.title)}",
                "",
                f"- Source: {source}",
                f"- URL: {record.url}",
                f"- Retrieval ranking:{rank_text or ' Not ranked.'}",
                "",
            ]
        )
    if not evidence:
        lines.append("- No evidence records were retained.")
    lines.extend(["", "## Terminology mappings", ""])
    for mapping in aggregate.mappings:
        selected = mapping.selected
        selected_text = (
            f"{_markdown_text(selected.code)} - {_markdown_text(selected.preferred_label)}"
            if selected is not None
            else "No validated selection"
        )
        lines.extend(
            [
                f"### {_markdown_text(mapping.original_term)}",
                "",
                f"- Ontology: {mapping.ontology.value}",
                f"- Selected: {selected_text}",
                f"- Match method: {_markdown_text(mapping.match_method)}",
                (f"- Human review required: {'yes' if mapping.human_review_required else 'no'}"),
                f"- Review note: {_markdown_text(mapping.review_reason or 'None')}",
                "",
            ]
        )

    lines.extend(
        [
            "## Interpretation and limitations",
            "",
            "### Clinical interpretation",
            "",
            _markdown_text(draft.clinical_interpretation),
            "",
            "### Limitations",
            "",
            *_bullets(draft.limitations),
            "",
            "### Uncertainties",
            "",
            *_bullets(draft.uncertainties),
            "",
            "### Evidence gaps",
            "",
            *_bullets(draft.evidence_gaps),
            "",
            "## Claim-level QA",
            "",
        ]
    )
    for assessment in result.final_qa.assessments:
        lines.extend(
            [
                f"- **{assessment.claim_id}** - `{assessment.classification.value}` "
                f"({assessment.severity.value}): {_markdown_text(assessment.explanation)}",
            ]
        )
    for finding in result.final_qa.deterministic_findings:
        lines.append(
            f"- **{finding.claim_id}** - `{finding.rule.value}` "
            f"({finding.severity.value}): {_markdown_text(finding.message)}"
        )
    if not result.final_qa.assessments and not result.final_qa.deterministic_findings:
        lines.append("- No final QA findings were recorded.")

    lines.extend(["", "## Revision history", ""])
    if result.revision is None:
        lines.append("- No revision was required.")
    else:
        for change in result.revision.changes:
            lines.extend(
                [
                    f"- **{change.claim_id}**: {_markdown_text(change.reason)}",
                    f"  - Original: {_markdown_text(change.original_text or 'Not present')}",
                    f"  - Revised: {_markdown_text(change.revised_text or 'Removed')}",
                ]
            )
    lines.extend(
        [
            "",
            "## Generation metadata",
            "",
            f"- Export schema: {document.schema_version}",
            f"- Generated at: {aggregate.created_at.isoformat()}",
            f"- Synthesis provider: {_markdown_text(result.synthesis_run.provider)}",
            f"- Synthesis model: {_markdown_text(result.synthesis_run.model)}",
            "",
        ]
    )
    return "\n".join(lines)


def _bullets(values: tuple[str, ...]) -> list[str]:
    return [f"- {_markdown_text(value)}" for value in values] or ["- None recorded."]


def _markdown_join(values: tuple[str, ...] | list[str]) -> str:
    return ", ".join(_markdown_text(value) for value in values)


def _markdown_text(value: str) -> str:
    """Render untrusted clinical/source text as inert Markdown data."""

    normalized = " ".join(value.split())
    html_safe = escape_html(normalized, quote=False)
    escaped = re.sub(r"([\\`*_[\]#!|])", r"\\\1", html_safe)
    escaped = re.sub(r"^([-+=])", r"\\\1", escaped)
    return re.sub(r"^(\d+)([.)])", r"\1\\\2", escaped)
