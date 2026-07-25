"""Deterministic claim-to-source consistency checks."""

import re

from evidenceforge.models.evidence import ClinicalTrialRecord, PubMedRecord
from evidenceforge.models.qa import (
    Claim,
    DeterministicFinding,
    DeterministicRule,
    QASeverity,
    SynthesisDraft,
)

EvidenceRecord = PubMedRecord | ClinicalTrialRecord


def run_deterministic_checks(
    draft: SynthesisDraft,
    evidence: list[EvidenceRecord],
) -> list[DeterministicFinding]:
    """Return reproducible safety findings without invoking an LLM."""

    evidence_by_id = {record.record_id: record for record in evidence}
    findings: list[DeterministicFinding] = []
    for claim in draft.claims:
        findings.extend(_check_links_and_passages(claim, evidence_by_id))
        linked = [
            evidence_by_id[source_id]
            for source_id in claim.linked_source_ids
            if source_id in evidence_by_id
        ]
        if not linked:
            continue
        findings.extend(_check_numeric_consistency(claim, linked))
        findings.extend(_check_study_design(claim, linked))
        findings.extend(_check_trial_status(claim, linked))
        findings.extend(_check_outcome_role(claim, linked))
        findings.extend(_check_causal_language(claim, linked))
    return findings


def _check_links_and_passages(
    claim: Claim,
    evidence_by_id: dict[str, EvidenceRecord],
) -> list[DeterministicFinding]:
    findings: list[DeterministicFinding] = []
    if not claim.linked_source_ids:
        findings.append(
            _finding(
                DeterministicRule.NO_LINKED_SOURCE,
                claim,
                QASeverity.HIGH,
                "Substantive claim has no linked evidence source.",
                "Remove the claim or link it to retrieved evidence with a supporting passage.",
            )
        )
    if not claim.supporting_passages:
        findings.append(
            _finding(
                DeterministicRule.NO_SUPPORTING_PASSAGE,
                claim,
                QASeverity.HIGH,
                "Substantive claim has no source-preserving supporting passage.",
                "Add a passage from a linked retrieved source or remove the claim.",
            )
        )
    unknown = sorted(set(claim.linked_source_ids) - evidence_by_id.keys())
    if unknown:
        findings.append(
            _finding(
                DeterministicRule.UNKNOWN_SOURCE,
                claim,
                QASeverity.CRITICAL,
                "Claim cites source IDs absent from the retrieved evidence set: "
                + ", ".join(unknown)
                + ".",
                "Remove fabricated identifiers or retrieve and validate the cited sources.",
            )
        )
    for passage in claim.supporting_passages:
        if (
            passage.source_id not in claim.linked_source_ids
            or passage.source_id not in evidence_by_id
        ):
            findings.append(
                _finding(
                    DeterministicRule.PASSAGE_SOURCE_MISMATCH,
                    claim,
                    QASeverity.HIGH,
                    f"Supporting passage source {passage.source_id} is not a valid linked source.",
                    "Link the passage to a retrieved source already associated with the claim.",
                )
            )
            continue
        source_text = _normalize_text(evidence_record_text(evidence_by_id[passage.source_id]))
        if _normalize_text(passage.text) not in source_text:
            findings.append(
                _finding(
                    DeterministicRule.PASSAGE_NOT_FOUND,
                    claim,
                    QASeverity.HIGH,
                    f"Supporting passage was not found in source {passage.source_id}.",
                    "Quote or closely preserve an actual passage from the normalized "
                    "source record.",
                )
            )
    return findings


def _check_numeric_consistency(
    claim: Claim,
    linked: list[EvidenceRecord],
) -> list[DeterministicFinding]:
    claim_numbers = _numbers(claim.text)
    if not claim_numbers:
        return []
    source_numbers = _numbers(" ".join(evidence_record_text(record) for record in linked))
    missing = sorted(claim_numbers - source_numbers)
    if not missing:
        return []
    return [
        _finding(
            DeterministicRule.NUMERIC_MISMATCH,
            claim,
            QASeverity.HIGH,
            f"Claim contains numeric values absent from linked evidence: {', '.join(missing)}.",
            "Correct the numeric values or remove the unsupported quantitative statement.",
        )
    ]


def _check_study_design(
    claim: Claim,
    linked: list[EvidenceRecord],
) -> list[DeterministicFinding]:
    text = claim.text.lower()
    expected: str | None = None
    if _has_unnegated_match(text, r"\b(?:randomi[sz]ed|rct)\b"):
        expected = "randomized"
        supported = any(_is_randomized(record) for record in linked)
    elif _has_unnegated_match(text, r"\b(?:observational|cohort)\b"):
        expected = "observational"
        supported = any(_is_observational(record) for record in linked)
    else:
        return []
    if supported:
        return []
    return [
        _finding(
            DeterministicRule.STUDY_DESIGN_MISMATCH,
            claim,
            QASeverity.HIGH,
            f"Claim labels linked evidence as {expected}, but source metadata does not support it.",
            "Use the study design stated in source metadata or remove the design label.",
        )
    ]


