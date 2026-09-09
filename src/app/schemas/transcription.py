from typing import Literal

from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    text: str
    duration_seconds: float
    detected_language: str | None = None
    confidence: float | None = None
    backend: str | None = None


class TranscriptionUpdateEvent(BaseModel):
    event: Literal["update"] = "update"
    state: Literal[
        "uploading",
        "uploaded",
        "busy",
        "processing",
        "completed",
        "error",
    ]
    msg: str


class TranscriptionDataEvent(BaseModel):
    event: Literal["data"] = "data"
    state: Literal["result"] = "result"
    transcript: str
    detected_language: str | None = None
    confidence: float | None = None
    backend: str | None = None


class TranscriptionErrorEvent(BaseModel):
    event: Literal["error"] = "error"
    state: Literal["error"] = "error"
    msg: str


class TranscriptionProviderResult(BaseModel):
    text: str
    detected_language: str | None = None
    confidence: float | None = None
    backend: str
