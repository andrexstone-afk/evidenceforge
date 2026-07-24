"""Replaceable external evidence clients."""

from evidenceforge.clients.evidence.clinical_trials import ClinicalTrialsClient
from evidenceforge.clients.evidence.pubmed import PubMedClient

__all__ = ["ClinicalTrialsClient", "PubMedClient"]
