from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AudioInput:
    """
    Canonical audio representation used by the transcription layer.

    pcm_bytes contains signed 16-bit little-endian PCM samples.
    """

    pcm_bytes: bytes
    sample_rate: int
    channels: int
    sample_width_bytes: int
    duration_seconds: float

    @property
    def sample_count(self) -> int:
        bytes_per_frame = self.channels * self.sample_width_bytes

        if bytes_per_frame == 0:
            return 0

        return len(self.pcm_bytes) // bytes_per_frame
