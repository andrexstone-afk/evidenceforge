"""EvidenceForge Streamlit evidence-review interface."""

from uuid import UUID

import streamlit as st

from evidenceforge.api.schemas import BriefQAResponse, BriefReadResponse
from evidenceforge.models.evidence import ClinicalTrialRecord, PubMedRecord
from evidenceforge.models.qa import QAStatus
from evidenceforge.settings import get_settings
from evidenceforge.ui import EvidenceForgeAPIClient, EvidenceForgeAPIError, ExportArtifact
from evidenceforge.ui.presenters import (
    assessment_by_claim,
    evidence_by_id,
    mapping_rows,
    ranking_rows,
)

BRIEF_STATE = "reviewed_brief"
QA_STATE = "reviewed_brief_qa"
EXPORT_STATE = "reviewed_brief_exports"


def _client() -> EvidenceForgeAPIClient:
    settings = get_settings()
    return EvidenceForgeAPIClient(
        base_url=str(settings.streamlit_api_base_url),
        timeout_seconds=settings.request_timeout_seconds,
    )


def _show_status(status: QAStatus) -> None:
    if status is QAStatus.PASS:
        st.success("Final claim-level QA status: PASS")
    elif status is QAStatus.NEEDS_REVISION:
        st.warning("Final claim-level QA status: NEEDS REVISION")
    else:
        st.error("Final claim-level QA status: BLOCKED — unresolved high-severity findings")


def _load_brief(raw_brief_id: str) -> None:
    try:
        brief_id = UUID(raw_brief_id)
    except ValueError:
        st.error("Enter a valid EvidenceForge brief UUID.")
        return
    client = _client()
    try:
        client.health()
        brief = client.get_brief(brief_id)
        qa = client.get_qa(brief_id)
    except EvidenceForgeAPIError as error:
        st.error(str(error))
        return
    st.session_state[BRIEF_STATE] = brief
    st.session_state[QA_STATE] = qa
    st.session_state.pop(EXPORT_STATE, None)


def _render_overview(brief: BriefReadResponse) -> None:
    aggregate = brief.aggregate
    result = aggregate.synthesis_qa
    _show_status(result.final_qa.status)
    st.caption(f"Brief ID: {brief.brief_id} · Generated: {aggregate.created_at.isoformat()}")
    st.subheader("Clinical question")
    st.text(aggregate.question)
    st.subheader("Executive answer")
    st.text(result.final_draft.executive_answer)
    st.subheader("Evidence summary")
    st.text(result.final_draft.evidence_summary)
    st.subheader("Clinical interpretation")
    st.text(result.final_draft.clinical_interpretation)
    st.caption("Artifact disclaimer")
    st.text(result.disclaimer)
    for heading, values in (
        ("Limitations", result.final_draft.limitations),
        ("Uncertainties", result.final_draft.uncertainties),
        ("Evidence gaps", result.final_draft.evidence_gaps),
    ):
        st.subheader(heading)
        if values:
            for value in values:
                st.text(f"• {value}")
        else:
            st.caption("None recorded.")


def _render_pico_and_mappings(brief: BriefReadResponse) -> None:
    aggregate = brief.aggregate
    pico = aggregate.pico
    st.subheader("Parsed PICO")
    st.table(
        [
            {"element": "Population", "value": pico.population},
            {"element": "Condition", "value": pico.condition},
            {"element": "Intervention", "value": pico.intervention},
            {"element": "Comparator", "value": pico.comparator},
            {"element": "Outcomes", "value": "; ".join(pico.outcomes)},
            {"element": "Time horizon", "value": pico.time_horizon or "Not specified"},
            {"element": "Study context", "value": pico.study_context or "Not specified"},
        ]
    )
    st.subheader("Ambiguity and missing information")
    st.table(
        [
            *({"type": "Ambiguity", "detail": value} for value in pico.ambiguities),
            *(
                {"type": "Missing information", "detail": value}
                for value in pico.missing_information
            ),
        ]
        or [{"type": "None", "detail": "No ambiguity or missing information recorded."}]
    )
    st.caption("Normalized search terms")
    st.code("\n".join(pico.normalized_search_terms), language=None)
    st.subheader("Ontology mappings")
    rows = mapping_rows(aggregate)
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.warning("No ontology mappings were recorded.")
    for index, mapping in enumerate(aggregate.mappings, start=1):
        with st.expander(f"Mapping {index}: {mapping.ontology.value} candidates"):
            if mapping.review_reason:
                st.text(mapping.review_reason)
            st.dataframe(
                [
                    {
                        "selected": candidate == mapping.selected,
                        "code": candidate.code,
                        "label": candidate.preferred_label,
                        "service rank": candidate.source_rank,
                        "score": candidate.score,
                        "source": str(candidate.source_url),
                    }
                    for candidate in mapping.candidates
                ],
                hide_index=True,
                width="stretch",
            )


