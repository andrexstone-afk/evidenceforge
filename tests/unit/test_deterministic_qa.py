from evidenceforge.models.evidence import ClinicalTrialRecord, PubMedRecord
from evidenceforge.models.qa import (
    Claim,
    ClaimType,
    EvidencePassage,
    SynthesisDraft,
)
from evidenceforge.qa import run_deterministic_checks
from tests.fixtures.qa import original_draft, retrieval_fixture


def _evidence() -> list[PubMedRecord | ClinicalTrialRecord]:
    retrieval = retrieval_fixture()
    return [*retrieval.pubmed.records, *retrieval.clinical_trials.records]


def _draft_with_claim(claim: Claim) -> SynthesisDraft:
    return original_draft().model_copy(update={"claims": (claim,)})


def test_numeric_mismatch_is_high_severity() -> None:
    findings = run_deterministic_checks(original_draft(), _evidence())

    numeric = [item for item in findings if item.rule.value == "numeric_mismatch"]
    assert len(numeric) == 1
    assert numeric[0].claim_id == "CLM-0002"
    assert numeric[0].severity.value == "high"


def test_unknown_source_and_missing_passage_are_blocking() -> None:
    claim = Claim(
        claim_id="CLM-0001",
        text="A synthetic statement.",
        claim_type=ClaimType.OTHER,
        linked_source_ids=["99999999"],
    )

    findings = run_deterministic_checks(_draft_with_claim(claim), _evidence())
    rules = {item.rule.value for item in findings}

    assert {"unknown_source", "no_supporting_passage"} <= rules
    assert any(item.severity.value == "critical" for item in findings)


def test_hallucinated_passage_is_detected() -> None:
    claim = Claim(
        claim_id="CLM-0001",
        text="A synthetic statement.",
        claim_type=ClaimType.OTHER,
        linked_source_ids=["11111111"],
        supporting_passages=[
            EvidencePassage(
                source_id="11111111",
                text="This passage is absent from the retrieved record.",
            )
        ],
    )

    findings = run_deterministic_checks(_draft_with_claim(claim), _evidence())

    assert {item.rule.value for item in findings} == {"passage_not_found"}


def test_observational_causal_overstatement_is_detected() -> None:
    observational = _evidence()[0].model_copy(update={"publication_types": ["Observational Study"]})
    assert isinstance(observational, PubMedRecord)
    claim = Claim(
        claim_id="CLM-0001",
        text="The exposure caused improved outcomes.",
        claim_type=ClaimType.EFFICACY,
        linked_source_ids=["11111111"],
        supporting_passages=[
            EvidencePassage(
                source_id="11111111",
                text="At 52 weeks, visual acuity improved in both synthetic groups.",
            )
        ],
    )

    findings = run_deterministic_checks(_draft_with_claim(claim), [observational])

    assert "observational_causal_overstatement" in {item.rule.value for item in findings}


def test_study_design_mismatch_is_detected() -> None:
    observational = _evidence()[0].model_copy(update={"publication_types": ["Cohort Study"]})
    assert isinstance(observational, PubMedRecord)
    claim = Claim(
        claim_id="CLM-0001",
        text="The randomized trial found a synthetic association.",
        claim_type=ClaimType.STUDY_DESIGN,
        linked_source_ids=["11111111"],
        supporting_passages=[
            EvidencePassage(
                source_id="11111111",
                text="At 52 weeks, visual acuity improved in both synthetic groups.",
            )
        ],
    )

    findings = run_deterministic_checks(_draft_with_claim(claim), [observational])

    assert "study_design_mismatch" in {item.rule.value for item in findings}


