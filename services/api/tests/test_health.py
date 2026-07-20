def test_health_ok_without_a_token(client):
    from fastapi.testclient import TestClient

    from api.main import app

    unauthenticated = TestClient(app)
    response = unauthenticated.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_reports_degraded_when_redis_is_unreachable(client, fake_redis):
    from fastapi.testclient import TestClient

    from api.deps import get_redis
    from api.main import app

    class _BrokenRedis:
        def ping(self):
            raise ConnectionError("redis unreachable")

    app.dependency_overrides[get_redis] = lambda: _BrokenRedis()
    try:
        unauthenticated = TestClient(app)
        response = unauthenticated.get("/health")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "degraded"
        assert body["checks"]["redis"] == "unreachable"
        assert body["checks"]["database"] == "ok"
    finally:
        # Restore the override the `client` fixture set up, so later tests in the
        # session (which reuse the same session-scoped `client`) still work.
        app.dependency_overrides[get_redis] = lambda: fake_redis
