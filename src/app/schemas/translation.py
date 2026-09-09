from pydantic import BaseModel, ConfigDict, Field, field_validator


class TranslationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    source_language: str = Field(default="auto", min_length=2, max_length=10)
    target_language: str = Field(min_length=2, max_length=10)

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("text must not be empty")
        return value

    @field_validator("source_language", "target_language")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        return value.strip().lower()


class TranslationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_text: str
    translated_text: str
    source_language: str
    target_language: str
