from fastapi import APIRouter, Depends

from app.api.dependencies.services import get_language_service
from app.schemas.common import LanguageInfo
from app.services.language_service import LanguageService

router = APIRouter(tags=["languages"])


@router.get(
    "/languages",
    response_model=list[LanguageInfo],
)
async def languages(
    service: LanguageService = Depends(get_language_service),
) -> list[LanguageInfo]:
    return [
        LanguageInfo(**language)
        for language in service.list_languages()
    ]
