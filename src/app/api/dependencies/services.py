from fastapi import Request

from app.services.language_service import LanguageService
from app.services.transcription_service import TranscriptionService
from app.services.translation_service import TranslationService


def get_language_service(
    request: Request,
) -> LanguageService:
    return request.app.state.language_service


def get_translation_service(
    request: Request,
) -> TranslationService:
    return request.app.state.translation_service


def get_transcription_service(
    request: Request,
) -> TranscriptionService:
    return request.app.state.transcription_service