def _render_evidence(brief: BriefReadResponse) -> None:
    aggregate = brief.aggregate
    retrieval = aggregate.retrieval
    st.warning(
        "Ranking is a transparent retrieval heuristic, not a validated clinical evidence hierarchy."
    )
    st.subheader("Search provenance")
    st.table(
        [
            {
                "source": retrieval.pubmed.metadata.source.value,
                "query": retrieval.pubmed.metadata.query,
                "executed": retrieval.pubmed.metadata.executed_at.isoformat(),
                "results": retrieval.pubmed.metadata.total_count,
            },
            {
                "source": retrieval.clinical_trials.metadata.source.value,
                "query": retrieval.clinical_trials.metadata.query,
                "executed": retrieval.clinical_trials.metadata.executed_at.isoformat(),
                "results": retrieval.clinical_trials.metadata.total_count,
            },
        ]
    )
    st.subheader("Transparent ranking")
    ranked = ranking_rows(aggregate)
    if ranked:
        st.dataframe(ranked, hide_index=True, width="stretch")
    else:
        st.caption("No ranking rows were recorded.")
    records = evidence_by_id(aggregate)
    st.subheader("Retrieved source records")
    for record_id, record in records.items():
        with st.expander(f"{record_id} · {record.__class__.__name__}"):
            st.text(record.title)
            if isinstance(record, PubMedRecord):
                st.table(
                    [
                        {"field": "Journal", "value": record.journal},
                        {"field": "Date", "value": record.publication_date or "Not reported"},
                        {"field": "Types", "value": "; ".join(record.publication_types)},
                        {"field": "Retracted", "value": str(record.is_retracted)},
                    ]
                )
                if record.abstract:
                    st.caption("Abstract")
                    st.text(record.abstract)
            elif isinstance(record, ClinicalTrialRecord):
                st.table(
                    [
                        {"field": "Status", "value": record.overall_status},
                        {"field": "Study type", "value": record.study_type},
                        {
                            "field": "Enrollment",
                            "value": str(record.enrollment)
                            if record.enrollment is not None
                            else "Not reported",
                        },
                        {"field": "Has results", "value": str(record.has_results)},
                    ]
                )
                if record.summary:
                    st.caption("Summary")
                    st.text(record.summary)
            st.link_button("Open canonical source", record.url)


def _render_claim_qa(brief: BriefReadResponse, qa: BriefQAResponse) -> None:
    result = brief.aggregate.synthesis_qa
    assessments = assessment_by_claim(qa.final_qa)
    _show_status(qa.final_qa.status)
    st.caption(f"Original QA: {qa.original_qa.status.value} · Final QA: {qa.final_qa.status.value}")
    for claim in result.final_draft.claims:
        with st.expander(f"{claim.claim_id} · {claim.claim_type.value}", expanded=True):
            st.text(claim.text)
            assessment = assessments[claim.claim_id]
            st.table(
                [
                    {"field": "Support", "value": assessment.classification.value},
                    {"field": "Severity", "value": assessment.severity.value},
                    {"field": "Contradiction", "value": str(assessment.contradiction)},
                    {"field": "Source IDs", "value": ", ".join(assessment.source_ids)},
                ]
            )
            st.caption("Independent QA explanation")
            st.text(assessment.explanation)
            if assessment.recommended_correction:
                st.caption("Recommended correction")
                st.text(assessment.recommended_correction)
            for passage in assessment.supporting_passages:
                st.caption(f"Supporting passage · {passage.source_id}")
                st.text(passage.text)
    st.subheader("Deterministic findings")
    deterministic = [
        {
            "claim": item.claim_id,
            "rule": item.rule.value,
            "severity": item.severity.value,
            "message": item.message,
            "correction": item.recommended_correction,
        }
        for item in qa.final_qa.deterministic_findings
    ]
    if deterministic:
        st.dataframe(deterministic, hide_index=True, width="stretch")
    else:
        st.success("No deterministic findings remain in the final reviewed draft.")
    if qa.final_qa.untracked_claims:
        st.subheader("Untracked substantive claims")
        st.dataframe(
            [item.model_dump(mode="json") for item in qa.final_qa.untracked_claims],
            hide_index=True,
            width="stretch",
        )


