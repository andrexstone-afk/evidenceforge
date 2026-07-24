"""Async ClinicalTrials.gov API v2 client."""

from collections.abc import Mapping

import httpx
from pydantic import ValidationError

from evidenceforge.clients.evidence.base import EvidenceClientError, SafeEvidenceClient
from evidenceforge.models.evidence import (
    ClinicalTrialRecord,
    EvidencePage,
    EvidenceQuery,
    EvidenceSource,
    SearchMetadata,
    TrialLocation,
)

TRIALS_BASE_URL = "https://clinicaltrials.gov/api/v2/"
TRIALS_HOST = "clinicaltrials.gov"


class ClinicalTrialsClient(SafeEvidenceClient):
    """Retrieve normalized studies from the non-legacy API v2 endpoint."""

    def __init__(
        self,
        *,
        base_url: str = TRIALS_BASE_URL,
        timeout_seconds: float = 10.0,
        retries: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
        min_interval_seconds: float = 0.1,
    ) -> None:
        super().__init__(
            base_url=base_url,
            allowed_host=TRIALS_HOST,
            timeout_seconds=timeout_seconds,
            retries=retries,
            min_interval_seconds=min_interval_seconds,
            transport=transport,
        )

    async def search(
        self,
        query: EvidenceQuery,
        *,
        page_token: str | None = None,
    ) -> EvidencePage[ClinicalTrialRecord]:
        """Search one bounded page and normalize API v2 study modules."""

        if query.source is not EvidenceSource.CLINICAL_TRIALS:
            raise ValueError("ClinicalTrialsClient requires a ClinicalTrials.gov query")
        params: dict[str, str | int | bool] = {
            "query.term": query.query,
            "pageSize": query.page_size,
            "countTotal": True,
            "format": "json",
        }
        statuses = query.filters.get("overall_status")
        if statuses:
            params["filter.overallStatus"] = statuses.replace(",", "|")
        if page_token:
            params["pageToken"] = page_token
        payload = await self._get_json("studies", params=params)
        try:
            payload_object = _as_object(payload)
            total_count = _as_int(payload_object.get("totalCount"))
            studies = [
                _normalize_study(item) for item in _as_object_list(payload_object.get("studies"))
            ]
            next_page_token = _optional_string(payload_object.get("nextPageToken"))
        except (TypeError, ValueError, ValidationError) as error:
            raise EvidenceClientError(
                "ClinicalTrials.gov returned invalid API v2 study data"
            ) from error
        return EvidencePage[ClinicalTrialRecord](
            records=studies,
            metadata=SearchMetadata(
                source=EvidenceSource.CLINICAL_TRIALS,
                query=query.query,
                filters=query.filters,
                total_count=total_count,
                page_size=query.page_size,
                page_token=page_token,
                next_page_token=next_page_token,
            ),
        )


def _normalize_study(study: Mapping[str, object]) -> ClinicalTrialRecord:
    protocol = _child(study, "protocolSection")
    identification = _child(protocol, "identificationModule")
    status = _child(protocol, "statusModule")
    design = _child(protocol, "designModule")
    conditions = _child(protocol, "conditionsModule", required=False)
    arms = _child(protocol, "armsInterventionsModule", required=False)
    outcomes = _child(protocol, "outcomesModule", required=False)
    sponsors = _child(protocol, "sponsorCollaboratorsModule", required=False)
    contacts = _child(protocol, "contactsLocationsModule", required=False)
    nct_id = _required_string(identification.get("nctId"))
    return ClinicalTrialRecord(
        nct_id=nct_id,
        title=_required_string(
            identification.get("briefTitle") or identification.get("officialTitle")
        ),
        summary=_optional_string(
            _child(protocol, "descriptionModule", required=False).get("briefSummary")
        ),
        conditions=_string_list(conditions.get("conditions")),
        interventions=[
            value
            for item in _as_object_list(arms.get("interventions"))
            if (value := _optional_string(item.get("name")))
        ],
        outcomes=_outcome_measures(outcomes),
        study_type=_required_string(design.get("studyType")),
        phases=_string_list(design.get("phases")),
        enrollment=_enrollment(design),
        overall_status=_required_string(status.get("overallStatus")),
        sponsor=_optional_string(_child(sponsors, "leadSponsor", required=False).get("name")),
        start_date=_structured_date(status.get("startDateStruct")),
        completion_date=_structured_date(status.get("completionDateStruct")),
        locations=_locations(contacts.get("locations")),
        last_update_date=_structured_date(status.get("lastUpdatePostDateStruct")),
        has_results=_as_bool(study.get("hasResults")),
        url=f"https://clinicaltrials.gov/study/{nct_id}",
    )


def _outcome_measures(outcomes: Mapping[str, object]) -> list[str]:
    result: list[str] = []
    for key in ("primaryOutcomes", "secondaryOutcomes"):
        for item in _as_object_list(outcomes.get(key)):
            if measure := _optional_string(item.get("measure")):
                result.append(measure)
    return result


def _enrollment(design: Mapping[str, object]) -> int | None:
    enrollment = _child(design, "enrollmentInfo", required=False)
    count = enrollment.get("count")
    return None if count is None else _as_int(count)


def _locations(value: object) -> list[TrialLocation]:
    return [
        TrialLocation(
            facility=_optional_string(item.get("facility")),
            city=_optional_string(item.get("city")),
            state=_optional_string(item.get("state")),
            country=_optional_string(item.get("country")),
        )
        for item in _as_object_list(value)
    ]


def _structured_date(value: object) -> str | None:
    return _optional_string(_as_object(value).get("date")) if value is not None else None


def _child(
    parent: Mapping[str, object],
    key: str,
    *,
    required: bool = True,
) -> Mapping[str, object]:
    value = parent.get(key)
    if value is None and not required:
        return {}
    return _as_object(value)


def _as_object(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise TypeError("Expected a JSON object")
    return value


def _as_object_list(value: object) -> list[Mapping[str, object]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise TypeError("Expected a JSON array")
    return [_as_object(item) for item in value]


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TypeError("Expected an array of strings")
    return [item.strip() for item in value if item.strip()]


def _required_string(value: object) -> str:
    result = _optional_string(value)
    if result is None:
        raise ValueError("Required API v2 string is missing")
    return result


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("Expected a string")
    return value.strip() or None


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        raise TypeError("Expected an integer")
    return int(value) if isinstance(value, (int, str)) else _raise_type("integer")


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    raise TypeError("Expected a boolean")


def _raise_type(name: str) -> int:
    raise TypeError(f"Expected an {name}")
