import pytest

from app.core.exceptions import (
    EmptyTextError,
    TextTooLongError,
    UnsupportedLanguageError,
    UnsupportedTranslationPairError
)


@pytest.mark.asyncio
async def test_translate_text(
    translation_service,
):
    result = await translation_service.translate(
        text="Hello",
        source_language="en",
        target_language="de",
    )

    assert result.source_text == "Hello"
    assert result.translated_text == "[translated] Hello"
    assert result.source_language == "en"
    assert result.target_language == "de"


@pytest.mark.asyncio
async def test_auto_detects_source_language(
    translation_service,
):
    result = await translation_service.translate(
        text="Hello",
        source_language="auto",
        target_language="de",
    )

    assert result.source_language == "en"


@pytest.mark.asyncio
async def test_rejects_empty_text(
    translation_service,
):
    with pytest.raises(EmptyTextError):
        await translation_service.translate(
            text="   ",
            source_language="en",
            target_language="de",
        )


@pytest.mark.asyncio
async def test_rejects_text_over_limit(
    translation_service,
):
    with pytest.raises(TextTooLongError):
        await translation_service.translate(
            text="x" * 251,
            source_language="en",
            target_language="de",
        )


@pytest.mark.asyncio
async def test_rejects_same_language(
    translation_service,
):
    with pytest.raises(UnsupportedTranslationPairError):
        await translation_service.translate(
            text="Hello",
            source_language="en",
            target_language="en",
        )


@pytest.mark.asyncio
async def test_rejects_unsupported_pair(
    translation_service,
):
    with pytest.raises(UnsupportedLanguageError):
        await translation_service.translate(
            text="Hello",
            source_language="en",
            target_language="xx",
        )
