import httpx
import pytest

from evidenceforge.clients.terminology import ICD10CMClient, RxNormClient
from evidenceforge.exporters import render_markdown
from evidenceforge.llm import MockLLMProvider
from evidenceforge.pipelines import CodedBriefPipeline
from tests.fixtures.terminology import ICD_RESPONSE, rx_response

QUESTION = (
    "In adults with neovascular age-related macular degeneration, how does aflibercept "
    "compare with ranibizumab for improving visual acuity?"
)


@pytest.mark.asyncio
async def test_amd_question_produces_validated_coded_markdown() -> None:
    def icd_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=ICD_RESPONSE)

    def rx_handler(request: httpx.Request) -> httpx.Response:
        term = request.url.params["term"]
        if term == "aflibercept":
            return httpx.Response(
                200,
                json=rx_response(rxcui="1232150", name="aflibercept", score="13.27"),
            )
        return httpx.Response(
            200,
            json=rx_response(rxcui="595060", name="ranibizumab", score="13.41"),
        )

    icd10 = ICD10CMClient(transport=httpx.MockTransport(icd_handler))
    rxnorm = RxNormClient(transport=httpx.MockTransport(rx_handler))
    try:
        brief = await CodedBriefPipeline(
            llm=MockLLMProvider(),
            icd10=icd10,
            rxnorm=rxnorm,
        ).run(QUESTION, confirmed_no_phi=True)
    finally:
        await icd10.aclose()
        await rxnorm.aclose()

    markdown = render_markdown(brief)

    assert "`H35.3291`" in markdown
    assert "`1232150`" in markdown
    assert "`595060`" in markdown
    assert "does not retrieve or synthesize clinical evidence" in markdown
    assert brief.mappings[0].human_review_required is True
    assert "eye laterality, lesion activity" in (brief.mappings[0].review_reason or "")
    assert brief.llm_run.provider == "mock"
    assert brief.llm_run.retry_count == 0


@pytest.mark.asyncio
async def test_pipeline_rejects_apparent_phi_before_external_calls() -> None:
    icd10 = ICD10CMClient(transport=httpx.MockTransport(lambda request: httpx.Response(500)))
    rxnorm = RxNormClient(transport=httpx.MockTransport(lambda request: httpx.Response(500)))
    try:
        pipeline = CodedBriefPipeline(
            llm=MockLLMProvider(),
            icd10=icd10,
            rxnorm=rxnorm,
        )
        with pytest.raises(ValueError, match="patient-identifiable"):
            await pipeline.run(
                f"{QUESTION} Patient MRN: 123456 and DOB: 01/01/1950.",
                confirmed_no_phi=True,
            )
    finally:
        await icd10.aclose()
        await rxnorm.aclose()


@pytest.mark.asyncio
async def test_pipeline_requires_no_phi_confirmation() -> None:
    icd10 = ICD10CMClient(transport=httpx.MockTransport(lambda request: httpx.Response(500)))
    rxnorm = RxNormClient(transport=httpx.MockTransport(lambda request: httpx.Response(500)))
    try:
        pipeline = CodedBriefPipeline(
            llm=MockLLMProvider(),
            icd10=icd10,
            rxnorm=rxnorm,
        )
        with pytest.raises(ValueError, match="Confirm"):
            await pipeline.run(QUESTION)
    finally:
        await icd10.aclose()
        await rxnorm.aclose()
