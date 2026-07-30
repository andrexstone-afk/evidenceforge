"""Provider-neutral PICO-to-evidence retrieval orchestration."""

import asyncio
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from evidenceforge.models.evidence import (
    ClinicalTrialRecord,
    EvidencePage,
    EvidenceQuery,
    PubMedRecord,
)
from evidenceforge.models.pico import PICO
from evidenceforge.ranking import RankedEvidence, rank_evidence
from evidenceforge.services.evidence_queries import build_pubmed_query, build_trial_query


class PubMedSearcher(Protocol):
    """Replaceable PubMed search boundary."""

    async def search(
        self,
        query: EvidenceQuery,
        *,
        offset: int = 0,
    ) -> EvidencePage[PubMedRecord]: ...


class ClinicalTrialSearcher(Protocol):
    """Replaceable ClinicalTrials.gov search boundary."""

    async def search(
        self,
        query: EvidenceQuery,
        *,
        page_token: str | None = None,
    ) -> EvidencePage[ClinicalTrialRecord]: ...


class EvidenceRetrievalResult(BaseModel):
    """Normalized source pages and their transparent combined ranking."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pubmed: EvidencePage[PubMedRecord]
    clinical_trials: EvidencePage[ClinicalTrialRecord]
    ranking: list[RankedEvidence]
    ranking_year: int = Field(ge=1900, le=9999)


class EvidenceRetrievalPipeline:
    """Retrieve both source pages concurrently and rank normalized records."""

    def __init__(
        self,
        *,
        pubmed: PubMedSearcher,
        clinical_trials: ClinicalTrialSearcher,
    ) -> None:
        self._pubmed = pubmed
        self._clinical_trials = clinical_trials

    async def run(
        self,
        pico: PICO,
        *,
        current_year: int,
        page_size: int = 20,
        condition_term: str | None = None,
        outcome_terms: tuple[str, ...] | None = None,
        direct_trial_comparison: bool = False,
    ) -> EvidenceRetrievalResult:
        """Execute a reproducible first-page retrieval for a validated PICO."""

        if current_year < 1900 or current_year > 9999:
            raise ValueError("current_year must be between 1900 and 9999")
        pubmed_query = build_pubmed_query(
            pico,
            condition_term=condition_term,
            outcome_terms=outcome_terms,
            page_size=page_size,
        )
        trial_query = build_trial_query(
            pico,
            condition_term=condition_term,
            direct_comparison=direct_trial_comparison,
            page_size=page_size,
        )
        pubmed_page, trial_page = await asyncio.gather(
            self._pubmed.search(pubmed_query),
            self._clinical_trials.search(trial_query),
        )
        return EvidenceRetrievalResult(
            pubmed=pubmed_page,
            clinical_trials=trial_page,
            ranking=rank_evidence(
                [*pubmed_page.records, *trial_page.records],
                pico,
                current_year=current_year,
            ),
            ranking_year=current_year,
        )
