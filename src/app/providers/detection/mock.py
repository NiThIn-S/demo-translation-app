from app.schemas.common import LanguageDetectionResult


class MockLanguageDetectionProvider:
    """Deterministic language detector for tests."""

    backend_name = "mock"

    def __init__(
        self,
        language: str = "en",
        confidence: float = 1.0,
    ) -> None:
        self.language = language
        self.confidence = confidence

    async def detect(self, text: str) -> LanguageDetectionResult:
        return LanguageDetectionResult(
            language=self.language,
            confidence=self.confidence,
        )

    async def health(self) -> bool:
        return True
