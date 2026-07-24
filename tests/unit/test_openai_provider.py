from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from evidenceforge.llm import OpenAIProvider
from evidenceforge.llm.mock import amd_pico
from evidenceforge.models import PICO


@pytest.mark.asyncio
async def test_openai_provider_records_validated_run_metadata() -> None:
    provider = OpenAIProvider(api_key="test-key", model="test-model")
    parse = AsyncMock(
        return_value=SimpleNamespace(
            output_parsed=amd_pico(),
            usage=SimpleNamespace(input_tokens=123, output_tokens=45),
        )
    )
    provider._client.responses.parse = parse  # type: ignore[method-assign]

    result = await provider.generate_structured(
        system_prompt="extract PICO",
        user_prompt=(
            "In neovascular AMD, does aflibercept versus ranibizumab improve visual acuity?"
        ),
        response_model=PICO,
    )

    assert result.intervention == "aflibercept"
    assert provider.last_run_metadata
    assert provider.last_run_metadata.provider == "openai"
    assert provider.last_run_metadata.model == "test-model"
    assert provider.last_run_metadata.input_tokens == 123
    assert provider.last_run_metadata.output_tokens == 45
    parse.assert_awaited_once_with(
        model="test-model",
        instructions="extract PICO",
        input="In neovascular AMD, does aflibercept versus ranibizumab improve visual acuity?",
        text_format=PICO,
        reasoning={"effort": "low"},
        store=False,
    )
    await provider.aclose()


@pytest.mark.asyncio
async def test_openai_provider_omits_reasoning_when_disabled() -> None:
    provider = OpenAIProvider(
        api_key="test-key",
        model="non-reasoning-model",
        reasoning_effort=None,
    )
    parse = AsyncMock(return_value=SimpleNamespace(output_parsed=amd_pico(), usage=None))
    provider._client.responses.parse = parse  # type: ignore[method-assign]

    await provider.generate_structured(
        system_prompt="extract PICO",
        user_prompt=(
            "In neovascular AMD, does aflibercept versus ranibizumab improve visual acuity?"
        ),
        response_model=PICO,
    )

    parse.assert_awaited_once_with(
        model="non-reasoning-model",
        instructions="extract PICO",
        input="In neovascular AMD, does aflibercept versus ranibizumab improve visual acuity?",
        text_format=PICO,
        store=False,
    )
    await provider.aclose()


def test_openai_provider_rejects_invalid_retry_count() -> None:
    with pytest.raises(ValueError, match="Retries"):
        OpenAIProvider(api_key="test-key", model="test-model", retries=-1)
