"""Read side of the audit log (docs/GAPS.md item 7): was write-only until now."""

from common.models import AuditLog
from common.pagination import DEFAULT_LIMIT
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import get_db
from api.pagination import paginate
from api.schemas import AuditLogListOut

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


@router.get("", response_model=AuditLogListOut)
def list_audit_log(
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
    operator_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    session: Session = Depends(get_db),
) -> dict:
    stmt = select(AuditLog)
    if operator_id is not None:
        stmt = stmt.where(AuditLog.operator_id == operator_id)
    if resource_type is not None:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    if resource_id is not None:
        stmt = stmt.where(AuditLog.resource_id == resource_id)
    rows, next_cursor = paginate(session, stmt, AuditLog, AuditLog.created_at, limit, cursor)
    return {"data": rows, "next_cursor": next_cursor}