def _render_revision(brief: BriefReadResponse, qa: BriefQAResponse) -> None:
    st.subheader("Preserved revision history")
    if qa.revision is None:
        st.info("No revision was required; the original and final drafts are identical.")
        return
    for change in qa.revision.changes:
        with st.expander(change.claim_id, expanded=True):
            st.caption("Original")
            st.text(change.original_text or "Claim added during revision.")
            st.caption("Revised")
            st.text(change.revised_text or "Claim removed during revision.")
            st.caption("Reason")
            st.text(change.reason)
            st.caption(
                "Sources: "
                f"{', '.join(change.original_source_ids) or 'none'} → "
                f"{', '.join(change.revised_source_ids) or 'none'}"
            )
    with st.expander("Original draft and QA"):
        st.text(brief.aggregate.synthesis_qa.original_draft.executive_answer)
        st.json(qa.original_qa.model_dump(mode="json"), expanded=False)


def _prepare_exports(brief_id: UUID) -> None:
    client = _client()
    exports: dict[str, ExportArtifact] = {}
    for name in ("json", "markdown", "pdf"):
        try:
            exports[name] = client.download_export(brief_id, name)
        except EvidenceForgeAPIError as error:
            st.error(f"{name.upper()} export: {error}")
    st.session_state[EXPORT_STATE] = exports


def _render_exports(brief: BriefReadResponse) -> None:
    st.subheader("Reviewed exports")
    st.caption(
        "Downloads are generated by the same reviewed export boundary used by the API and CLI."
    )
    if st.button("Prepare JSON, Markdown, and PDF", type="primary"):
        _prepare_exports(UUID(brief.brief_id))
    exports: dict[str, ExportArtifact] | None = st.session_state.get(EXPORT_STATE)
    if not exports:
        return
    for name, artifact in exports.items():
        st.download_button(
            f"Download {name.upper()}",
            data=artifact.content,
            file_name=artifact.filename,
            mime=artifact.media_type,
            key=f"download-{name}",
        )


def main() -> None:
    """Render the single-page evidence-review interface."""

    st.set_page_config(
        page_title="EvidenceForge Review",
        page_icon="🔎",
        layout="wide",
    )
    st.title("EvidenceForge · Reviewed evidence brief")
    st.warning(
        "Research and evidence-synthesis prototype only. Not a medical device, not for "
        "diagnosis, and not individualized clinical advice. Do not enter PHI."
    )
    st.caption(
        "This interface reads completed, validated artifacts from the EvidenceForge API. "
        "It does not call terminology, evidence, or LLM services."
    )
    with st.form("brief-loader"):
        raw_brief_id = st.text_input(
            "Persisted brief UUID",
            placeholder="52f80aa8-2604-4f68-906a-66ac5678b7b8",
        )
        submitted = st.form_submit_button("Load reviewed brief", type="primary")
    if submitted:
        _load_brief(raw_brief_id.strip())
    brief: BriefReadResponse | None = st.session_state.get(BRIEF_STATE)
    qa: BriefQAResponse | None = st.session_state.get(QA_STATE)
    if brief is None or qa is None:
        st.info("Load a persisted brief UUID to inspect its evidence and claim-level QA.")
        return
    tabs = st.tabs(
        [
            "Overview",
            "PICO & mappings",
            "Evidence",
            "Claims & QA",
            "Revision",
            "Exports",
        ]
    )
    with tabs[0]:
        _render_overview(brief)
    with tabs[1]:
        _render_pico_and_mappings(brief)
    with tabs[2]:
        _render_evidence(brief)
    with tabs[3]:
        _render_claim_qa(brief, qa)
    with tabs[4]:
        _render_revision(brief, qa)
    with tabs[5]:
        _render_exports(brief)


if __name__ == "__main__":
    main()
