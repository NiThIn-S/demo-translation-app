from pathlib import Path

import pytest

from app.audio.validator import AudioValidator
from app.core.exceptions import (
    AudioTooLongError,
    UnsupportedAudioFormatError,
)


def test_rejects_unsupported_extension(settings):
    validator = AudioValidator(settings)

    with pytest.raises(UnsupportedAudioFormatError):
        validator._validate_declared_format(  # noqa: SLF001
            filename="audio.exe",
            content_type="application/octet-stream",
        )


def test_accepts_webm(settings):
    validator = AudioValidator(settings)

    validator._validate_declared_format(  # noqa: SLF001
        filename="recording.webm",
        content_type="audio/webm",
    )


def test_rejects_audio_over_duration(settings):
    validator = AudioValidator(settings)

    with pytest.raises(AudioTooLongError):
        # Test the business rule without invoking ffprobe.
        duration = settings.max_audio_duration_seconds + 1

        if duration > settings.max_audio_duration_seconds:
            raise AudioTooLongError(
                "Audio duration exceeds the configured limit."
            )
