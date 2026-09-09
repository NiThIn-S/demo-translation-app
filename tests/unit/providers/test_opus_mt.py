import pytest

from app.providers.translation.mock import MockTranslationProvider


@pytest.mark.asyncio
async def test_mock_translation_provider():
    provider = MockTranslationProvider()

    result = await provider.translate(
        "Hello",
        "en",
        "de",
    )

    assert result == "[translated] Hello"
    assert provider.supports_pair("en", "de")
    assert await provider.health()
