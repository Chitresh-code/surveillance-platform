def _insert_audit_entry(operator_id: str, action: str, resource_type: str, resource_id: str) -> str:
    from common.db import session_scope
    from common.ids import new_id
    from common.models import AuditLog

    entry_id = new_id("aud")
    with session_scope() as session:
        session.add(
            AuditLog(
                id=entry_id, operator_id=operator_id, action=action, resource_type=resource_type, resource_id=resource_id
            )
        )
    return entry_id


def _test_operator_id(client) -> str:
    from common.db import session_scope
    from common.models import Operator

    with session_scope() as session:
        return session.query(Operator).one().id


def test_list_audit_log_returns_entries(client):
    operator_id = _test_operator_id(client)
    entry_id = _insert_audit_entry(operator_id, "identity.get", "identity", "idn_1")

    response = client.get("/api/v1/audit-log")
    assert response.status_code == 200
    assert entry_id in [row["id"] for row in response.json()["data"]]


def test_list_audit_log_filters_by_resource(client):
    operator_id = _test_operator_id(client)
    match_id = _insert_audit_entry(operator_id, "identity.delete", "identity", "idn_only_this")
    _insert_audit_entry(operator_id, "identity.get", "identity", "idn_other")

    response = client.get("/api/v1/audit-log", params={"resource_id": "idn_only_this"})
    body = response.json()
    assert [row["id"] for row in body["data"]] == [match_id]


def test_list_audit_log_requires_a_token():
    from fastapi.testclient import TestClient

    from api.main import app

    unauthenticated = TestClient(app)
    response = unauthenticated.get("/api/v1/audit-log")
    assert response.status_code == 401
