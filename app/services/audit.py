from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog

async def record_audit(
    db: AsyncSession,
    *,
    action: str,
    resource_type: str,
    actor_user_id: UUID | None = None,
    project_id: UUID | None = None,
    resource_id: str | None = None,
    request_id: str | None = None,
    source_ip: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            project_id=project_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            source_ip=source_ip,
            details=details or {},
        )
    )