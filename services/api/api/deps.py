from collections.abc import Iterator

import jwt
from common.db import session_scope
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from api.auth import AuthenticatedOperator, decode_access_token
from api.errors import APIError

_bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Iterator[Session]:
    with session_scope() as session:
        yield session


def current_operator(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthenticatedOperator:
    if credentials is None:
        raise APIError(401, "unauthorized", "Missing bearer token.")
    try:
        return decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise APIError(401, "unauthorized", "Invalid or expired token.") from exc
