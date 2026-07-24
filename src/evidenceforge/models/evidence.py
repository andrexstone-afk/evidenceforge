"""Normalized evidence records and reproducible search metadata."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

EvidenceText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class EvidenceSource(StrEnum):
    """Supported external evidence sources."""

    PUBMED = "pubmed"
    CLINICAL_TRIALS = "clinicaltrials.gov"


class EvidenceQuery(BaseModel):
    """An inspectable query before it is sent to an external source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: EvidenceSource
    query: EvidenceText
    filters: dict[str, EvidenceText] = Field(default_factory=dict)
    page_size: int = Field(default=20, ge=1, le=100)


class SearchMetadata(BaseModel):
    """Metadata required to reproduce and audit one search page."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: EvidenceSource
    query: EvidenceText
    filters: dict[str, EvidenceText] = Field(default_factory=dict)
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_count: int = Field(ge=0)
    page_size: int = Field(ge=1)
    offset: int | None = Field(default=None, ge=0)
    page_token: str | None = None
    next_page_token: str | None = None


class PubMedRecord(BaseModel):
    """Normalized PubMed citation record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pmid: str = Field(pattern=r"^\d{1,10}$")
    title: EvidenceText
    abstract: str | None = None
    authors: list[EvidenceText] = Field(default_factory=list)
    journal: EvidenceText
    publication_date: str | None = None
    publication_types: list[EvidenceText] = Field(default_factory=list)
    doi: str | None = None
    mesh_terms: list[EvidenceText] = Field(default_factory=list)
    languages: list[EvidenceText] = Field(default_factory=list)
    is_retracted: bool = False
    is_correction: bool = False
    url: str = Field(pattern=r"^https://pubmed\.ncbi\.nlm\.nih\.gov/\d+/$")

    @model_validator(mode="after")
    def validate_canonical_url(self) -> Self:
        """Reject a canonical URL that points at a different PMID."""

        if self.url != f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/":
            raise ValueError("PubMed URL must match PMID")
        return self

    @property
    def record_id(self) -> str:
        """Return the stable source identifier."""

        return self.pmid


class TrialLocation(BaseModel):
    """A normalized ClinicalTrials.gov study location."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    facility: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None


class ClinicalTrialRecord(BaseModel):
    """Normalized ClinicalTrials.gov API v2 study record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    nct_id: str = Field(pattern=r"^NCT\d{8}$")
    title: EvidenceText
    summary: str | None = None
    conditions: list[EvidenceText] = Field(default_factory=list)
    interventions: list[EvidenceText] = Field(default_factory=list)
    outcomes: list[EvidenceText] = Field(default_factory=list)
    primary_outcomes: list[EvidenceText] = Field(default_factory=list)
    secondary_outcomes: list[EvidenceText] = Field(default_factory=list)
    study_type: EvidenceText
    allocation: str | None = None
    phases: list[EvidenceText] = Field(default_factory=list)
    enrollment: int | None = Field(default=None, ge=0)
    overall_status: EvidenceText
    sponsor: str | None = None
    start_date: str | None = None
    completion_date: str | None = None
    locations: list[TrialLocation] = Field(default_factory=list)
    last_update_date: str | None = None
    has_results: bool = False
    url: str = Field(pattern=r"^https://clinicaltrials\.gov/study/NCT\d{8}$")

    @model_validator(mode="after")
    def validate_canonical_url(self) -> Self:
        """Reject a canonical URL that points at a different NCT ID."""

        if self.url != f"https://clinicaltrials.gov/study/{self.nct_id}":
            raise ValueError("ClinicalTrials.gov URL must match NCT ID")
        return self

    @property
    def record_id(self) -> str:
        """Return the stable source identifier."""

        return self.nct_id


class EvidencePage[RecordT: (PubMedRecord, ClinicalTrialRecord)](BaseModel):
    """One normalized, auditable page from an evidence source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    records: list[RecordT]
    metadata: SearchMetadata
