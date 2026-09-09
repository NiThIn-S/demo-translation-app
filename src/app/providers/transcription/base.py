from abc import ABC, abstractmethod

from app.audio.types import AudioInput
from app.schemas.transcription import TranscriptionProviderResult


class TranscriptionProvider(ABC):
    backend_name: str

    @abstractmethod
    async def transcribe(
        self,
        audio: AudioInput,
    ) -> TranscriptionProviderResult:
        raise NotImplementedError

    @abstractmethod
    async def health(self) -> bool:
        raise NotImplementedError
