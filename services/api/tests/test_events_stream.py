def test_stream_sightings_rejects_missing_token():
    from fastapi.testclient import TestClient

    from api.main import app

    unauthenticated = TestClient(app)
    response = unauthenticated.get("/api/v1/events/stream")
    assert response.status_code == 400  # missing required query param


def test_stream_sightings_rejects_invalid_token():
    from fastapi.testclient import TestClient

    from api.main import app

    unauthenticated = TestClient(app)
    response = unauthenticated.get("/api/v1/events/stream", params={"token": "not-a-real-token"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
