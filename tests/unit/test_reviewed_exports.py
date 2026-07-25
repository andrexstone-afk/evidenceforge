from typing import ClassVar

import pytest
import yaml

from evidenceforge.exporters import (
    BriefExportDocument,
    PDFExportError,
    build_export_document,
    render_export_html,
    render_export_json,
    render_export_markdown,
    render_export_pdf,
)
from evidenceforge.exporters.reviewed_brief import _markdown_text
from evidenceforge.models.ontology import Mapping, OntologyCandidate, OntologyName
from evidenceforge.models.qa import QAStatus
from tests.fixtures.persistence import persistence_input
from tests.fixtures.qa import QUESTION

BRIEF_ID = "11111111-2222-4333-8444-555555555555"


class RecordingPDFBackend:
    html: ClassVar[str] = ""

    def render(self, html: str) -> bytes:
        type(self).html = html
        return b"%PDF-synthetic"


class InvalidPDFBackend:
    def render(self, _html: str) -> bytes:
        return b"not-a-pdf"


async def test_export_document_is_lossless_and_service_code_grounded() -> None:
    aggregate = await persistence_input()

    document = build_export_document(brief_id=BRIEF_ID, aggregate=aggregate)
    restored = BriefExportDocument.model_validate_json(render_export_json(document))

    assert restored == document
    assert restored.aggregate == aggregate
    assert restored.metatags.question == QUESTION
    assert restored.metatags.clinical_domains == ()
    assert restored.metatags.conditions[0].icd10cm == "H35.3291"
    assert restored.metatags.interventions == ()
    assert restored.metatags.qa_status.value == "pass"
    assert restored.metatags.evidence_sources == ("pubmed", "clinicaltrials.gov")
    assert restored.metatags.prompt_versions == {
        "synthesis": "synthesis-v1",
        "qa_original": "qa-v1",
        "qa_final": "qa-v1",
        "revision": "revision-v1",
    }


async def test_export_metatags_classify_service_selected_rxnorm_codes() -> None:
    aggregate = await persistence_input()
    intervention = _rxnorm_mapping("aflibercept", code="1234")
    comparator = _rxnorm_mapping("ranibizumab", code="5678")
    aggregate = aggregate.model_copy(
        update={"mappings": (*aggregate.mappings, intervention, comparator)},
    )

    document = build_export_document(brief_id=BRIEF_ID, aggregate=aggregate)

    assert document.metatags.interventions[0].rxnorm == "1234"
    assert document.metatags.comparators[0].rxnorm == "5678"


async def test_exports_preserve_unselected_mapping_without_inventing_code() -> None:
    aggregate = await persistence_input()
    unselected = aggregate.mappings[0].model_copy(update={"selected": None})
    aggregate = aggregate.model_copy(update={"mappings": (unselected,)})

    document = build_export_document(brief_id=BRIEF_ID, aggregate=aggregate)

    assert document.metatags.conditions == ()
    assert "No validated selection" in render_export_markdown(document)
    assert "No validated selection" in render_export_html(document)


async def test_reviewed_markdown_has_parseable_metatags_and_traceability() -> None:
    document = build_export_document(
        brief_id=BRIEF_ID,
        aggregate=await persistence_input(),
    )

    markdown = render_export_markdown(document)
    frontmatter = yaml.safe_load(markdown.split("---", 2)[1])

    assert frontmatter["brief_id"] == BRIEF_ID
    assert frontmatter["qa_status"] == "pass"
    assert frontmatter["conditions"][0]["icd10cm"] == "H35.3291"
    assert "CLM-0001" in markdown
    assert "11111111" in markdown
    assert "Research evidence-synthesis prototype" in markdown
    assert "## Revision history" in markdown


async def test_reviewed_markdown_renders_untrusted_text_as_inert_data() -> None:
    aggregate = await persistence_input()
    question = '<img src="https://attacker.invalid/track"> ![load](track)'
    document = build_export_document(brief_id=BRIEF_ID, aggregate=aggregate)
    poisoned = aggregate.model_copy(
        update={"question": question},
    )
    document = document.model_copy(
        update={
            "aggregate": poisoned,
            "metatags": document.metatags.model_copy(update={"question": question}),
        },
    )

    markdown = render_export_markdown(document)
    frontmatter_text, body = markdown.split("---", 2)[1:]

    assert yaml.safe_load(frontmatter_text)["question"] == question
    assert '<img src="https://attacker.invalid/track">' not in body
    assert "![load](track)" not in body
    assert '&lt;img src="https://attacker.invalid/track"&gt;' in body
    assert r"\!\[load\](track)" in body


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("- item", r"\- item"),
        ("+ item", r"\+ item"),
        ("> quote", "&gt; quote"),
        ("1. ordered", r"1\. ordered"),
        ("2) ordered", r"2\) ordered"),
        ("---", r"\---"),
        ("===", r"\==="),
        ("    indented code", "indented code"),
    ],
)
def test_markdown_text_neutralizes_block_level_markers(
    value: str,
    expected: str,
) -> None:
    assert _markdown_text(value) == expected


async def test_pdf_boundary_receives_escaped_self_contained_html() -> None:
    document = build_export_document(
        brief_id=BRIEF_ID,
        aggregate=await persistence_input(),
    )

    result = render_export_pdf(document, backend=RecordingPDFBackend())

    assert result == b"%PDF-synthetic"
    assert "<!doctype html>" in RecordingPDFBackend.html
    assert QUESTION in RecordingPDFBackend.html
    assert "QA: pass" in RecordingPDFBackend.html
    assert 'class="status status-pass"' in RecordingPDFBackend.html


async def test_pdf_boundary_rejects_invalid_renderer_output() -> None:
    document = build_export_document(
        brief_id=BRIEF_ID,
        aggregate=await persistence_input(),
    )

    with pytest.raises(PDFExportError, match="invalid document"):
        render_export_pdf(document, backend=InvalidPDFBackend())


async def test_pdf_uses_alert_styling_for_non_passing_qa() -> None:
    aggregate = await persistence_input()
    document = build_export_document(brief_id=BRIEF_ID, aggregate=aggregate)
    result = aggregate.synthesis_qa
    blocked_result = result.model_copy(
        update={
            "final_qa": result.final_qa.model_copy(update={"status": QAStatus.BLOCKED}),
        },
    )
    blocked_aggregate = aggregate.model_copy(update={"synthesis_qa": blocked_result})
    document = document.model_copy(update={"aggregate": blocked_aggregate})

    html = render_export_html(document)

    assert 'class="status status-alert"' in html
    assert "QA: blocked" in html


def _rxnorm_mapping(term: str, *, code: str) -> Mapping:
    candidate = OntologyCandidate(
        ontology=OntologyName.RXNORM,
        code=code,
        preferred_label=term,
        source_url="https://rxnav.nlm.nih.gov/REST/approximateTerm.json",
        source_rank=1,
    )
    return Mapping(
        original_term=term,
        normalized_term=term,
        ontology=OntologyName.RXNORM,
        selected=candidate,
        candidates=[candidate],
        match_method="synthetic-service-candidate",
        human_review_required=False,
    )
