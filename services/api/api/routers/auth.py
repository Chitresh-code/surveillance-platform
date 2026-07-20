"""Auth endpoints: login, refresh, logout (docs/DECISIONS.md ADR-0010, ADR-0013)."""

from datetime import datetime, timezone

import redis
from common.ids import new_id
from common.models import Operator, RefreshToken
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth import (
    REFRESH_TOKEN_TTL,
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    hash_password,
    verify_password,
)
from api.deps import get_db, get_redis
from api.errors import APIError
from api.ratelimit import is_rate_limited, record_failed_attempt
from api.schemas import LoginRequest, LogoutRequest, RefreshRequest, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_tokens(session: Session, operator: Operator) -> dict:
    refresh_token = generate_refresh_token()
    session.add(
        RefreshToken(
            id=new_id("rft"),
            operator_id=operator.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.now(timezone.utc) + REFRESH_TOKEN_TTL,
        )
    )
    return {
        "access_token": create_access_token(operator.id, operator.username),
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/login", response_model=TokenOut)
def login(
    body: LoginRequest,
    request: Request,
    session: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> dict:
    client_host = request.client.host if request.client else "unknown"
    ip_key = f"login_rl:ip:{client_host}"
    user_key = f"login_rl:user:{body.username}"
    if is_rate_limited(redis_client, ip_key) or is_rate_limited(redis_client, user_key):
        raise APIError(429, "rate_limited", "Too many login attempts, try again later.")

    operator = session.execute(select(Operator).where(Operator.username == body.username)).scalar_one_or_none()
    if operator is None or not operator.is_active or not verify_password(body.password, operator.password_hash):
        record_failed_attempt(redis_client, ip_key)
        record_failed_attempt(redis_client, user_key)
        raise APIError(401, "invalid_credentials", "Incorrect username or password.")

    tokens = _issue_tokens(session, operator)
    session.flush()
    return tokens


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshRequest, session: Session = Depends(get_db)) -> dict:
    now = datetime.now(timezone.utc)
    stored = session.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(body.refresh_token),
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
    ).scalar_one_or_none()
    if stored is None:
        raise APIError(401, "unauthorized", "Invalid, expired, or already-used refresh token.")

    operator = session.get(Operator, stored.operator_id)
    if operator is None or not operator.is_active:
        raise APIError(401, "unauthorized", "Invalid, expired, or already-used refresh token.")

    # Rotation: reusing an already-exchanged refresh token fails the same way an
    # expired one does (docs/DECISIONS.md ADR-0013), since it's now revoked below.
    stored.revoked_at = now
    tokens = _issue_tokens(session, operator)
    session.flush()
    return tokens


@router.post("/logout", status_code=204)
def logout(body: LogoutRequest, session: Session = Depends(get_db)) -> None:
    stored = session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(body.refresh_token))
    ).scalar_one_or_none()
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(timezone.utc)
