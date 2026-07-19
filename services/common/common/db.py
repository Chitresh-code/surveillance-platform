"""DB engine/session helpers. DATABASE_URL comes from the environment (docs/CODING_STANDARDS.md §7)."""

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def make_engine(database_url: str | None = None):
    url = database_url or os.environ["DATABASE_URL"]
    return create_engine(url, pool_pre_ping=True)


_engine = None
_SessionLocal: sessionmaker | None = None


def _get_session_factory() -> sessionmaker:
    global _engine, _SessionLocal
    if _SessionLocal is None:
        _engine = make_engine()
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    session = _get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
