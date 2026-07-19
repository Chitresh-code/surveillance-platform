"""Password hashing and JWT issuance/verification for operator auth (docs/DECISIONS.md ADR-0010)."""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

ACCESS_TOKEN_TTL = timedelta(hours=12)
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(operator_id: str, username: str) -> str:
    payload = {
        "sub": operator_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + ACCESS_TOKEN_TTL,
    }
    return jwt.encode(payload, os.environ["JWT_SECRET_KEY"], algorithm=JWT_ALGORITHM)


@dataclass
class AuthenticatedOperator:
    id: str
    username: str


def decode_access_token(token: str) -> AuthenticatedOperator:
    payload = jwt.decode(token, os.environ["JWT_SECRET_KEY"], algorithms=[JWT_ALGORITHM])
    return AuthenticatedOperator(id=payload["sub"], username=payload["username"])
