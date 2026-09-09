from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    version: str

class LanguageInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=2, max_length=10)
    name: str

class LanguageDetectionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