def test_negated_design_status_and_causal_terms_do_not_trigger() -> None:
    evidence = _evidence()
    observational = evidence[0].model_copy(update={"publication_types": ["Cohort Study"]})
    recruiting_trial = evidence[1].model_copy(
        update={"overall_status": "RECRUITING", "has_results": False}
    )
    assert isinstance(observational, PubMedRecord)
    assert isinstance(recruiting_trial, ClinicalTrialRecord)
    claims = [
        Claim(
            claim_id="CLM-0001",
            text="This was not a randomized study and did not reduce outcomes.",
            claim_type=ClaimType.STUDY_DESIGN,
            linked_source_ids=["11111111"],
            supporting_passages=[
                EvidencePassage(
                    source_id="11111111",
                    text="At 52 weeks, visual acuity improved in both synthetic groups.",
                )
            ],
        ),
        Claim(
            claim_id="CLM-0002",
            text="The trial has not completed and has not reported results.",
            claim_type=ClaimType.TRIAL_STATUS,
            linked_source_ids=["NCT00000001"],
            supporting_passages=[
                EvidencePassage(
                    source_id="NCT00000001",
                    text="The synthetic trial enrolled 120 participants.",
                )
            ],
        ),
    ]
    draft = original_draft().model_copy(update={"claims": tuple(claims)})

    findings = run_deterministic_checks(draft, [observational, recruiting_trial])
    rules = {item.rule.value for item in findings}

    assert "study_design_mismatch" not in rules
    assert "trial_status_mismatch" not in rules
    assert "observational_causal_overstatement" not in rules


def test_negation_does_not_cross_into_a_later_positive_clause() -> None:
    observational = _evidence()[0].model_copy(update={"publication_types": ["Observational Study"]})
    assert isinstance(observational, PubMedRecord)
    claim = Claim(
        claim_id="CLM-0001",
        text="The study was not randomized but improved outcomes.",
        claim_type=ClaimType.EFFICACY,
        linked_source_ids=["11111111"],
        supporting_passages=[
            EvidencePassage(
                source_id="11111111",
                text="At 52 weeks, visual acuity improved in both synthetic groups.",
            )
        ],
    )

    findings = run_deterministic_checks(_draft_with_claim(claim), [observational])
    rules = {item.rule.value for item in findings}

    assert "study_design_mismatch" not in rules
    assert "observational_causal_overstatement" in rules


def test_contraction_negations_do_not_trigger() -> None:
    observational = _evidence()[0].model_copy(update={"publication_types": ["Observational Study"]})
    assert isinstance(observational, PubMedRecord)
    claim = Claim(
        claim_id="CLM-0001",
        text="The study isn't randomized and didn't reduce outcomes.",
        claim_type=ClaimType.STUDY_DESIGN,
        linked_source_ids=["11111111"],
        supporting_passages=[
            EvidencePassage(
                source_id="11111111",
                text="At 52 weeks, visual acuity improved in both synthetic groups.",
            )
        ],
    )

    findings = run_deterministic_checks(_draft_with_claim(claim), [observational])
    rules = {item.rule.value for item in findings}

    assert "study_design_mismatch" not in rules
    assert "observational_causal_overstatement" not in rules


def test_percentage_whitespace_is_normalized() -> None:
    source = _evidence()[0].model_copy(update={"abstract": "The response was 50%."})
    assert isinstance(source, PubMedRecord)
    claim = Claim(
        claim_id="CLM-0001",
        text="The response was 50 %.",
        claim_type=ClaimType.NUMERIC,
        linked_source_ids=["11111111"],
        supporting_passages=[EvidencePassage(source_id="11111111", text="The response was 50%.")],
    )

    findings = run_deterministic_checks(_draft_with_claim(claim), [source])

    assert "numeric_mismatch" not in {item.rule.value for item in findings}


def test_trial_status_and_outcome_role_mismatches_are_detected() -> None:
    evidence = _evidence()
    trial = evidence[1].model_copy(update={"overall_status": "RECRUITING", "has_results": False})
    assert isinstance(trial, ClinicalTrialRecord)
    claim = Claim(
        claim_id="CLM-0001",
        text=("The completed trial reported results and its primary outcome was blood pressure."),
        claim_type=ClaimType.TRIAL_STATUS,
        linked_source_ids=["NCT00000001"],
        supporting_passages=[
            EvidencePassage(
                source_id="NCT00000001",
                text="The synthetic trial enrolled 120 participants.",
            )
        ],
    )

    findings = run_deterministic_checks(_draft_with_claim(claim), [trial])
    rules = {item.rule.value for item in findings}

    assert "trial_status_mismatch" in rules
    assert "outcome_role_mismatch" in rules
