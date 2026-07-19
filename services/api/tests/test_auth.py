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
