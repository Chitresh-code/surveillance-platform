import os
import tempfile

import pytest


@pytest.fixture(scope="session", autouse=True)
def database_url():
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_file.close()
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file.name}"
    yield os.environ["DATABASE_URL"]
    os.remove(db_file.name)


@pytest.fixture(scope="session", autouse=True)
def _create_schema(database_url):
    from common.db import make_engine
    from common.models import Base

    Base.metadata.create_all(make_engine(database_url))
