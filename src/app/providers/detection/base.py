from abc import ABC, abstractmethod

from app.schemas.common import LanguageDetectionResult


class LanguageDetectionProvider(ABC):
    """Provider interface for language detection."""

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return the provider/backend identifier."""

    @abstractmethod
    async def detect(
        self,
        text: str,
    ) -> LanguageDetectionResult:
        """Detect the language of text."""

    @abstractmethod
    async def health(self) -> bool:
        """Return whether the provider is available."""
