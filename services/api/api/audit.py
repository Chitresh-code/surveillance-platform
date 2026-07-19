"""Audit log writes for operator actions on identities (docs/GAPS.md item 7)."""

from common.ids import new_id
from common.models import AuditLog
from sqlalchemy.orm import Session

from api.auth import AuthenticatedOperator


def log_audit(session: Session, operator: AuthenticatedOperator, action: str, resource_type: str, resource_id: str) -> None:
    session.add(
        AuditLog(
            id=new_id("aud"),
            operator_id=operator.id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
        )
    )
