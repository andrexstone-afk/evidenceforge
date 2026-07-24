"""Shared safe HTTP behavior for allowlisted terminology services."""

import asyncio
import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import httpx


class TerminologyClientError(RuntimeError):
    """Raised when a terminology service cannot return validated data."""


class SafeAsyncClient:
    def __init__(
        self,
        *,
        base_url: str,
        allowed_host: str,
        timeout_seconds: float = 10.0,
        retries: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or parsed.hostname != allowed_host:
            raise ValueError(f"Base URL must use HTTPS and host {allowed_host}")
        if retries < 0 or retries > 5:
            raise ValueError("Retries must be between 0 and 5")
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout_seconds,
            transport=transport,
            headers={"User-Agent": "EvidenceForge/0.1 (research prototype)"},
        )
        self._retries = retries

    async def _get_json(self, path: str, *, params: Mapping[str, str | int]) -> Any:
        for attempt in range(self._retries + 1):
            try:
                response = await self._client.get(path, params=params)
                response.raise_for_status()
                try:
                    return response.json()
                except json.JSONDecodeError as error:
                    raise TerminologyClientError(
                        "Terminology service returned malformed JSON"
                    ) from error
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as error:
                if attempt == self._retries or (
                    isinstance(error, httpx.HTTPStatusError)
                    and error.response.status_code < 500
                    and error.response.status_code != 429
                ):
                    raise TerminologyClientError("Terminology service request failed") from error
                retry_after = (
                    error.response.headers.get("Retry-After")
                    if isinstance(error, httpx.HTTPStatusError)
                    else None
                )
                delay = _retry_delay(retry_after=retry_after, attempt=attempt)
                await asyncio.sleep(delay)
        raise AssertionError("retry loop exhausted")

    async def aclose(self) -> None:
        await self._client.aclose()


def _retry_delay(*, retry_after: str | None, attempt: int) -> float:
    if retry_after is not None:
        try:
            return float(min(max(float(retry_after), 0.0), 30.0))
        except ValueError:
            pass
    return 0.25 * (2.0**attempt)
