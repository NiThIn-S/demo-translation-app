import asyncio
from typing import Any

from app.config.constants import SUPPORTED_TRANSLATION_PAIRS
from app.core.exceptions import ModelLoadError, ProviderUnavailableError
from app.core.logger import get_logger
from app.providers.translation.base import TranslationProvider

logger = get_logger(__name__)


class OpusMTTranslationProvider(TranslationProvider):
    """
    Helsinki-NLP OPUS-MT adapter.

    Models are loaded lazily so application startup does not require
    downloading or initializing ML artifacts.
    """

    backend_name = "opus_mt"

    def __init__(
        self,
        *,
        model_name: str | None = None,
        cache_dir: str | None = None,
    ) -> None:
        self._configured_model_name = model_name
        self._cache_dir = cache_dir
        self._models: dict[tuple[str, str], Any] = {}
        self._load_lock = asyncio.Lock()

    def supports_pair(
        self,
        source_language: str,
        target_language: str,
    ) -> bool:
        return (
            source_language,
            target_language,
        ) in SUPPORTED_TRANSLATION_PAIRS

    async def health(self) -> bool:
        try:
            await self._ensure_dependencies()
            return True
        except (ImportError, ProviderUnavailableError):
            return False

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        if not self.supports_pair(source_language, target_language):
            raise ProviderUnavailableError(
                "Translation provider does not support this language pair.",
                details={
                    "source_language": source_language,
                    "target_language": target_language,
                },
            )

        tokenizer, model = await self._get_model(
            source_language,
            target_language,
        )

        try:
            return await asyncio.to_thread(
                self._translate_sync,
                tokenizer,
                model,
                text,
            )
        except Exception as exc:
            logger.exception(
                "translation_inference_failed",
                source_language=source_language,
                target_language=target_language,
            )
            raise ProviderUnavailableError(
                "Translation inference failed."
            ) from exc

    async def _get_model(
        self,
        source_language: str,
        target_language: str,
    ) -> tuple[Any, Any]:
        pair = (source_language, target_language)

        if pair in self._models:
            return self._models[pair]

        async with self._load_lock:
            if pair in self._models:
                return self._models[pair]

            try:
                tokenizer, model = await asyncio.to_thread(
                    self._load_model_sync,
                    source_language,
                    target_language,
                )
            except Exception as exc:
                logger.exception(
                    "translation_model_load_failed",
                    source_language=source_language,
                    target_language=target_language,
                )
                raise ModelLoadError(
                    "Unable to load the translation model."
                ) from exc

            self._models[pair] = (tokenizer, model)

        return self._models[pair]

    def _load_model_sync(
        self,
        source_language: str,
        target_language: str,
    ) -> tuple[Any, Any]:
        try:
            from transformers import (
                AutoModelForSeq2SeqLM,
                AutoTokenizer,
            )
        except ImportError as exc:
            raise ModelLoadError(
                "Transformers is not installed."
            ) from exc

        model_name = self._configured_model_name or (
            f"Helsinki-NLP/opus-mt-{source_language}-{target_language}"
        )

        kwargs: dict[str, Any] = {}

        if self._cache_dir:
            kwargs["cache_dir"] = self._cache_dir

        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            **kwargs,
        )

        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            **kwargs,
        )

        model.eval()

        return tokenizer, model

    @staticmethod
    def _translate_sync(
        tokenizer: Any,
        model: Any,
        text: str,
    ) -> str:
        import torch

        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
        )

        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=256,
            )

        return tokenizer.decode(
            output[0],
            skip_special_tokens=True,
        ).strip()

    @staticmethod
    async def _ensure_dependencies() -> None:
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
        except ImportError as exc:
            raise ProviderUnavailableError(
                "Translation dependencies are unavailable."
            ) from exc
