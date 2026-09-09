from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.audio.decoder import AudioDecoder
from app.audio.normalizer import AudioNormalizer
from app.audio.validator import AudioValidator
from app.config.settings import Settings
from app.core.concurrency import InferenceLimiter
from app.main import create_app
from app.providers.detection.mock import MockLanguageDetectionProvider
from app.providers.transcription.mock import MockTranscriptionProvider
from app.providers.translation.mock import MockTranslationProvider
from app.services.language_service import LanguageService
from app.services.transcription_service import TranscriptionService
from app.services.translation_service import TranslationService
from app.api.dependencies.services import get_translation_service

@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        max_file_size_mb=1,
        max_audio_duration_seconds=30,
        max_translation_chars=250,
        max_inflight=1,
        inference_timeout_seconds=2,
        model_cache_dir=tmp_path / "models",
    )


@pytest.fixture
def translation_provider():
    return MockTranslationProvider()


@pytest.fixture
def detection_provider():
    return MockLanguageDetectionProvider()


@pytest.fixture
def transcription_provider():
    return MockTranscriptionProvider()


@pytest.fixture
def language_service():
    return LanguageService()


@pytest.fixture
def translation_service(
    settings,
    translation_provider,
    detection_provider,
    language_service,
):
    return TranslationService(
        settings=settings,
        language_service=language_service,
        translation_provider=translation_provider,
        detection_provider=detection_provider,
        inference_limiter=InferenceLimiter(
            max_inflight=settings.max_inflight,
        ),
    )


@pytest.fixture
def transcription_service(
    settings,
    transcription_provider,
):
    return TranscriptionService(
        settings=settings,
        validator=AudioValidator(settings),
        decoder=AudioDecoder(settings),
        normalizer=AudioNormalizer(),
        transcription_provider=transcription_provider,
        inference_limiter=InferenceLimiter(
            max_inflight=settings.max_inflight,
        ),
    )


@pytest.fixture
def client(
    settings,
    translation_provider,
    detection_provider,
    transcription_provider,
    language_service,
):
    app = create_app(settings)

    translation_service = TranslationService(
        settings=settings,
        language_service=language_service,
        translation_provider=translation_provider,
        detection_provider=detection_provider,
        inference_limiter=InferenceLimiter(
            max_inflight=settings.max_inflight,
        ),
    )

    transcription_service = TranscriptionService(
        settings=settings,
        validator=AudioValidator(settings),
        decoder=AudioDecoder(settings),
        normalizer=AudioNormalizer(),
        transcription_provider=transcription_provider,
        inference_limiter=InferenceLimiter(
            max_inflight=settings.max_inflight,
        ),
    )

    app.state.translation_provider = translation_provider
    app.state.detection_provider = detection_provider
    app.state.transcription_provider = transcription_provider
    app.state.language_service = language_service

    app.state.translation_service = translation_service
    app.state.transcription_service = transcription_service

    app.dependency_overrides[get_translation_service] = (
        lambda: translation_service
    )

    with TestClient(app) as test_client:
        yield test_client
