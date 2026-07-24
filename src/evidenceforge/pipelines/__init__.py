"""Clinical workflow pipelines."""

from evidenceforge.pipelines.coded_brief import CodedBriefPipeline
from evidenceforge.pipelines.evidence_retrieval import (
    EvidenceRetrievalPipeline,
    EvidenceRetrievalResult,
)
from evidenceforge.pipelines.synthesis_qa import SynthesisQAPipeline

__all__ = [
    "CodedBriefPipeline",
    "EvidenceRetrievalPipeline",
    "EvidenceRetrievalResult",
    "SynthesisQAPipeline",
]
