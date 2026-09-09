from fastapi import APIRouter, Depends

from app.api.dependencies.services import get_translation_service
from app.schemas.translation import (
    TranslationRequest,
    TranslationResponse,
)
from app.services.translation_service import TranslationService

router = APIRouter(tags=["translation"])


@router.post(
    "/translate",
    response_model=TranslationResponse,
)
async def translate(
    request: TranslationRequest,
    service: TranslationService = Depends(get_translation_service),
) -> TranslationResponse:
    return await service.translate(
        text=request.text,
        source_language=request.source_language,
        target_language=request.target_language,
    )
