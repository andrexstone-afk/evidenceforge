"""Deterministic Markdown handoff for benchmark question-selection review."""

import json
from html import escape

from evidenceforge.models.evaluation import BenchmarkQuestionSet, QuestionSetReviewStatus


def render_question_review_packet(question_set: BenchmarkQuestionSet) -> str:
    """Render a draft question set without creating review or gold-label provenance."""

    if question_set.review_status is not QuestionSetReviewStatus.DRAFT:
        raise ValueError("Review packets can only be generated from draft question sets")

    lines = [
        "---",
        "artifact_type: benchmark-question-review-packet",
        f"schema_version: {json.dumps(question_set.schema_version)}",
        f"dataset_name: {json.dumps(_yaml_text(question_set.dataset_name), ensure_ascii=False)}",
        "dataset_version: "
        f"{json.dumps(_yaml_text(question_set.dataset_version), ensure_ascii=False)}",
        f"review_status: {question_set.review_status.value}",
        f"review_scope: {question_set.review_scope}",
        f"annotation_status: {question_set.annotation_status}",
        f"versioned_at: {question_set.versioned_at.isoformat()}",
        "---",
        "",
        "# EvidenceForge benchmark question-selection review packet",
        "",
        "> **DRAFT — NOT PHYSICIAN REVIEWED.** This worksheet covers question selection",
        "> only. It contains no gold annotations and makes no clinical-performance claim.",
        "",
        "## Review instructions",
        "",
        "For each candidate, mark exactly one decision: Include as written, Revise, or",
        "Exclude. If revision is needed, record population-level wording only.",
        "",
        "- Do not enter patient-identifiable information.",
        "- Do not assign evidence-relevance or evidence-density labels.",
        "- Do not add ontology gold codes, claim-support labels, or treatment conclusions.",
        "- Do not change the source JSON review status during this worksheet review.",
        "- After all questions are reviewed, record the review date and reviewer count in",
        "  the versioned question-set JSON through the validated EvidenceForge contract.",
        "",
        "## Dataset context",
        "",
        f"- Dataset: {_inline(question_set.dataset_name)}",
        f"- Version: `{_code(question_set.dataset_version)}`",
        f"- Candidate questions: {len(question_set.questions)}",
        f"- Review method: {_inline(question_set.review_method)}",
        "",
        "### Current limitations",
        "",
        *[f"- {_inline(item)}" for item in question_set.limitations],
        "",
    ]

    for index, question in enumerate(question_set.questions, start=1):
        lines.extend(
            [
                f"## {index}. {_inline(question.clinical_domain)} — "
                f"{_inline(question.question_type)}",
                "",
                f"- Case ID: `{_code(question.case_id)}`",
                f"- Coded artifact: `{_code(question.coded_brief_path)}`",
                f"- Evidence-density expectation: `{question.evidence_density_expectation}`",
                "",
                "### Candidate question",
                "",
                f"> {_inline(question.question)}",
                "",
                "### Review focus",
                "",
                *[f"- {_inline(item)}" for item in question.review_focus],
                "",
                "### Decision",
                "",
                "- [ ] Include as written",
                "- [ ] Revise",
                "- [ ] Exclude",
                "",
                "**Proposed population-level revision (leave blank unless Revise is marked):**",
                "",
                "_Reviewer entry:_",
                "",
                "**Selection rationale:**",
                "",
                "_Reviewer entry:_",
                "",
            ]
        )

    lines.extend(
        [
            "## Review completion",
            "",
            "- [ ] Every candidate has exactly one decision.",
            "- [ ] Revisions contain population-level wording and no PHI.",
            "- [ ] No gold annotations or clinical conclusions were added.",
            "- Review date (YYYY-MM-DD):",
            "- Reviewer count:",
            "- Reviewer role(s), without personal identifiers:",
            "",
            "Completion of this worksheet does not itself change repository provenance.",
            "The versioned question-set JSON must be updated and independently validated.",
            "",
        ]
    )
    return "\n".join(lines)


def _plain(value: str) -> str:
    return " ".join(value.split())


def _yaml_text(value: str) -> str:
    return escape(_plain(value), quote=False)


def _code(value: str) -> str:
    return escape(_plain(value), quote=False).replace("`", "\\`")


def _inline(value: str) -> str:
    result = escape(_plain(value), quote=False).replace("\\", "\\\\")
    for character in "`*_[]|#":
        result = result.replace(character, f"\\{character}")
    return result
