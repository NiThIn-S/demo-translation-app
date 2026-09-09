from abc import ABC, abstractmethod


class TranslationProvider(ABC):
    """Provider interface for machine translation."""

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return the provider/backend identifier."""

    @abstractmethod
    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        """Translate text from source language to target language."""

    @abstractmethod
    def supports_pair(
        self,
        source_language: str,
        target_language: str,
    ) -> bool:
        """Return whether the provider supports the requested language pair."""

    @abstractmethod
    async def health(self) -> bool:
        """Return whether the provider is available."""
