from io import BytesIO

import pytest
from fastapi import UploadFile

from app.core.exceptions import FileTooLargeError


class FakeValidator:
    async def validate_file(
        self,
        path,
        **kwargs,
    ):
        return 1.5


class FakeDecoder:
    async def decode(self, path):
        return b"\x00\x00" * 16000


@pytest.mark.asyncio
async def test_transcription_service(
    transcription_service,
    monkeypatch,
):
    transcription_service._validator = FakeValidator()  # noqa: SLF001
    transcription_service._decoder = FakeDecoder()  # noqa: SLF001

    upload = UploadFile(
        filename="test.wav",
        file=BytesIO(b"fake audio"),
    )

    result = await transcription_service.transcribe(upload)

    assert result.text == "mock transcription"
    assert result.duration_seconds == 1.5


@pytest.mark.asyncio
async def test_upload_size_is_enforced(
    transcription_service,
    settings,
):
    upload = UploadFile(
        filename="large.wav",
        file=BytesIO(
            b"x" * (settings.max_file_size_bytes + 1)
        ),
    )

    with pytest.raises(FileTooLargeError):
        await transcription_service.transcribe(upload)
