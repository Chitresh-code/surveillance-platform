def test_health_ok_without_a_token(client):
    from fastapi.testclient import TestClient

    from api.main import app

    unauthenticated = TestClient(app)
    response = unauthenticated.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
