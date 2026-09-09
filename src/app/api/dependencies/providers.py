from fastapi import Request

from app.providers.detection.base import LanguageDetectionProvider
from app.providers.transcription.base import TranscriptionProvider
from app.providers.translation.base import TranslationProvider


def get_translation_provider(
    request: Request,
) -> TranslationProvider:
    return request.app.state.translation_provider


def get_transcription_provider(
    request: Request,
) -> TranscriptionProvider:
    return request.app.state.transcription_provider


def get_detection_provider(
    request: Request,
) -> LanguageDetectionProvider:
    return request.app.state.detection_provider
