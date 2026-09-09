import asyncio
import json
from pathlib import Path
from typing import Any

from app.config.constants import (
    FFMPEG_BINARY,
    FFPROBE_BINARY,
    SUPPORTED_AUDIO_EXTENSIONS,
    SUPPORTED_AUDIO_MIME_TYPES,
)
from app.config.settings import Settings
from app.core.exceptions import (
    AudioTooLongError,
    FileTooLargeError,
    InvalidAudioError,
    UnsupportedAudioFormatError,
)
from app.core.logger import get_logger

logger = get_logger(__name__)


class AudioValidator:
    """Validates uploaded audio using both metadata and FFmpeg tooling."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def validate_file(
        self,
        path: Path,
        *,
        filename: str | None = None,
        content_type: str | None = None,
        size_bytes: int | None = None,
    ) -> float:
        """
        Validate an audio file and return its duration in seconds.

        Filename and MIME type are treated as hints only. Actual media
        validation is performed through ffprobe/ffmpeg.
        """
        if size_bytes is not None:
            self._validate_size(size_bytes)

        self._validate_declared_format(
            filename=filename,
            content_type=content_type,
        )

        probe = await self._probe(path)

        self._validate_probe(path, probe)

        duration = await self._extract_duration(
            path,
            probe,
        )

        if duration > self._settings.max_audio_duration_seconds:
            raise AudioTooLongError(
                "Audio duration exceeds the configured limit.",
                details={
                    "duration_seconds": duration,
                    "max_duration_seconds": (
                        self._settings.max_audio_duration_seconds
                    ),
                },
            )

        return duration

    def _validate_size(self, size_bytes: int) -> None:
        if size_bytes > self._settings.max_file_size_bytes:
            raise FileTooLargeError(
                "Audio file exceeds the configured size limit.",
                details={
                    "size_bytes": size_bytes,
                    "max_size_bytes": self._settings.max_file_size_bytes,
                },
            )

    @staticmethod
    def _validate_declared_format(
        *,
        filename: str | None,
        content_type: str | None,
    ) -> None:
        extension = Path(filename).suffix.lower() if filename else ""

        normalized_mime = (
            content_type or ""
        ).split(";", 1)[0].strip().lower()

        extension_valid = extension in SUPPORTED_AUDIO_EXTENSIONS

        mime_valid = (
            not normalized_mime
            or normalized_mime in SUPPORTED_AUDIO_MIME_TYPES
        )

        if not extension_valid and not mime_valid:
            raise UnsupportedAudioFormatError(
                "Unsupported audio format.",
                details={
                    "filename": filename,
                    "content_type": content_type,
                },
            )

        if not extension_valid and not normalized_mime:
            raise UnsupportedAudioFormatError(
                "Audio format could not be determined.",
                details={
                    "filename": filename,
                },
            )

        if not mime_valid:
            raise UnsupportedAudioFormatError(
                "Unsupported audio MIME type.",
                details={
                    "content_type": content_type,
                },
            )

    async def _probe(self, path: Path) -> dict[str, Any]:
        command = [
            FFPROBE_BINARY,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,codec_name",
            "-of",
            "json",
            str(path),
        ]

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=10,
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.communicate()

            raise InvalidAudioError(
                "Audio validation timed out."
            ) from exc

        if process.returncode != 0:
            logger.warning(
                "ffprobe_rejected_audio",
                returncode=process.returncode,
                stderr=stderr.decode(
                    "utf-8",
                    errors="replace",
                )[:500],
            )

            raise InvalidAudioError(
                "The uploaded file is not a valid readable audio file."
            )

        try:
            result = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise InvalidAudioError(
                "Unable to parse audio metadata."
            ) from exc

        if not isinstance(result, dict):
            raise InvalidAudioError(
                "Invalid audio metadata."
            )

        return result

    @staticmethod
    def _validate_probe(
        path: Path,
        probe: dict[str, Any],
    ) -> None:
        streams = probe.get("streams")

        if not isinstance(streams, list):
            raise InvalidAudioError(
                "Audio file contains no readable streams."
            )

        audio_streams = [
            stream
            for stream in streams
            if isinstance(stream, dict)
            and stream.get("codec_type") == "audio"
        ]

        if not audio_streams:
            raise InvalidAudioError(
                "Uploaded file does not contain an audio stream."
            )

        if not path.is_file():
            raise InvalidAudioError(
                "Audio file is no longer available."
            )

    async def _extract_duration(
        self,
        path: Path,
        probe: dict[str, Any],
    ) -> float:
        """
        Extract duration from ffprobe metadata.

        Browser MediaRecorder files, especially WebM recordings, can
        legitimately have no container-level format.duration. In that
        case fall back to FFmpeg/ffprobe stream duration information.
        """
        format_info = probe.get("format")

        if isinstance(format_info, dict):
            raw_duration = format_info.get("duration")

            duration = self._parse_duration(raw_duration)

            if duration is not None:
                return duration

        # Some containers do not expose format.duration but do expose
        # duration on the individual audio stream.
        streams = probe.get("streams")

        if isinstance(streams, list):
            for stream in streams:
                if not isinstance(stream, dict):
                    continue

                if stream.get("codec_type") != "audio":
                    continue

                duration = self._parse_duration(
                    stream.get("duration")
                )

                if duration is not None:
                    return duration

        # Browser MediaRecorder WebM files can have neither format nor
        # stream duration. Fall back to decoding with FFmpeg and use
        # the decoded audio duration.
        return await self._extract_duration_with_ffmpeg(path)

    @staticmethod
    def _parse_duration(
        raw_duration: Any,
    ) -> float | None:
        if raw_duration is None:
            return None

        try:
            duration = float(raw_duration)
        except (TypeError, ValueError):
            return None

        if duration <= 0:
            return None

        if duration != duration or duration == float("inf"):
            return None

        return duration

    async def _extract_duration_with_ffmpeg(
        self,
        path: Path,
    ) -> float:
        """
        Determine duration by decoding the audio with FFmpeg.

        This is primarily a fallback for browser-generated recordings
        whose container metadata does not contain a duration.
        """
        command = [
            FFMPEG_BINARY,
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-f",
            "null",
            "-",
        ]

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=15,
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.communicate()

            raise InvalidAudioError(
                "Audio duration could not be determined."
            ) from exc

        if process.returncode != 0:
            logger.warning(
                "ffmpeg_duration_fallback_failed",
                returncode=process.returncode,
                stderr=stderr.decode(
                    "utf-8",
                    errors="replace",
                )[:500],
            )

            raise InvalidAudioError(
                "Audio duration could not be determined."
            )

        # FFmpeg's null muxer does not reliably provide the duration
        # through stdout, so use a second ffprobe invocation with
        # packet timestamps as the fallback.
        duration = await self._probe_duration_from_packets(path)

        if duration is None:
            raise InvalidAudioError(
                "Audio duration could not be determined."
            )

        return duration

    async def _probe_duration_from_packets(
        self,
        path: Path,
    ) -> float | None:
        """
        Read the final audio packet timestamp.

        This handles MediaRecorder WebM files that have no container
        duration metadata.
        """
        command = [
            FFPROBE_BINARY,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "packet=pts_time,dts_time,duration_time",
            "-of",
            "json",
            str(path),
        ]

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=15,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            return None

        if process.returncode != 0:
            logger.warning(
                "ffprobe_packet_duration_failed",
                returncode=process.returncode,
                stderr=stderr.decode(
                    "utf-8",
                    errors="replace",
                )[:500],
            )
            return None

        try:
            result = json.loads(stdout)
        except json.JSONDecodeError:
            return None

        packets = result.get("packets")

        if not isinstance(packets, list) or not packets:
            return None

        maximum_timestamp = 0.0

        for packet in packets:
            if not isinstance(packet, dict):
                continue

            pts = self._parse_non_negative_float(
                packet.get("pts_time")
            )

            dts = self._parse_non_negative_float(
                packet.get("dts_time")
            )

            duration = self._parse_non_negative_float(
                packet.get("duration_time")
            )

            timestamp = max(
                value
                for value in (pts, dts)
                if value is not None
            ) if (
                pts is not None or dts is not None
            ) else None

            if timestamp is None:
                continue

            packet_end = timestamp + (duration or 0.0)

            if packet_end > maximum_timestamp:
                maximum_timestamp = packet_end

        if maximum_timestamp <= 0:
            return None

        return maximum_timestamp

    @staticmethod
    def _parse_non_negative_float(
        value: Any,
    ) -> float | None:
        if value is None:
            return None

        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None

        if parsed < 0:
            return None

        if parsed != parsed or parsed == float("inf"):
            return None

        return parsed