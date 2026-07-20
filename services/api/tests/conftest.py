import os
import tempfile

import pytest


@pytest.fixture(scope="session", autouse=True)
def database_url() -> str:
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_file.close()
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file.name}"
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
    os.environ.setdefault("FRAME_STORE_DIR", tempfile.mkdtemp())
    yield os.environ["DATABASE_URL"]
    os.remove(db_file.name)


TEST_USERNAME = "test-operator"
TEST_PASSWORD = "test-password"


class FakeRedis:
    """In-memory stand-in for the rate limiter's Redis calls (docs/DECISIONS.md ADR-0013):
    no real Redis is available to the test suite, same reasoning as detection/reid's own
    _FakeRedis/_NoopRedis test doubles. Doesn't simulate key expiry — tests only exercise
    the attempt-counting/threshold logic, not the window-reset behavior.
    """

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def get(self, key: str) -> bytes | None:
        value = self._counts.get(key)
        return str(value).encode() if value is not None else None

    def ping(self) -> bool:
        return True

    def pipeline(self) -> "_FakePipeline":
        return _FakePipeline(self)


class _FakePipeline:
    def __init__(self, parent: FakeRedis) -> None:
        self._parent = parent
        self._incr_keys: list[str] = []

    def incr(self, key: str) -> "_FakePipeline":
        self._incr_keys.append(key)
        return self

    def expire(self, key: str, seconds: int, nx: bool = False) -> "_FakePipeline":
        return self

    def execute(self) -> None:
        for key in self._incr_keys:
            self._parent._counts[key] = self._parent._counts.get(key, 0) + 1
        self._incr_keys = []


@pytest.fixture(scope="session")
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture(scope="session")
def client(database_url, fake_redis):
    from common.db import make_engine, session_scope
    from common.ids import new_id
    from common.models import Base, Operator
    from fastapi.testclient import TestClient

    from api.auth import hash_password
    from api.deps import get_redis
    from api.main import app

    Base.metadata.create_all(make_engine(database_url))
    with session_scope() as session:
        session.add(Operator(id=new_id("op"), username=TEST_USERNAME, password_hash=hash_password(TEST_PASSWORD)))

    app.dependency_overrides[get_redis] = lambda: fake_redis
    test_client = TestClient(app)
    login = test_client.post("/api/v1/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD})
    test_client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    return test_client
