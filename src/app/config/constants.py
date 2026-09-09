from typing import Final

HEALTH_STATUS_OK: Final[str] = "ok"

SUPPORTED_LANGUAGES: Final[dict[str, str]] = {
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
}

AUTO_LANGUAGE: Final[str] = "auto"

# These are the formats we expose as supported input formats.
#
# FFmpeg remains the authority for determining whether the actual uploaded
# content is valid audio. Extension/MIME checks alone are not trusted.
SUPPORTED_AUDIO_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {
        ".wav",
        ".mp3",
        ".m4a",
        ".webm",
        ".ogg",
        ".flac",
    }
)

SUPPORTED_AUDIO_MIME_TYPES: Final[frozenset[str]] = frozenset(
    {
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",
        "audio/x-m4a",
        "audio/webm",
        "audio/ogg",
        "audio/flac",
        "application/ogg",
    }
)

ASR_SAMPLE_RATE: Final[int] = 16_000
ASR_CHANNELS: Final[int] = 1
ASR_SAMPLE_WIDTH_BYTES: Final[int] = 2

ASR_SAMPLE_FORMAT: Final[str] = "s16le"

FFMPEG_BINARY: Final[str] = "ffmpeg"
FFPROBE_BINARY: Final[str] = "ffprobe"

FFMPEG_OUTPUT_FORMAT: Final[str] = "s16le"


SUPPORTED_TRANSLATION_PAIRS: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("en", "de"),
        ("en", "fr"),
        ("en", "es"),
        ("de", "en"),
        ("de", "fr"),
        ("de", "es"),
        ("fr", "en"),
        ("fr", "de"),
        ("fr", "es"),
        ("es", "en"),
        ("es", "de"),
        ("es", "fr"),
    }
)

ERROR_INVALID_AUDIO: Final[str] = "INVALID_AUDIO"
ERROR_UNSUPPORTED_AUDIO_FORMAT: Final[str] = "UNSUPPORTED_AUDIO_FORMAT"
ERROR_FILE_TOO_LARGE: Final[str] = "FILE_TOO_LARGE"
ERROR_AUDIO_TOO_LONG: Final[str] = "AUDIO_TOO_LONG"

ERROR_EMPTY_TEXT: Final[str] = "EMPTY_TEXT"
ERROR_TEXT_TOO_LONG: Final[str] = "TEXT_TOO_LONG"

ERROR_UNSUPPORTED_LANGUAGE: Final[str] = "UNSUPPORTED_LANGUAGE"
ERROR_UNSUPPORTED_TRANSLATION_PAIR: Final[str] = "UNSUPPORTED_TRANSLATION_PAIR"

ERROR_INFERENCE_BUSY: Final[str] = "INFERENCE_BUSY"
ERROR_INFERENCE_TIMEOUT: Final[str] = "INFERENCE_TIMEOUT"

ERROR_PROVIDER_UNAVAILABLE: Final[str] = "PROVIDER_UNAVAILABLE"
ERROR_MODEL_LOAD: Final[str] = "MODEL_LOAD_ERROR"


REQUEST_ID_HEADER: Final[str] = "X-Request-ID"
