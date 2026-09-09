from app.config.constants import (
    SUPPORTED_LANGUAGES,
    SUPPORTED_TRANSLATION_PAIRS,
)
from app.core.exceptions import UnsupportedLanguageError


class LanguageService:
    """Business logic for supported languages and translation pairs."""

    def list_languages(self) -> list[dict[str, str]]:
        return [
            {"code": code, "name": name}
            for code, name in SUPPORTED_LANGUAGES.items()
        ]

    def normalize_language(self, language: str) -> str:
        normalized = language.strip().lower()

        if normalized not in SUPPORTED_LANGUAGES:
            raise UnsupportedLanguageError(
                f"Unsupported language: {language}",
                details={"language": language},
            )

        return normalized

    def is_supported(self, language: str) -> bool:
        return language.strip().lower() in SUPPORTED_LANGUAGES

    def supports_translation_pair(
        self,
        source_language: str,
        target_language: str,
    ) -> bool:
        return (
            source_language,
            target_language,
        ) in SUPPORTED_TRANSLATION_PAIRS
