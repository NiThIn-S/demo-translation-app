from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.audio.decoder import AudioDecoder
from app.audio.normalizer import AudioNormalizer
from app.audio.validator import AudioValidator
from app.config.settings import Settings
from app.core.concurrency import InferenceLimiter
from app.core.logger import get_logger
from app.providers.detection.lingua import LinguaLanguageDetectionProvider
from app.providers.transcription.faster_whisper import FasterWhisperProvider
from app.providers.translation.opus_mt import OpusMTTranslationProvider
from app.providers.translation.mock import MockTranslationProvider
from app.services.language_service import LanguageService
from app.services.transcription_service import TranscriptionService
from app.services.translation_service import TranslationService

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(
    app: FastAPI,
    settings: Settings,
) -> AsyncIterator[None]:
    """
    Construct application resources.

    ML models are intentionally lazy-loaded by their providers. This keeps
    application startup fast and prevents every worker from downloading or
    initializing models immediately.
    """
    settings.model_cache_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    translation_limiter = InferenceLimiter(
        max_inflight=settings.max_inflight,
    )

    transcription_limiter = InferenceLimiter(
        max_inflight=settings.max_inflight,
    )

    language_service = LanguageService()

    if settings.translation_provider == "mock":
        translation_provider = MockTranslationProvider()
    elif settings.translation_provider == "opus_mt":
        translation_provider = OpusMTTranslationProvider(
            model_name=settings.translation_model or None,
            cache_dir=str(settings.model_cache_path),
        )
    else:
        raise ValueError(
            f"Unsupported translation provider: "
            f"{settings.translation_provider}"
        )

    transcription_provider = FasterWhisperProvider(
        model_name=settings.asr_model,
        device=settings.asr_device,
        compute_type=settings.asr_compute_type,
        download_root=str(settings.model_cache_path),
    )

    detection_provider = LinguaLanguageDetectionProvider()

    audio_validator = AudioValidator(settings)
    audio_decoder = AudioDecoder(settings)
    audio_normalizer = AudioNormalizer()

    translation_service = TranslationService(
        settings=settings,
        language_service=language_service,
        translation_provider=translation_provider,
        detection_provider=detection_provider,
        inference_limiter=translation_limiter,
    )

    transcription_service = TranscriptionService(
        settings=settings,
        validator=audio_validator,
        decoder=audio_decoder,
        normalizer=audio_normalizer,
        transcription_provider=transcription_provider,
        inference_limiter=transcription_limiter,
    )

    app.state.settings = settings
    app.state.transcription_limiter = transcription_limiter
    app.state.translation_limiter = translation_limiter

    app.state.language_service = language_service
    app.state.translation_service = translation_service
    app.state.transcription_service = transcription_service

    app.state.translation_provider = translation_provider
    app.state.transcription_provider = transcription_provider
    app.state.detection_provider = detection_provider

    logger.info(
        "application_started",
        environment=settings.environment,
        max_inflight=settings.max_inflight,
        max_file_size_mb=settings.max_file_size_mb,
        max_audio_duration_seconds=(
            settings.max_audio_duration_seconds
        ),
        max_translation_chars=settings.max_translation_chars,
    )

    try:
        yield
    finally:
        logger.info("application_stopping")
