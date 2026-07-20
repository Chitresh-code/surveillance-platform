def test_create_list_and_deactivate_operator(client):
    create = client.post("/api/v1/operators", json={"username": "new-operator", "password": "a-strong-password"})
    assert create.status_code == 201
    body = create.json()
    assert body["username"] == "new-operator"
    assert body["is_active"] is True
    operator_id = body["id"]

    listed = client.get("/api/v1/operators")
    assert operator_id in [row["id"] for row in listed.json()["data"]]

    deactivate = client.delete(f"/api/v1/operators/{operator_id}")
    assert deactivate.status_code == 204

    listed_again = client.get("/api/v1/operators")
    row = next(r for r in listed_again.json()["data"] if r["id"] == operator_id)
    assert row["is_active"] is False


def test_create_operator_rejects_duplicate_username(client):
    client.post("/api/v1/operators", json={"username": "dupe-operator", "password": "a-strong-password"})
    response = client.post("/api/v1/operators", json={"username": "dupe-operator", "password": "another-password"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "operator_exists"


def test_deactivated_operator_cannot_log_in(client):
    client.post("/api/v1/operators", json={"username": "soon-deactivated", "password": "a-strong-password"})
    operator_id = next(
        r["id"] for r in client.get("/api/v1/operators").json()["data"] if r["username"] == "soon-deactivated"
    )
    client.delete(f"/api/v1/operators/{operator_id}")

    login = client.post(
        "/api/v1/auth/login", json={"username": "soon-deactivated", "password": "a-strong-password"}
    )
    assert login.status_code == 401
    assert login.json()["error"]["code"] == "invalid_credentials"


def test_deactivate_nonexistent_operator_404s(client):
    response = client.delete("/api/v1/operators/op_does_not_exist")
    assert response.status_code == 404
