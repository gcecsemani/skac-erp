"""Audit trail helper. Call from services on every create/update/delete."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def record_audit(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | int | None = None,
    actor_user_id: int | None = None,
    organization_id: int | None = None,
    branch_id: int | None = None,
    changes: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Persist an audit row. Does not commit — caller controls the transaction."""
    entry = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        actor_user_id=actor_user_id,
        organization_id=organization_id,
        branch_id=branch_id,
        changes=changes,
        ip_address=ip_address,
    )
    db.add(entry)
    return entry
