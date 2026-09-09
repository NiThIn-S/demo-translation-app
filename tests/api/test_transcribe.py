def test_transcribe(client, monkeypatch):
    from app.schemas.transcription import TranscriptionProviderResult

    async def fake_validate_file(*args, **kwargs):
        return 2.0

    async def fake_decode(*args, **kwargs):
        return b"\x00\x00" * 16000

    async def fake_provider_transcribe(audio):
        return TranscriptionProviderResult(
            text="hello world",
            detected_language="en",
            confidence=0.99,
            backend="mock",
        )

    monkeypatch.setattr(
        client.app.state.transcription_service._validator,
        "validate_file",
        fake_validate_file,
    )

    monkeypatch.setattr(
        client.app.state.transcription_service._decoder,
        "decode",
        fake_decode,
    )

    monkeypatch.setattr(
        client.app.state.transcription_service._provider,
        "transcribe",
        fake_provider_transcribe,
    )

    response = client.post(
        "/transcribe",
        files={
            "file": (
                "test.wav",
                b"fake audio",
                "audio/wav",
            )
        },
    )
    assert response.status_code == 200

    lines = [
        line
        for line in response.text.splitlines()
        if line.strip()
    ]

    assert any('"state": "uploaded"' in line for line in lines)
    assert any('"state": "processing"' in line for line in lines)
    assert any('"state": "completed"' in line for line in lines)
    assert any('"transcript": "hello world"' in line for line in lines)


def test_transcribe_requires_file(client):
    response = client.post("/transcribe")

    assert response.status_code == 422
