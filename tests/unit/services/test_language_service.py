import pytest

from app.core.exceptions import UnsupportedLanguageError
from app.services.language_service import LanguageService


def test_list_languages():
    service = LanguageService()

    languages = service.list_languages()

    assert len(languages) == 4
    assert {"code": "en", "name": "English"} in languages
    assert {"code": "de", "name": "German"} in languages


def test_normalize_language():
    service = LanguageService()

    assert service.normalize_language(" EN ") == "en"


def test_rejects_unknown_language():
    service = LanguageService()

    with pytest.raises(UnsupportedLanguageError):
        service.normalize_language("xx")


def test_supported_translation_pair():
    service = LanguageService()

    assert service.supports_translation_pair("en", "de")
    assert not service.supports_translation_pair("en", "xx")
