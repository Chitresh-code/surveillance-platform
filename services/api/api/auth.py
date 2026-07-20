"""Password hashing and JWT issuance/verification for operator auth (docs/DECISIONS.md
ADR-0010), plus opaque refresh token generation/hashing (docs/DECISIONS.md ADR-0013).
"""

import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

ACCESS_TOKEN_TTL = timedelta(hours=12)
REFRESH_TOKEN_TTL = timedelta(days=7)
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


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    # ponytail: a fast hash, not bcrypt — this hashes a 256-bit random value, not a
    # low-entropy user password, so there's no brute-force risk to slow down against.
    return hashlib.sha256(token.encode()).hexdigest()
