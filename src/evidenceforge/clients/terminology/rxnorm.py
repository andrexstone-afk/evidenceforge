"""NLM RxNorm approximate-match client."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from evidenceforge.clients.terminology.base import SafeAsyncClient, TerminologyClientError
from evidenceforge.models.ontology import OntologyCandidate, OntologyName

RXNORM_URL = "https://rxnav.nlm.nih.gov/REST/approximateTerm.json"


class _RxCandidate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rxcui: str
    name: str | None = None
    score: float
    rank: int
    source: str


class _ApproximateGroup(BaseModel):
    candidate: list[_RxCandidate] = Field(default_factory=list)


class _RxResponse(BaseModel):
    approximateGroup: _ApproximateGroup


class RxNormClient(SafeAsyncClient):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            base_url="https://rxnav.nlm.nih.gov",
            allowed_host="rxnav.nlm.nih.gov",
            **kwargs,
        )

    async def search(self, term: str, *, limit: int = 5) -> list[OntologyCandidate]:
        payload = await self._get_json(
            "/REST/approximateTerm.json",
            params={"term": term, "maxEntries": limit, "option": 1},
        )
        try:
            parsed = _RxResponse.model_validate(payload)
        except ValidationError as error:
            raise TerminologyClientError("Invalid RxNorm response shape") from error

        unique: dict[str, _RxCandidate] = {}
        for candidate in parsed.approximateGroup.candidate:
            current = unique.get(candidate.rxcui)
            if current is None or (candidate.source == "RXNORM" and candidate.name):
                unique[candidate.rxcui] = candidate

        return [
            OntologyCandidate(
                ontology=OntologyName.RXNORM,
                code=candidate.rxcui,
                preferred_label=candidate.name or term,
                source_url=RXNORM_URL,
                source_rank=index,
                score=candidate.score,
            )
            for index, candidate in enumerate(unique.values(), start=1)
            if candidate.name
        ]
