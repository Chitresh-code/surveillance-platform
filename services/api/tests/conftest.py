import os
import tempfile

import pytest


@pytest.fixture(scope="session", autouse=True)
def database_url() -> str:
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_file.close()
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file.name}"
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
    yield os.environ["DATABASE_URL"]
    os.remove(db_file.name)


TEST_USERNAME = "test-operator"
TEST_PASSWORD = "test-password"


@pytest.fixture(scope="session")
def client(database_url):
    from common.db import make_engine, session_scope
    from common.ids import new_id
    from common.models import Base, Operator
    from fastapi.testclient import TestClient

    from api.auth import hash_password
    from api.main import app

    Base.metadata.create_all(make_engine(database_url))
    with session_scope() as session:
        session.add(Operator(id=new_id("op"), username=TEST_USERNAME, password_hash=hash_password(TEST_PASSWORD)))

    test_client = TestClient(app)
    login = test_client.post("/api/v1/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD})
    test_client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    return test_client
