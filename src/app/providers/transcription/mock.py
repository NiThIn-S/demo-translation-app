from app.audio.types import AudioInput
from app.providers.transcription.base import TranscriptionProvider
from app.schemas.transcription import TranscriptionProviderResult


class MockTranscriptionProvider(TranscriptionProvider):
    backend_name = "mock"

    def __init__(
        self,
        *,
        text: str = "mock transcription",
        language: str = "en",
        confidence: float = 1.0,
    ) -> None:
        self._text = text
        self._language = language
        self._confidence = confidence

    async def health(self) -> bool:
        return True

    async def transcribe(
        self,
        audio: AudioInput,
    ) -> TranscriptionProviderResult:
        return TranscriptionProviderResult(
            text=self._text,
            detected_language=self._language,
            confidence=self._confidence,
            backend=self.backend_name,
        )
