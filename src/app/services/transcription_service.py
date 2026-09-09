import asyncio
import json
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import UploadFile

from app.audio.decoder import AudioDecoder
from app.audio.normalizer import AudioNormalizer
from app.audio.validator import AudioValidator
from app.config.settings import Settings
from app.core.concurrency import InferenceLimiter
from app.core.exceptions import FileTooLargeError, ProviderUnavailableError
from app.providers.transcription.base import TranscriptionProvider
from app.schemas.transcription import (
    TranscriptionDataEvent,
    TranscriptionErrorEvent,
    TranscriptionProviderResult,
    TranscriptionUpdateEvent,
)


class TranscriptionService:
    """Application-level orchestration for audio transcription."""

    def __init__(
        self,
        *,
        settings: Settings,
        validator: AudioValidator,
        decoder: AudioDecoder,
        normalizer: AudioNormalizer,
        transcription_provider: TranscriptionProvider,
        inference_limiter: InferenceLimiter,
    ) -> None:
        self._settings = settings
        self._validator = validator
        self._decoder = decoder
        self._normalizer = normalizer
        self._provider = transcription_provider
        self._limiter = inference_limiter

    async def stream_transcribe(
        self,
        upload: UploadFile,
    ) -> AsyncIterator[str]:
        temporary_path: Path | None = None

        try:
            yield self._event(
                TranscriptionUpdateEvent(
                    state="uploading",
                    msg="Uploading file",
                )
            )

            temporary_path = await self._save_upload(upload)

            yield self._event(
                TranscriptionUpdateEvent(
                    state="uploaded",
                    msg="File uploaded",
                )
            )

            duration = await self._validator.validate_file(
                temporary_path,
                filename=upload.filename,
                content_type=upload.content_type,
                size_bytes=temporary_path.stat().st_size,
            )

            # Retry the inference slot for streamed transcription.
            #
            # Attempt 1: immediately
            # Attempt 2: after 4 seconds
            # Attempt 3: after 8 seconds
            retry_delays = [0, 4, 8]

            for attempt, delay in enumerate(retry_delays):
                if delay:
                    yield self._event(
                        TranscriptionUpdateEvent(
                            state="busy",
                            msg=(
                                "Transcription model is busy. "
                                f"Retrying in {delay} seconds..."
                            ),
                        )
                    )

                    await asyncio.sleep(delay)

                try:
                    async with self._limiter.slot():
                        yield self._event(
                            TranscriptionUpdateEvent(
                                state="processing",
                                msg="Processing audio",
                            )
                        )

                        pcm_bytes = await self._decoder.decode(
                            temporary_path,
                        )

                        audio = self._normalizer.normalize(
                            pcm_bytes,
                            duration_seconds=duration,
                        )

                        result = await asyncio.wait_for(
                            self._provider.transcribe(audio),
                            timeout=(
                                self._settings
                                .inference_timeout_seconds
                            ),
                        )

                    break

                except ProviderUnavailableError:
                    if attempt == len(retry_delays) - 1:
                        raise

            yield self._event(
                TranscriptionUpdateEvent(
                    state="completed",
                    msg="Transcription completed",
                )
            )

            yield self._event(
                TranscriptionDataEvent(
                    transcript=result.text,
                    detected_language=result.detected_language,
                    confidence=result.confidence,
                    backend=result.backend,
                )
            )

        except asyncio.TimeoutError:
            yield self._event(
                TranscriptionErrorEvent(
                    msg="Transcription inference timed out.",
                )
            )

        except ProviderUnavailableError:
            yield self._event(
                TranscriptionErrorEvent(
                    msg=(
                        "Transcription model is still busy. "
                        "Please try again shortly."
                    ),
                )
            )

        except Exception as exc:
            from app.core.logger import get_logger

            logger = get_logger(__name__)

            logger.exception(
                "transcription_stream_failed",
            )

            yield self._event(
                TranscriptionErrorEvent(
                    msg=self._get_error_message(exc),
                )
            )

        finally:
            if temporary_path is not None:
                temporary_path.unlink(
                    missing_ok=True,
                )

            await upload.close()

    async def transcribe(
        self,
        upload: UploadFile,
    ):
        """
        Backwards-compatible non-streaming API.

        Keep this temporarily for existing unit tests or callers.
        """
        temporary_path: Path | None = None

        try:
            temporary_path = await self._save_upload(upload)

            duration = await self._validator.validate_file(
                temporary_path,
                filename=upload.filename,
                content_type=upload.content_type,
                size_bytes=temporary_path.stat().st_size,
            )

            pcm_bytes = await self._decoder.decode(
                temporary_path,
            )

            audio = self._normalizer.normalize(
                pcm_bytes,
                duration_seconds=duration,
            )

            async with self._limiter.slot():
                result = await asyncio.wait_for(
                    self._provider.transcribe(audio),
                    timeout=(
                        self._settings
                        .inference_timeout_seconds
                    ),
                )

            from app.schemas.transcription import (
                TranscriptionResponse,
            )

            return TranscriptionResponse(
                text=result.text,
                duration_seconds=duration,
                detected_language=result.detected_language,
                confidence=result.confidence,
                backend=result.backend,
            )

        except asyncio.TimeoutError as exc:
            from app.core.exceptions import (
                InferenceTimeoutError,
            )

            raise InferenceTimeoutError(
                "Transcription inference timed out.",
            ) from exc

        finally:
            if temporary_path is not None:
                temporary_path.unlink(
                    missing_ok=True,
                )

            await upload.close()

    async def _save_upload(
        self,
        upload: UploadFile,
    ) -> Path:
        """
        Stream the upload to disk while enforcing
        the configured size limit.
        """
        temporary_file = tempfile.NamedTemporaryFile(
            prefix="audio-",
            suffix=".upload",
            delete=False,
        )

        path = Path(temporary_file.name)

        total_bytes = 0
        chunk_size = 1024 * 1024

        try:
            with temporary_file:
                while True:
                    chunk = await upload.read(
                        chunk_size,
                    )

                    if not chunk:
                        break

                    total_bytes += len(chunk)

                    if (
                        total_bytes
                        > self._settings.max_file_size_bytes
                    ):
                        raise FileTooLargeError(
                            "Audio file exceeds the configured size limit.",
                            details={
                                "max_size_bytes": (
                                    self._settings
                                    .max_file_size_bytes
                                ),
                            },
                        )

                    temporary_file.write(chunk)

        except Exception:
            path.unlink(missing_ok=True)
            raise

        if total_bytes == 0:
            path.unlink(missing_ok=True)

            raise FileTooLargeError(
                "Uploaded audio file is empty.",
            )

        return path

    @staticmethod
    def _event(event) -> str:
        return (
            json.dumps(
                event.model_dump(
                    exclude_none=True,
                )
            )
            + "\n"
        )

    @staticmethod
    def _get_error_message(
        exc: Exception,
    ) -> str:
        message = str(exc).strip()

        if message:
            return message

        return "Transcription failed."
