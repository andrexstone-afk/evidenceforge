"""Async PubMed ESearch and EFetch client."""

from collections.abc import Iterable
from typing import Any

import httpx
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from pydantic import ValidationError

from evidenceforge.clients.evidence.base import EvidenceClientError, SafeEvidenceClient
from evidenceforge.models.evidence import (
    EvidencePage,
    EvidenceQuery,
    EvidenceSource,
    PubMedRecord,
    SearchMetadata,
)

PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
PUBMED_HOST = "eutils.ncbi.nlm.nih.gov"


class PubMedClient(SafeEvidenceClient):
    """Retrieve normalized PubMed records from fixed NCBI E-utility endpoints."""

    def __init__(
        self,
        *,
        email: str,
        api_key: str | None = None,
        base_url: str = PUBMED_BASE_URL,
        timeout_seconds: float = 10.0,
        retries: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
        min_interval_seconds: float | None = None,
    ) -> None:
        cleaned_email = email.strip()
        if "@" not in cleaned_email or " " in cleaned_email:
            raise ValueError("A valid NCBI contact email is required")
        self._email = cleaned_email
        self._api_key = api_key
        interval = (
            (0.11 if api_key else 0.34) if min_interval_seconds is None else min_interval_seconds
        )
        super().__init__(
            base_url=base_url,
            allowed_host=PUBMED_HOST,
            timeout_seconds=timeout_seconds,
            retries=retries,
            min_interval_seconds=interval,
            transport=transport,
        )

    async def search(self, query: EvidenceQuery, *, offset: int = 0) -> EvidencePage[PubMedRecord]:
        """Search PubMed and batch-fetch one normalized result page."""

        if query.source is not EvidenceSource.PUBMED:
            raise ValueError("PubMedClient requires a PubMed evidence query")
        if offset < 0:
            raise ValueError("PubMed offset must not be negative")
        params = self._common_params()
        params.update(
            {
                "db": "pubmed",
                "term": query.query,
                "retmode": "json",
                "retstart": offset,
                "retmax": query.page_size,
                "sort": "relevance",
            }
        )
        payload = await self._get_json("esearch.fcgi", params=params)
        try:
            search_result = payload["esearchresult"]
            total_count = int(search_result["count"])
            identifiers = [str(value) for value in search_result["idlist"]]
        except (KeyError, TypeError, ValueError) as error:
            raise EvidenceClientError(
                "PubMed ESearch returned an invalid response shape"
            ) from error
        records = await self._fetch(identifiers)
        return EvidencePage[PubMedRecord](
            records=records,
            metadata=SearchMetadata(
                source=EvidenceSource.PUBMED,
                query=query.query,
                filters=query.filters,
                total_count=total_count,
                page_size=query.page_size,
                offset=offset,
            ),
        )

    async def _fetch(self, identifiers: list[str]) -> list[PubMedRecord]:
        if not identifiers:
            return []
        params = self._common_params()
        params.update(
            {
                "db": "pubmed",
                "id": ",".join(identifiers),
                "retmode": "xml",
                "rettype": "abstract",
            }
        )
        xml = await self._get_text("efetch.fcgi", params=params)
        try:
            root = ElementTree.fromstring(xml)
            records = [_normalize_article(article) for article in root.findall("PubmedArticle")]
        except (
            DefusedXmlException,
            ElementTree.ParseError,
            ValidationError,
            ValueError,
        ) as error:
            raise EvidenceClientError("PubMed EFetch returned invalid citation data") from error
        returned_ids = {record.pmid for record in records}
        if len(records) != len(identifiers) or returned_ids != set(identifiers):
            raise EvidenceClientError("PubMed EFetch identifiers did not match ESearch results")
        return records

    def _common_params(self) -> dict[str, str | int | bool]:
        params: dict[str, str | int | bool] = {
            "tool": "evidenceforge",
            "email": self._email,
        }
        if self._api_key:
            params["api_key"] = self._api_key
        return params


def _normalize_article(article: Any) -> PubMedRecord:
    citation = article.find("MedlineCitation")
    article_data = citation.find("Article") if citation is not None else None
    if citation is None or article_data is None:
        raise ValueError("PubMed article is missing required citation fields")
    pmid = _required_text(citation.find("PMID"))
    title = _element_text(article_data.find("ArticleTitle"))
    journal = _required_text(article_data.find("Journal/Title"))
    publication_types = _texts(article_data.findall("PublicationTypeList/PublicationType"))
    return PubMedRecord(
        pmid=pmid,
        title=title,
        abstract=_abstract_text(article_data.findall("Abstract/AbstractText")),
        authors=_authors(article_data.findall("AuthorList/Author")),
        journal=journal,
        publication_date=_publication_date(article_data),
        publication_types=publication_types,
        doi=_doi(article),
        mesh_terms=_texts(citation.findall("MeshHeadingList/MeshHeading/DescriptorName")),
        languages=_texts(article_data.findall("Language")),
        is_retracted="Retracted Publication" in publication_types
        or _has_correction_type(citation, "RetractionIn"),
        is_correction="Published Erratum" in publication_types
        or _has_correction_type(citation, "ErratumFor", "CorrectedandRepublishedIn"),
        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
    )


def _required_text(element: Any) -> str:
    value = _element_text(element)
    if not value:
        raise ValueError("PubMed required text field is missing")
    return value


def _element_text(element: Any) -> str:
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def _texts(elements: Iterable[Any]) -> list[str]:
    return [value for element in elements if (value := _element_text(element))]


def _abstract_text(elements: list[Any]) -> str | None:
    sections: list[str] = []
    for element in elements:
        text = _element_text(element)
        if not text:
            continue
        label = element.attrib.get("Label")
        sections.append(f"{label}: {text}" if label else text)
    return "\n".join(sections) or None


def _authors(elements: list[Any]) -> list[str]:
    authors: list[str] = []
    for author in elements:
        collective = _element_text(author.find("CollectiveName"))
        if collective:
            authors.append(collective)
            continue
        name = " ".join(
            item
            for item in (
                _element_text(author.find("ForeName")),
                _element_text(author.find("LastName")),
            )
            if item
        )
        if name:
            authors.append(name)
    return authors


def _publication_date(article_data: Any) -> str | None:
    article_date = article_data.find("ArticleDate")
    if article_date is not None:
        parts = [_element_text(article_date.find(name)) for name in ("Year", "Month", "Day")]
        if parts[0]:
            return "-".join(
                part.zfill(2) if index else part for index, part in enumerate(parts) if part
            )
    pub_date = article_data.find("Journal/JournalIssue/PubDate")
    if pub_date is None:
        return None
    medline_date = _element_text(pub_date.find("MedlineDate"))
    if medline_date:
        return medline_date
    parts = [_element_text(pub_date.find(name)) for name in ("Year", "Month", "Day")]
    return "-".join(part for part in parts if part) or None


def _doi(article: Any) -> str | None:
    for identifier in article.findall("PubmedData/ArticleIdList/ArticleId"):
        if identifier.attrib.get("IdType") == "doi":
            return _element_text(identifier) or None
    return None


def _has_correction_type(citation: Any, *types: str) -> bool:
    return any(
        item.attrib.get("RefType") in types
        for item in citation.findall("CommentsCorrectionsList/CommentsCorrections")
    )
