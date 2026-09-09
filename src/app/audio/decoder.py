import asyncio
from pathlib import Path

from app.config.constants import (
    ASR_CHANNELS,
    ASR_SAMPLE_RATE,
    FFMPEG_BINARY,
    FFMPEG_OUTPUT_FORMAT,
)
from app.config.settings import Settings
from app.core.exceptions import InvalidAudioError
from app.core.logger import get_logger

logger = get_logger(__name__)


class AudioDecoder:
    """Decode arbitrary supported audio into canonical PCM bytes."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def decode(
        self,
        path: Path,
    ) -> bytes:
        command = [
            FFMPEG_BINARY,
            "-v",
            "error",
            "-nostdin",
            "-i",
            str(path),
            "-vn",
            "-ac",
            str(ASR_CHANNELS),
            "-ar",
            str(ASR_SAMPLE_RATE),
            "-f",
            FFMPEG_OUTPUT_FORMAT,
            "-acodec",
            "pcm_s16le",
            "pipe:1",
        ]

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        timeout = max(
            self._settings.inference_timeout_seconds,
            self._settings.max_audio_duration_seconds * 2,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.communicate()

            raise InvalidAudioError(
                "Audio decoding timed out."
            ) from exc

        if process.returncode != 0:
            logger.warning(
                "ffmpeg_decode_failed",
                returncode=process.returncode,
                stderr=stderr.decode("utf-8", errors="replace")[:500],
            )
            raise InvalidAudioError(
                "Unable to decode the uploaded audio."
            )

        if not stdout:
            raise InvalidAudioError(
                "Decoded audio contains no samples."
            )

        return stdout
