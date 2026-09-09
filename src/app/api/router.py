from fastapi import APIRouter

from app.api.v1.health_router import router as health_router
from app.api.v1.languages_router import router as languages_router
from app.api.v1.transcribe_router import router as transcribe_router
from app.api.v1.translate_router import router as translate_router

router = APIRouter()

router.include_router(health_router)
router.include_router(languages_router)
router.include_router(translate_router)
router.include_router(transcribe_router)
