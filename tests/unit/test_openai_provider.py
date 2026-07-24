from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from evidenceforge.llm import OpenAIProvider
from evidenceforge.llm.mock import amd_pico
from evidenceforge.models import PICO


@pytest.mark.asyncio
async def test_openai_provider_records_validated_run_metadata() -> None:
    provider = OpenAIProvider(api_key="test-key", model="test-model")
    provider._client.responses.parse = AsyncMock(  # type: ignore[method-assign]
        return_value=SimpleNamespace(
            output_parsed=amd_pico(),
            usage=SimpleNamespace(input_tokens=123, output_tokens=45),
        )
    )

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
