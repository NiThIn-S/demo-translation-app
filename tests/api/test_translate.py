def test_translate(client):
    response = client.post(
        "/translate",
        json={
            "text": "Hello",
            "source_language": "en",
            "target_language": "de",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["source_text"] == "Hello"
    assert data["translated_text"] == "[translated] Hello"
    assert data["source_language"] == "en"
    assert data["target_language"] == "de"


def test_translate_rejects_empty_text(client):
    response = client.post(
        "/translate",
        json={
            "text": "",
            "source_language": "en",
            "target_language": "de",
        },
    )

    assert response.status_code == 422


def test_translate_rejects_unsupported_pair(client):
    response = client.post(
        "/translate",
        json={
            "text": "Hello",
            "source_language": "en",
            "target_language": "en",
        },
    )

    assert response.status_code == 400

    data = response.json()

    assert data["error"]["code"] == "UNSUPPORTED_TRANSLATION_PAIR"
