import asyncio

from app.config.constants import AUTO_LANGUAGE
from app.config.settings import Settings
from app.core.concurrency import InferenceLimiter
from app.core.exceptions import (
    EmptyTextError,
    InferenceTimeoutError,
    TextTooLongError,
    UnsupportedTranslationPairError,
)
from app.providers.detection.base import LanguageDetectionProvider
from app.providers.translation.base import TranslationProvider
from app.schemas.translation import TranslationResponse
from app.services.language_service import LanguageService


class TranslationService:
    """Application-level orchestration for translation."""

    def __init__(
        self,
        *,
        settings: Settings,
        language_service: LanguageService,
        translation_provider: TranslationProvider,
        detection_provider: LanguageDetectionProvider,
        inference_limiter: InferenceLimiter,
    ) -> None:
        self._settings = settings
        self._language_service = language_service
        self._translation_provider = translation_provider
        self._detection_provider = detection_provider
        self._limiter = inference_limiter

    async def translate(
        self,
        *,
        text: str,
        source_language: str,
        target_language: str,
    ) -> TranslationResponse:
        normalized_text = self._validate_text(text)

        normalized_target = self._language_service.normalize_language(
            target_language,
        )

        normalized_source = source_language.strip().lower()

        if normalized_source == AUTO_LANGUAGE:
            detection = await self._detection_provider.detect(
                normalized_text,
            )
            normalized_source = self._language_service.normalize_language(
                detection.language,
            )
        else:
            normalized_source = self._language_service.normalize_language(
                normalized_source,
            )

        if normalized_source == normalized_target:
            raise UnsupportedTranslationPairError(
                "Source and target languages must be different.",
                details={
                    "source_language": normalized_source,
                    "target_language": normalized_target,
                },
            )

        if not self._language_service.supports_translation_pair(
            normalized_source,
            normalized_target,
        ):
            raise UnsupportedTranslationPairError(
                "The requested translation pair is not supported.",
                details={
                    "source_language": normalized_source,
                    "target_language": normalized_target,
                },
            )

        if not self._translation_provider.supports_pair(
            normalized_source,
            normalized_target,
        ):
            raise UnsupportedTranslationPairError(
                "The configured translation provider does not support "
                "the requested language pair.",
                details={
                    "source_language": normalized_source,
                    "target_language": normalized_target,
                    "provider": self._translation_provider.backend_name,
                },
            )

        async with self._limiter.slot():
            try:
                translated_text = await asyncio.wait_for(
                    self._translation_provider.translate(
                        normalized_text,
                        normalized_source,
                        normalized_target,
                    ),
                    timeout=self._settings.inference_timeout_seconds,
                )
            except asyncio.TimeoutError as exc:
                raise InferenceTimeoutError(
                    "Translation inference timed out."
                ) from exc

        return TranslationResponse(
            source_text=normalized_text,
            translated_text=translated_text,
            source_language=normalized_source,
            target_language=normalized_target,
        )

    def _validate_text(self, text: str) -> str:
        normalized = text.strip()

        if not normalized:
            raise EmptyTextError(
                "Text must not be empty."
            )

        if len(normalized) > self._settings.max_translation_chars:
            raise TextTooLongError(
                "Text exceeds the configured character limit.",
                details={
                    "length": len(normalized),
                    "max_length": self._settings.max_translation_chars,
                },
            )

        return normalized
