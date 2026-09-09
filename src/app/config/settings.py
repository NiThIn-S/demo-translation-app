from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration.
    Values can be supplied through environment variables or a local .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    app_name: str = Field(
        default="Translation & Transcription",
        validation_alias="APP_NAME",
    )
    app_version: str = Field(
        default="0.1.0",
        validation_alias="APP_VERSION",
    )
    environment: str = Field(
        default="development",
        validation_alias="ENVIRONMENT",
    )
    debug: bool = Field(
        default=False,
        validation_alias="DEBUG",
    )
    host: str = Field(
        default="0.0.0.0",
        validation_alias="HOST",
    )
    port: int = Field(
        default=8000,
        validation_alias="PORT",
        ge=1,
        le=65535,
    )
    log_level: str = Field(
        default="INFO",
        validation_alias="LOG_LEVEL",
    )
    max_file_size_mb: float = Field(
        default=5.0,
        validation_alias="MAX_FILE_SIZE_MB",
        gt=0,
    )
    max_audio_duration_seconds: float = Field(
        default=30.0,
        validation_alias="MAX_AUDIO_DURATION_SECONDS",
        gt=0,
    )
    max_translation_chars: int = Field(
        default=250,
        validation_alias="MAX_TRANSLATION_CHARS",
        gt=0,
    )
    max_inflight: int = Field(
        default=1,
        validation_alias="MAX_INFLIGHT",
        ge=1,
    )
    inference_timeout_seconds: float = Field(
        default=120.0,
        validation_alias="INFERENCE_TIMEOUT_SECONDS",
        gt=0,
    )

    translation_provider: str = Field(
        default="opus_mt",
        validation_alias="TRANSLATION_PROVIDER",
    )
    translation_model: str = Field(
        default="",
        validation_alias="TRANSLATION_MODEL",
    )

    asr_provider: str = Field(
        default="faster_whisper",
        validation_alias="ASR_PROVIDER",
    )
    asr_model: str = Field(
        default="tiny",
        validation_alias="ASR_MODEL",
    )
    asr_device: str = Field(
        default="cpu",
        validation_alias="ASR_DEVICE",
    )
    asr_compute_type: str = Field(
        default="int8",
        validation_alias="ASR_COMPUTE_TYPE",
    )

    detection_provider: str = Field(
        default="lingua",
        validation_alias="DETECTION_PROVIDER",
    )
    model_cache_dir: Path = Field(
        default=Path(".cache/models"),
        validation_alias="MODEL_CACHE_DIR",
    )

    @property
    def max_file_size_bytes(self) -> int:
        """Maximum accepted upload size in bytes."""
        return int(self.max_file_size_mb * 1024 * 1024)

    @property
    def environment_is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def normalized_log_level(self) -> str:
        return self.log_level.upper()

    @property
    def model_cache_path(self) -> Path:
        return self.model_cache_dir.expanduser().resolve()

    @field_validator(
        "translation_provider",
        "asr_provider",
        "detection_provider",
        mode="before",
    )
    @classmethod
    def normalize_provider_name(cls, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("provider name must be a string")

        return value.strip().lower()

    @field_validator("asr_device", "asr_compute_type", mode="before")
    @classmethod
    def normalize_asr_setting(cls, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("ASR setting must be a string")

        return value.strip().lower()

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("LOG_LEVEL must be a string")

        return value.strip().upper()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the application settings singleton.
    """
    return Settings()