def _check_trial_status(
    claim: Claim,
    linked: list[EvidenceRecord],
) -> list[DeterministicFinding]:
    trials = [record for record in linked if isinstance(record, ClinicalTrialRecord)]
    if not trials:
        return []
    text = claim.text.lower()
    if _has_unnegated_match(text, r"\b(?:completed|finished)\b") and not any(
        trial.overall_status.upper() == "COMPLETED" for trial in trials
    ):
        return [
            _finding(
                DeterministicRule.TRIAL_STATUS_MISMATCH,
                claim,
                QASeverity.HIGH,
                "Claim describes a completed trial, but linked trial metadata is not completed.",
                "State the current registry status and distinguish planned from "
                "completed evidence.",
            )
        ]
    if _has_unnegated_match(
        text,
        r"\b(?:reported|posted|available)\s+results\b",
    ) and not any(trial.has_results for trial in trials):
        return [
            _finding(
                DeterministicRule.TRIAL_STATUS_MISMATCH,
                claim,
                QASeverity.HIGH,
                "Claim describes posted results, but linked trial records have no results.",
                "Describe the trial as registered/planned until results are present.",
            )
        ]
    return []


def _check_outcome_role(
    claim: Claim,
    linked: list[EvidenceRecord],
) -> list[DeterministicFinding]:
    trials = [record for record in linked if isinstance(record, ClinicalTrialRecord)]
    if not trials:
        return []
    text = claim.text.lower()
    if "primary outcome" in text:
        outcomes = [item for trial in trials for item in trial.primary_outcomes]
        role = "primary"
    elif "secondary outcome" in text:
        outcomes = [item for trial in trials for item in trial.secondary_outcomes]
        role = "secondary"
    else:
        return []
    if outcomes and any(_outcome_matches(claim.text, outcome) for outcome in outcomes):
        return []
    return [
        _finding(
            DeterministicRule.OUTCOME_ROLE_MISMATCH,
            claim,
            QASeverity.HIGH,
            f"Claimed {role} outcome does not match linked trial outcome metadata.",
            "Correct the outcome role or link the claim to matching registry metadata.",
        )
    ]


def _check_causal_language(
    claim: Claim,
    linked: list[EvidenceRecord],
) -> list[DeterministicFinding]:
    causal = _has_unnegated_match(
        claim.text.lower(),
        r"\b(?:caused|causes|led to|resulted in|improved|reduced|prevented)\b",
    )
    if not causal or not linked or not all(_is_observational(record) for record in linked):
        return []
    return [
        _finding(
            DeterministicRule.OBSERVATIONAL_CAUSAL_OVERSTATEMENT,
            claim,
            QASeverity.HIGH,
            "Claim uses causal language for evidence labeled observational.",
            "Use associational language and state the observational design limitation.",
        )
    ]


def evidence_record_text(record: EvidenceRecord) -> str:
    """Return the normalized record fields eligible to support claims."""

    if isinstance(record, PubMedRecord):
        return " ".join(
            (
                record.title,
                record.abstract or "",
                record.journal,
                record.publication_date or "",
                " ".join(record.publication_types),
                " ".join(record.mesh_terms),
            )
        )
    return " ".join(
        (
            record.title,
            record.summary or "",
            record.study_type,
            record.allocation or "",
            record.overall_status,
            str(record.enrollment) if record.enrollment is not None else "",
            " ".join(record.phases),
            " ".join(record.conditions),
            " ".join(record.interventions),
            " ".join(record.primary_outcomes),
            " ".join(record.secondary_outcomes),
        )
    )


def _numbers(value: str) -> set[str]:
    without_ids = re.sub(r"\b(?:NCT|PMID[:\s]*)\d+\b", "", value, flags=re.IGNORECASE)
    return {
        re.sub(r"[\s,]", "", item)
        for item in re.findall(
            r"(?<![A-Za-z])\d[\d,]*(?:\.\d+)?(?:[ \t]*%)?",
            without_ids,
        )
    }


def _has_unnegated_match(value: str, pattern: str) -> bool:
    negations = {
        "didn't",
        "doesn't",
        "hasn't",
        "isn't",
        "never",
        "no",
        "not",
        "without",
    }
    for match in re.finditer(pattern, value):
        prefix_segment = re.split(
            r"[.;,:]|\b(?:although|and|but|however|yet)\b",
            value[: match.start()],
        )[-1]
        prefix_tokens = re.findall(r"[a-z]+(?:'[a-z]+)?", prefix_segment)
        if not negations.intersection(prefix_tokens[-3:]):
            return True
    return False


def _is_randomized(record: EvidenceRecord) -> bool:
    if isinstance(record, ClinicalTrialRecord):
        return (record.allocation or "").upper() == "RANDOMIZED"
    return any("randomized controlled trial" in value.lower() for value in record.publication_types)


def _is_observational(record: EvidenceRecord) -> bool:
    if isinstance(record, ClinicalTrialRecord):
        return record.study_type.upper() == "OBSERVATIONAL"
    labels = " ".join(record.publication_types).lower()
    return any(
        value in labels for value in ("observational", "cohort", "case-control", "cross-sectional")
    )


def _outcome_matches(claim_text: str, outcome: str) -> bool:
    ignored = {
        "primary",
        "secondary",
        "outcome",
        "outcomes",
        "was",
        "were",
        "the",
        "and",
        "for",
        "trial",
    }
    claim_tokens = _tokens(claim_text) - ignored
    outcome_tokens = _tokens(outcome) - ignored
    return bool(claim_tokens & outcome_tokens)


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2}


def _normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def _finding(
    rule: DeterministicRule,
    claim: Claim,
    severity: QASeverity,
    message: str,
    correction: str,
) -> DeterministicFinding:
    return DeterministicFinding(
        rule=rule,
        claim_id=claim.claim_id,
        severity=severity,
        message=message,
        recommended_correction=correction,
    )
