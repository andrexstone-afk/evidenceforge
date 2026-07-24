"""Validated domain models."""

from evidenceforge.models.brief import CodedBrief
from evidenceforge.models.evidence import (
    ClinicalTrialRecord,
    EvidencePage,
    EvidenceQuery,
    EvidenceSource,
    PubMedRecord,
    SearchMetadata,
    TrialLocation,
)
from evidenceforge.models.llm import LLMRunMetadata
from evidenceforge.models.ontology import Mapping, OntologyCandidate, OntologyName
from evidenceforge.models.pico import PICO
from evidenceforge.models.qa import (
    Claim,
    ClaimAssessment,
    ClaimType,
    ConsistencyAssessment,
    DeterministicFinding,
    DeterministicRule,
    EvidencePassage,
    QAReport,
    QAReviewerOutput,
    QASeverity,
    QAStatus,
    RevisedDraftOutput,
    RevisionArtifact,
    RevisionChange,
    SupportClassification,
    SynthesisDraft,
    SynthesisQAResult,
    UntrackedClaimFinding,
)

__all__ = [
    "PICO",
    "Claim",
    "ClaimAssessment",
    "ClaimType",
    "ClinicalTrialRecord",
    "CodedBrief",
    "ConsistencyAssessment",
    "DeterministicFinding",
    "DeterministicRule",
    "EvidencePage",
    "EvidencePassage",
    "EvidenceQuery",
    "EvidenceSource",
    "LLMRunMetadata",
    "Mapping",
    "OntologyCandidate",
    "OntologyName",
    "PubMedRecord",
    "QAReport",
    "QAReviewerOutput",
    "QASeverity",
    "QAStatus",
    "RevisedDraftOutput",
    "RevisionArtifact",
    "RevisionChange",
    "SearchMetadata",
    "SupportClassification",
    "SynthesisDraft",
    "SynthesisQAResult",
    "TrialLocation",
    "UntrackedClaimFinding",
]
