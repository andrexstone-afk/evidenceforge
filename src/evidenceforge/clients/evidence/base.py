"""Shared outbound-request safety and resilience for evidence sources."""

import asyncio
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from time import monotonic
from typing import Any
from urllib.parse import urlparse

import httpx

QueryValue = str | int | bool


class EvidenceClientError(RuntimeError):
    """Raised when an evidence source cannot return validated data."""


class SafeEvidenceClient:
    """HTTPS-only client restricted to one known evidence-source host."""

    def __init__(
        self,
        *,
        base_url: str,
        allowed_host: str,
        timeout_seconds: float = 10.0,
        retries: int = 2,
        min_interval_seconds: float = 0.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        parsed = urlparse(base_url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != allowed_host
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
        ):
            raise ValueError(f"Base URL must use HTTPS and host {allowed_host}")
        if retries < 0 or retries > 5:
            raise ValueError("Retries must be between 0 and 5")
        if min_interval_seconds < 0 or min_interval_seconds > 5:
            raise ValueError("Minimum request interval must be between 0 and 5 seconds")
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout_seconds,
            transport=transport,
            headers={"User-Agent": "EvidenceForge/0.1 (research prototype)"},
        )
        self._retries = retries
        self._min_interval_seconds = min_interval_seconds
        self._request_lock = asyncio.Lock()
        self._last_request_at: float | None = None

    async def _get_json(
        self,
        path: str,
        *,
        params: Mapping[str, QueryValue],
    ) -> Any:
        response = await self._request(path, params=params)
        try:
            return response.json()
        except json.JSONDecodeError as error:
            raise EvidenceClientError("Evidence source returned malformed JSON") from error

    async def _get_text(
        self,
        path: str,
        *,
        params: Mapping[str, QueryValue],
    ) -> str:
        return (await self._request(path, params=params)).text

    async def _request(
        self,
        path: str,
        *,
        params: Mapping[str, QueryValue],
    ) -> httpx.Response:
        parsed_path = urlparse(path)
        if parsed_path.scheme or parsed_path.netloc or path.startswith("//"):
            raise ValueError("Evidence client paths must be relative to the allowlisted host")
        for attempt in range(self._retries + 1):
            try:
                async with self._request_lock:
                    await self._pace_request()
                    try:
                        response = await self._client.get(path, params=params)
                    finally:
                        self._last_request_at = monotonic()
                response.raise_for_status()
                return response
            except (httpx.TransportError, httpx.HTTPStatusError) as error:
                if attempt == self._retries or not _is_retryable(error):
                    raise EvidenceClientError("Evidence source request failed") from error
                retry_after = (
                    error.response.headers.get("Retry-After")
                    if isinstance(error, httpx.HTTPStatusError)
                    else None
                )
                await asyncio.sleep(_retry_delay(retry_after=retry_after, attempt=attempt))
        raise AssertionError("retry loop exhausted")

    async def _pace_request(self) -> None:
        if self._last_request_at is None:
            return
        remaining = self._min_interval_seconds - (monotonic() - self._last_request_at)
        if remaining > 0:
            await asyncio.sleep(remaining)

    async def aclose(self) -> None:
        """Close the underlying connection pool."""

        await self._client.aclose()


def _is_retryable(error: httpx.HTTPError) -> bool:
    return not isinstance(error, httpx.HTTPStatusError) or (
        error.response.status_code == 429 or error.response.status_code >= 500
    )


def _retry_delay(
    *,
    retry_after: str | None,
    attempt: int,
    now: datetime | None = None,
) -> float:
    if retry_after is not None:
        try:
            return float(min(max(float(retry_after), 0.0), 30.0))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=UTC)
                reference = now or datetime.now(UTC)
                return float(min(max((retry_at - reference).total_seconds(), 0.0), 30.0))
            except (TypeError, ValueError, OverflowError):
                pass
    return 0.25 * (2.0**attempt)
