def test_languages(client):
    response = client.get("/languages")

    assert response.status_code == 200

    languages = response.json()

    assert len(languages) == 4
    assert languages[0]["code"] == "en"
