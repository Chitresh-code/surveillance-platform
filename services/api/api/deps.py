from collections.abc import Iterator

from common.db import session_scope
from sqlalchemy.orm import Session


def get_db() -> Iterator[Session]:
    with session_scope() as session:
        yield session
