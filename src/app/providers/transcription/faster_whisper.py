import asyncio
from typing import Any

from app.audio.types import AudioInput
from app.core.exceptions import ModelLoadError, ProviderUnavailableError
from app.core.logger import get_logger
from app.providers.transcription.base import TranscriptionProvider
from app.schemas.transcription import TranscriptionProviderResult

logger = get_logger(__name__)


class FasterWhisperProvider(TranscriptionProvider):
    """
    faster-whisper adapter using a lazy-loaded CTranslate2 model.

    Audio is expected to already be normalized to:
    - 16 kHz
    - mono
    - signed 16-bit PCM
    """

    backend_name = "faster_whisper"

    def __init__(
        self,
        *,
        model_name: str = "tiny",
        device: str = "cpu",
        compute_type: str = "int8",
        download_root: str | None = None,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._compute_type = compute_type
        self._download_root = download_root

        self._model: Any | None = None
        self._load_lock = asyncio.Lock()

    async def health(self) -> bool:
        try:
            await self._get_model()
            return True
        except (
            ModelLoadError,
            ProviderUnavailableError,
        ):
            return False

    async def transcribe(
        self,
        audio: AudioInput,
    ) -> TranscriptionProviderResult:
        model = await self._get_model()

        try:
            return await asyncio.to_thread(
                self._transcribe_sync,
                model,
                audio,
            )
        except Exception as exc:
            logger.exception(
                "transcription_inference_failed",
            )

            raise ProviderUnavailableError(
                "Transcription inference failed.",
            ) from exc

    async def _get_model(self) -> Any:
        if self._model is not None:
            return self._model

        async with self._load_lock:
            if self._model is not None:
                return self._model

            try:
                self._model = await asyncio.to_thread(
                    self._load_model_sync,
                )
            except Exception as exc:
                logger.exception(
                    "transcription_model_load_failed",
                    model=self._model_name,
                    device=self._device,
                    compute_type=self._compute_type,
                )

                raise ModelLoadError(
                    "Unable to load the transcription model.",
                ) from exc

        return self._model

    def _load_model_sync(self) -> Any:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ModelLoadError(
                "faster-whisper is not installed.",
            ) from exc

        kwargs: dict[str, Any] = {
            "device": self._device,
            "compute_type": self._compute_type,
        }

        if self._download_root:
            kwargs["download_root"] = self._download_root

        return WhisperModel(
            self._model_name,
            **kwargs,
        )

    @classmethod
    def _transcribe_sync(
        cls,
        model: Any,
        audio: AudioInput,
    ) -> TranscriptionProviderResult:
        try:
            import numpy as np
        except ImportError as exc:
            raise ProviderUnavailableError(
                "NumPy is required for transcription.",
            ) from exc

        samples = np.frombuffer(
            audio.pcm_bytes,
            dtype=np.int16,
        )

        if samples.size == 0:
            return TranscriptionProviderResult(
                text="",
                backend=cls.backend_name,
            )

        waveform = (
            samples.astype(np.float32) / 32768.0
        )

        segments, info = model.transcribe(
            waveform,
            language=None,
            beam_size=1,
            vad_filter=True,
        )

        text = " ".join(
            segment.text.strip()
            for segment in segments
            if segment.text.strip()
        ).strip()

        detected_language = getattr(
            info,
            "language",
            None,
        )

        confidence = getattr(
            info,
            "language_probability",
            None,
        )

        return TranscriptionProviderResult(
            text=text,
            detected_language=detected_language,
            confidence=(
                float(confidence)
                if confidence is not None
                else None
            ),
            backend=cls.backend_name,
        )
