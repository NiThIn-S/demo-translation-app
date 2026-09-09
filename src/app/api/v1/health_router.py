import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies.providers import (
    get_detection_provider,
    get_transcription_provider,
    get_translation_provider,
)
from app.config.constants import HEALTH_STATUS_OK
from app.config.settings import Settings, get_settings
from app.providers.detection.base import LanguageDetectionProvider
from app.providers.transcription.base import TranscriptionProvider
from app.providers.translation.base import TranslationProvider
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
)
async def health(
    settings: Settings = Depends(get_settings),
    translation_provider: TranslationProvider = Depends(
        get_translation_provider,
    ),
    transcription_provider: TranscriptionProvider = Depends(
        get_transcription_provider,
    ),
    detection_provider: LanguageDetectionProvider = Depends(
        get_detection_provider,
    ),
) -> HealthResponse:
    results = await asyncio.gather(
        translation_provider.health(),
        transcription_provider.health(),
        detection_provider.health(),
        return_exceptions=True,
    )

    if any(
        isinstance(result, Exception) or result is False
        for result in results
    ):
        raise HTTPException(
            status_code=503,
            detail="One or more providers are unavailable.",
        )

    return HealthResponse(
        status=HEALTH_STATUS_OK,
        version=settings.app_version,
    )
