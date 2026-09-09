import asyncio

from app.config.constants import SUPPORTED_LANGUAGES
from app.core.exceptions import ModelLoadError, ProviderUnavailableError
from app.core.logger import get_logger
from app.providers.detection.base import LanguageDetectionProvider
from app.schemas.common import LanguageDetectionResult

logger = get_logger(__name__)


class LinguaLanguageDetectionProvider(LanguageDetectionProvider):
    """
    Lingua-based language detector restricted to application-supported
    languages to keep resource usage small and predictable.
    """

    backend_name = "lingua"

    def __init__(self) -> None:
        self._detector = None
        self._load_lock = asyncio.Lock()

    async def health(self) -> bool:
        try:
            await self._get_detector()
            return True
        except (ModelLoadError, ProviderUnavailableError):
            return False

    async def detect(
        self,
        text: str,
    ) -> LanguageDetectionResult:
        detector = await self._get_detector()

        try:
            return await asyncio.to_thread(
                self._detect_sync,
                detector,
                text,
            )
        except Exception as exc:
            logger.exception("language_detection_failed")
            raise ProviderUnavailableError(
                "Language detection failed."
            ) from exc

    async def _get_detector(self):
        if self._detector is not None:
            return self._detector

        async with self._load_lock:
            if self._detector is not None:
                return self._detector

            try:
                self._detector = await asyncio.to_thread(
                    self._build_detector_sync,
                )
            except Exception as exc:
                logger.exception("language_detector_load_failed")
                raise ModelLoadError(
                    "Unable to initialize the language detector."
                ) from exc

        return self._detector

    @staticmethod
    def _build_detector_sync():
        try:
            from lingua import Language, LanguageDetectorBuilder
        except ImportError as exc:
            raise ModelLoadError(
                "Lingua language detector is not installed."
            ) from exc

        languages = {
            "en": Language.ENGLISH,
            "de": Language.GERMAN,
            "fr": Language.FRENCH,
            "es": Language.SPANISH,
        }

        configured_languages = [
            languages[code]
            for code in SUPPORTED_LANGUAGES
        ]

        return LanguageDetectorBuilder.from_languages(
            *configured_languages,
        ).build()

    @staticmethod
    def _detect_sync(
        detector,
        text: str,
    ) -> LanguageDetectionResult:
        from lingua import Language

        language = detector.detect_language_of(text)

        if language is None:
            raise ProviderUnavailableError(
                "Unable to detect the input language."
            )

        mapping = {
            Language.ENGLISH: "en",
            Language.GERMAN: "de",
            Language.FRENCH: "fr",
            Language.SPANISH: "es",
        }

        language_code = mapping.get(language)

        if language_code is None:
            raise ProviderUnavailableError(
                "Detected language is not supported."
            )

        # Lingua expects the text first and the Language second.
        confidence = detector.compute_language_confidence(
            text,
            language,
        )

        return LanguageDetectionResult(
            language=language_code,
            confidence=float(confidence),
        )
