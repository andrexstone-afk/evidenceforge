from streamlit.testing.v1 import AppTest

from evidenceforge.api.schemas import BriefQAResponse, BriefReadResponse
from evidenceforge.db.schemas import BriefPersistenceInput
from evidenceforge.models.qa import SynthesisQAResult
from evidenceforge.ui import ExportArtifact
from streamlit_app.app import BRIEF_STATE, EXPORT_STATE, QA_STATE
from tests.fixtures.persistence import persistence_input

APP_PATH = "streamlit_app/app.py"
BRIEF_ID = "11111111-2222-4333-8444-555555555555"


def test_streamlit_app_starts_without_live_services() -> None:
    app = AppTest.from_file(APP_PATH).run()

    assert not app.exception
    assert app.title[0].value == "EvidenceForge · Reviewed evidence brief"
    assert "not a medical device" in app.warning[0].value.lower()
    assert len(app.text_input) == 1


def test_streamlit_app_rejects_invalid_brief_id_without_network() -> None:
    app = AppTest.from_file(APP_PATH).run()

    app.text_input[0].input("not-a-uuid")
    app.button[0].click().run()

    assert not app.exception
    assert any("valid EvidenceForge brief UUID" in item.value for item in app.error)


async def test_streamlit_app_renders_reviewed_artifact_graph() -> None:
    aggregate = await persistence_input()
    brief = BriefReadResponse(brief_id=BRIEF_ID, aggregate=aggregate)
    qa = BriefQAResponse(
        brief_id=BRIEF_ID,
        original_qa=aggregate.synthesis_qa.original_qa,
        final_qa=aggregate.synthesis_qa.final_qa,
        revision=aggregate.synthesis_qa.revision,
    )
    app = AppTest.from_file(APP_PATH)
    app.session_state[BRIEF_STATE] = brief
    app.session_state[QA_STATE] = qa
    app.session_state[EXPORT_STATE] = {
        "json": ExportArtifact(b"{}", "application/json", "brief.json"),
        "markdown": ExportArtifact(b"# Brief", "text/markdown", "brief.md"),
        "pdf": ExportArtifact(b"%PDF", "application/pdf", "brief.pdf"),
    }

    app.run(timeout=15)

    assert not app.exception
    assert len(app.tabs) == 6
    assert any("Final claim-level QA status: PASS" in item.value for item in app.success)
    assert any("CLM-0002" in item.label for item in app.expander)
    assert len(app.get("download_button")) == 3


async def test_streamlit_app_never_presents_blocked_qa_as_passing() -> None:
    aggregate = await persistence_input()
    synthesis = aggregate.synthesis_qa
    blocked_synthesis = SynthesisQAResult(
        original_draft=synthesis.original_draft,
        original_qa=synthesis.original_qa,
        revision=None,
        final_draft=synthesis.original_draft,
        final_qa=synthesis.original_qa,
        synthesis_run=synthesis.synthesis_run,
    )
    blocked_aggregate = BriefPersistenceInput.model_validate(
        {
            **aggregate.model_dump(mode="python"),
            "synthesis_qa": blocked_synthesis,
        }
    )
    brief = BriefReadResponse(brief_id=BRIEF_ID, aggregate=blocked_aggregate)
    qa = BriefQAResponse(
        brief_id=BRIEF_ID,
        original_qa=blocked_synthesis.original_qa,
        final_qa=blocked_synthesis.final_qa,
        revision=None,
    )
    app = AppTest.from_file(APP_PATH)
    app.session_state[BRIEF_STATE] = brief
    app.session_state[QA_STATE] = qa

    app.run(timeout=15)

    assert not app.exception
    assert any("BLOCKED" in item.value for item in app.error)
    assert not any("status: PASS" in item.value for item in app.success)


async def test_streamlit_app_fails_closed_when_claim_assessment_is_missing() -> None:
    aggregate = await persistence_input()
    brief = BriefReadResponse(brief_id=BRIEF_ID, aggregate=aggregate)
    incomplete_report = aggregate.synthesis_qa.final_qa.model_copy(
        update={"assessments": aggregate.synthesis_qa.final_qa.assessments[:1]}
    )
    qa = BriefQAResponse(
        brief_id=BRIEF_ID,
        original_qa=aggregate.synthesis_qa.original_qa,
        final_qa=incomplete_report,
        revision=aggregate.synthesis_qa.revision,
    )
    app = AppTest.from_file(APP_PATH)
    app.session_state[BRIEF_STATE] = brief
    app.session_state[QA_STATE] = qa

    app.run(timeout=15)

    assert not app.exception
    assert any("claim support cannot be verified" in item.value for item in app.error)
