import asyncio

import pytest

from app.audio.decoder import AudioDecoder
from app.core.exceptions import InvalidAudioError


@pytest.mark.asyncio
async def test_decoder_command_uses_ffmpeg(
    settings,
    monkeypatch,
    tmp_path,
):
    captured = {}

    class FakeProcess:
        returncode = 0

        async def communicate(self):
            return b"\x00\x00" * 100, b""

    async def fake_create_process(*command, **kwargs):
        captured["command"] = command
        return FakeProcess()

    monkeypatch.setattr(
        asyncio,
        "create_subprocess_exec",
        fake_create_process,
    )

    decoder = AudioDecoder(settings)

    result = await decoder.decode(
        tmp_path / "audio.webm",
    )

    assert result
    assert captured["command"][0] == "ffmpeg"
    assert "-nostdin" in captured["command"]
    assert "-ac" in captured["command"]
    assert "1" in captured["command"]
    assert "-ar" in captured["command"]
    assert "16000" in captured["command"]


@pytest.mark.asyncio
async def test_decoder_rejects_ffmpeg_failure(
    settings,
    monkeypatch,
    tmp_path,
):
    class FakeProcess:
        returncode = 1

        async def communicate(self):
            return b"", b"invalid audio"

    async def fake_create_process(*command, **kwargs):
        return FakeProcess()

    monkeypatch.setattr(
        asyncio,
        "create_subprocess_exec",
        fake_create_process,
    )

    decoder = AudioDecoder(settings)

    with pytest.raises(InvalidAudioError):
        await decoder.decode(
            tmp_path / "audio.wav",
        )
