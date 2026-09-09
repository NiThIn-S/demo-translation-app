import pytest

from app.audio.types import AudioInput
from app.providers.transcription.mock import MockTranscriptionProvider


@pytest.mark.asyncio
async def test_mock_transcription_provider():
    provider = MockTranscriptionProvider(
        text="hello world",
    )

    audio = AudioInput(
        pcm_bytes=b"\x00\x00" * 100,
        sample_rate=16000,
        channels=1,
        sample_width_bytes=2,
        duration_seconds=0.01,
    )

    result = await provider.transcribe(audio)

    assert result.text == "hello world"
    assert result.detected_language == "en"
    assert result.confidence == 1.0
    assert result.backend == "mock"
    assert await provider.health()
