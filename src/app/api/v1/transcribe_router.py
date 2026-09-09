from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse

from app.api.dependencies.services import (
    get_transcription_service,
)
from app.services.transcription_service import (
    TranscriptionService,
)

router = APIRouter(tags=["transcription"])


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    service: TranscriptionService = Depends(
        get_transcription_service,
    ),
) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[str]:
        async for event in service.stream_transcribe(
            file,
        ):
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
