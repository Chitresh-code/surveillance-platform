"""Operator account management (docs/GAPS.md item 2's remaining piece): create/list/deactivate
operators via the API instead of only the `api.create_operator` CLI script.
"""

from common.ids import new_id
from common.models import Operator
from common.pagination import DEFAULT_LIMIT
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth import hash_password
from api.deps import get_db
from api.errors import APIError
from api.pagination import paginate
from api.schemas import OperatorCreate, OperatorListOut, OperatorOut

router = APIRouter(prefix="/operators", tags=["operators"])


def _get_operator_or_404(session: Session, operator_id: str) -> Operator:
    operator = session.get(Operator, operator_id)
    if operator is None:
        raise APIError(404, "operator_not_found", f"No operator with id {operator_id}.")
    return operator


@router.post("", response_model=OperatorOut, status_code=201)
def create_operator(body: OperatorCreate, session: Session = Depends(get_db)) -> Operator:
    existing = session.execute(select(Operator).where(Operator.username == body.username)).scalar_one_or_none()
    if existing is not None:
        raise APIError(409, "operator_exists", f"An operator named {body.username!r} already exists.")
    operator = Operator(id=new_id("op"), username=body.username, password_hash=hash_password(body.password))
    session.add(operator)
    session.flush()
    return operator


@router.get("", response_model=OperatorListOut)
def list_operators(limit: int = DEFAULT_LIMIT, cursor: str | None = None, session: Session = Depends(get_db)) -> dict:
    rows, next_cursor = paginate(session, select(Operator), Operator, Operator.created_at, limit, cursor)
    return {"data": rows, "next_cursor": next_cursor}


@router.delete("/{operator_id}", status_code=204)
def deactivate_operator(operator_id: str, session: Session = Depends(get_db)) -> None:
    # ponytail: deactivation only, not a hard delete — audit_log rows carry a
    # not-null FK to operator_id, and a deactivated operator's *past* actions
    # should stay attributable. An existing access token isn't revoked by this
    # (ADR-0010: no per-request DB round-trip), it just can't be renewed —
    # bounded by the access token's own TTL, or immediately once ADR-0013's
    # refresh token is also revoked.
    operator = _get_operator_or_404(session, operator_id)
    operator.is_active = False
