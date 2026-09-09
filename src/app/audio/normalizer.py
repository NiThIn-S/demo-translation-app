from app.audio.types import AudioInput
from app.config.constants import (
    ASR_CHANNELS,
    ASR_SAMPLE_RATE,
    ASR_SAMPLE_WIDTH_BYTES,
)
from app.core.exceptions import InvalidAudioError


class AudioNormalizer:
    """
    Build the canonical AudioInput representation.

    AudioDecoder already asks FFmpeg to produce the target format, so this
    class verifies and packages the resulting PCM rather than performing
    another lossy conversion.
    """

    def normalize(
        self,
        pcm_bytes: bytes,
        *,
        duration_seconds: float,
    ) -> AudioInput:
        if not pcm_bytes:
            raise InvalidAudioError(
                "Audio contains no PCM samples."
            )

        bytes_per_second = (
            ASR_SAMPLE_RATE
            * ASR_CHANNELS
            * ASR_SAMPLE_WIDTH_BYTES
        )

        calculated_duration = len(pcm_bytes) / bytes_per_second

        if calculated_duration <= 0:
            raise InvalidAudioError(
                "Decoded audio duration is invalid."
            )

        # PCM frames must always be complete.
        frame_size = ASR_CHANNELS * ASR_SAMPLE_WIDTH_BYTES

        if len(pcm_bytes) % frame_size != 0:
            raise InvalidAudioError(
                "Decoded PCM data is incomplete."
            )

        return AudioInput(
            pcm_bytes=pcm_bytes,
            sample_rate=ASR_SAMPLE_RATE,
            channels=ASR_CHANNELS,
            sample_width_bytes=ASR_SAMPLE_WIDTH_BYTES,
            duration_seconds=duration_seconds,
        )
