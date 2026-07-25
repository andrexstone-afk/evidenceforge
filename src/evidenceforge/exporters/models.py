"""Canonical, lossless export document for reviewed evidence briefs."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from evidenceforge.db.schemas import BriefPersistenceInput
from evidenceforge.models.ontology import OntologyName
from evidenceforge.models.qa import QAStatus


class ConditionMetatag(BaseModel):
    """Condition label with only service-validated terminology codes."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str
    icd10cm: str | None = None
    snomed: str | None = None


class DrugMetatag(BaseModel):
    """Intervention or comparator label with a service-validated RxNorm code."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str
    rxnorm: str


class ExportMetatags(BaseModel):
    """Stable YAML/JSON metadata contract for one exported brief."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    brief_id: str = Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    question: str
    clinical_domains: tuple[str, ...] = ()
    conditions: tuple[ConditionMetatag, ...] = ()
    interventions: tuple[DrugMetatag, ...] = ()
    comparators: tuple[DrugMetatag, ...] = ()
    outcomes: tuple[str, ...]
    evidence_sources: tuple[str, ...]
    qa_status: QAStatus
    generated_at: datetime
    prompt_versions: dict[str, str]


class BriefExportDocument(BaseModel):
    """Versioned export wrapper retaining the complete validated aggregate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    metatags: ExportMetatags
    aggregate: BriefPersistenceInput


def build_export_document(
    *,
    brief_id: str,
    aggregate: BriefPersistenceInput,
) -> BriefExportDocument:
    """Build lossless export metadata without inferring unvalidated codes or domains."""

    conditions: list[ConditionMetatag] = []
    interventions: list[DrugMetatag] = []
    comparators: list[DrugMetatag] = []
    intervention_term = aggregate.pico.intervention.casefold()
    comparator_term = aggregate.pico.comparator.casefold()
    for mapping in aggregate.mappings:
        selected = mapping.selected
        if selected is None:
            continue
        if mapping.ontology is OntologyName.ICD10CM:
            conditions.append(
                ConditionMetatag(
                    label=selected.preferred_label,
                    icd10cm=selected.code,
                )
            )
        elif mapping.ontology is OntologyName.RXNORM:
            concept = DrugMetatag(label=selected.preferred_label, rxnorm=selected.code)
            normalized_terms = {
                mapping.original_term.casefold(),
                mapping.normalized_term.casefold(),
            }
            if intervention_term in normalized_terms:
                interventions.append(concept)
            if comparator_term in normalized_terms:
                comparators.append(concept)

    result = aggregate.synthesis_qa
    prompt_versions = {
        "synthesis": result.original_draft.prompt_version,
        "qa_original": result.original_qa.prompt_version,
        "qa_final": result.final_qa.prompt_version,
    }
    if result.revision is not None:
        prompt_versions["revision"] = result.revision.prompt_version

    return BriefExportDocument(
        metatags=ExportMetatags(
            brief_id=brief_id,
            question=aggregate.question,
            conditions=tuple(conditions),
            interventions=tuple(interventions),
            comparators=tuple(comparators),
            outcomes=tuple(aggregate.pico.outcomes),
            evidence_sources=(
                aggregate.retrieval.pubmed.metadata.source.value,
                aggregate.retrieval.clinical_trials.metadata.source.value,
            ),
            qa_status=result.final_qa.status,
            generated_at=aggregate.created_at,
            prompt_versions=prompt_versions,
        ),
        aggregate=aggregate,
    )
