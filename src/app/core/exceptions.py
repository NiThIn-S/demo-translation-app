from typing import Any

class AppError(Exception):
    """Base exception for expected application errors."""

    code = "APPLICATION_ERROR"
    status_code = 500

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

class InvalidAudioError(AppError):
    code = "INVALID_AUDIO"
    status_code = 400

class UnsupportedAudioFormatError(AppError):
    code = "UNSUPPORTED_AUDIO_FORMAT"
    status_code = 415

class FileTooLargeError(AppError):
    code = "FILE_TOO_LARGE"
    status_code = 413

class AudioTooLongError(AppError):
    code = "AUDIO_TOO_LONG"
    status_code = 413

class EmptyTextError(AppError):
    code = "EMPTY_TEXT"
    status_code = 400

class TextTooLongError(AppError):
    code = "TEXT_TOO_LONG"
    status_code = 413

class UnsupportedLanguageError(AppError):
    code = "UNSUPPORTED_LANGUAGE"
    status_code = 400

class UnsupportedTranslationPairError(AppError):
    code = "UNSUPPORTED_TRANSLATION_PAIR"
    status_code = 400

class InferenceBusyError(AppError):
    code = "INFERENCE_BUSY"
    status_code = 429

class InferenceTimeoutError(AppError):
    code = "INFERENCE_TIMEOUT"
    status_code = 504

class ProviderUnavailableError(AppError):
    code = "PROVIDER_UNAVAILABLE"
    status_code = 503

class ModelLoadError(AppError):
    code = "MODEL_LOAD_ERROR"
    status_code = 503
