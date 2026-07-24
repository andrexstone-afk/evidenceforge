"""NLM Clinical Tables ICD-10-CM client."""

from typing import Any

from pydantic import TypeAdapter, ValidationError

from evidenceforge.clients.terminology.base import SafeAsyncClient, TerminologyClientError
from evidenceforge.models.ontology import OntologyCandidate, OntologyName

ICD10_URL = "https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search"


class ICD10CMClient(SafeAsyncClient):
    def __init__(
        self,
        *,
        base_url: str = "https://clinicaltables.nlm.nih.gov",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            base_url=base_url,
            allowed_host="clinicaltables.nlm.nih.gov",
            **kwargs,
        )

    async def search(self, term: str, *, limit: int = 10) -> list[OntologyCandidate]:
        payload = await self._get_json(
            "/api/icd10cm/v3/search",
            params={"terms": term, "sf": "code,name", "df": "code,name", "count": limit},
        )
        try:
            rows = TypeAdapter(list[list[str]]).validate_python(payload[3])
        except (IndexError, KeyError, TypeError, ValidationError) as error:
            raise TerminologyClientError("Invalid ICD-10-CM response shape") from error
        return [
            OntologyCandidate(
                ontology=OntologyName.ICD10CM,
                code=row[0],
                preferred_label=row[1],
                source_url=ICD10_URL,
                source_rank=index,
            )
            for index, row in enumerate(rows, start=1)
            if len(row) >= 2
        ]
