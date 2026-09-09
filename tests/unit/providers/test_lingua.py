import pytest

from app.providers.detection.mock import MockLanguageDetectionProvider


@pytest.mark.asyncio
async def test_mock_language_detection():
    provider = MockLanguageDetectionProvider(
        language="en",
        confidence=0.99,
    )

    result = await provider.detect("Hello world")

    assert result.language == "en"
    assert result.confidence == 0.99
    assert await provider.health()
