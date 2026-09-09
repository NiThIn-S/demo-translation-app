class MockTranslationProvider:
    """Small deterministic provider used by tests and local development."""

    backend_name = "mock"

    def __init__(self, prefix: str = "[translated]") -> None:
        self.prefix = prefix

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        return f"{self.prefix} {text}"

    def supports_pair(
        self,
        source_language: str,
        target_language: str,
    ) -> bool:
        return source_language != target_language

    async def health(self) -> bool:
        return True
