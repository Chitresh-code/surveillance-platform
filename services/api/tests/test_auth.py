from datetime import datetime, timezone

from fastapi.testclient import TestClient

from conftest import TEST_PASSWORD, TEST_USERNAME


def test_login_succeeds_with_correct_credentials(client):
    response = client.post("/api/v1/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_rejects_wrong_password(client):
    response = client.post("/api/v1/auth/login", json={"username": TEST_USERNAME, "password": "wrong"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_protected_endpoint_rejects_missing_token():
    from api.main import app

    unauthenticated = TestClient(app)
    response = unauthenticated.get("/api/v1/cameras")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_protected_endpoint_rejects_bad_token():
    from api.main import app

    unauthenticated = TestClient(app)
    response = unauthenticated.get("/api/v1/cameras", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_login_issues_a_refresh_token_alongside_the_access_token(client):
    response = client.post("/api/v1/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD})
    assert response.status_code == 200
    assert response.json()["refresh_token"]


def test_refresh_rotates_the_token_and_rejects_reuse(client):
    login = client.post("/api/v1/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD})
    old_refresh_token = login.json()["refresh_token"]

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh_token})
    assert refreshed.status_code == 200
    new_refresh_token = refreshed.json()["refresh_token"]
    assert new_refresh_token != old_refresh_token

    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh_token})
    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "unauthorized"

    still_good = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh_token})
    assert still_good.status_code == 200


def test_refresh_rejects_an_unknown_token(client):
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-real-refresh-token"})
    assert response.status_code == 401


def test_logout_revokes_the_refresh_token(client):
    login = client.post("/api/v1/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD})
    refresh_token = login.json()["refresh_token"]

    logout = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 204

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401


def test_login_rate_limits_after_too_many_failed_attempts(client, fake_redis):
    from api.ratelimit import MAX_ATTEMPTS

    username = "rate-limit-test-user"
    for _ in range(MAX_ATTEMPTS):
        pipe = fake_redis.pipeline()
        pipe.incr(f"login_rl:user:{username}")
        pipe.execute()

    response = client.post("/api/v1/auth/login", json={"username": username, "password": "wrong"})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"


def test_identity_get_writes_an_audit_log_entry(client):
    from common.db import session_scope
    from common.models import AuditLog, Identity

    now = datetime.now(timezone.utc)
    with session_scope() as session:
        session.add(Identity(id="idn_audit_test", first_seen=now, last_seen=now, embedding=[1.0, 0.0]))

    response = client.get("/api/v1/identities/idn_audit_test")
    assert response.status_code == 200

    with session_scope() as session:
        entries = (
            session.query(AuditLog)
            .filter_by(resource_type="identity", resource_id="idn_audit_test", action="identity.get")
            .all()
        )
    assert len(entries) == 1
