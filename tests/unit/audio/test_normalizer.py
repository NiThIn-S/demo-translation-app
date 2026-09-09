import pytest

from app.audio.normalizer import AudioNormalizer
from app.config.constants import (
    ASR_CHANNELS,
    ASR_SAMPLE_RATE,
    ASR_SAMPLE_WIDTH_BYTES,
)
from app.core.exceptions import InvalidAudioError


def test_normalizes_pcm():
    normalizer = AudioNormalizer()

    pcm = b"\x00\x00" * ASR_SAMPLE_RATE

    result = normalizer.normalize(
        pcm,
        duration_seconds=1.0,
    )

    assert result.pcm_bytes == pcm
    assert result.sample_rate == ASR_SAMPLE_RATE
    assert result.channels == ASR_CHANNELS
    assert result.sample_width_bytes == ASR_SAMPLE_WIDTH_BYTES


def test_rejects_empty_pcm():
    normalizer = AudioNormalizer()

    with pytest.raises(InvalidAudioError):
        normalizer.normalize(
            b"",
            duration_seconds=0,
        )


def test_rejects_incomplete_pcm_frame():
    normalizer = AudioNormalizer()

    with pytest.raises(InvalidAudioError):
        normalizer.normalize(
            b"\x00",
            duration_seconds=0.1,
        )
