from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.security import new_id, utcnow
from app.db.models import AuditEvent


def log_event(
    db: Session,
    *,
    action: str,
    actor_user_id: str | None = None,
    target_user_id: str | None = None,
    outcome: str = "success",
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        id=new_id(),
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        action=action,
        outcome=outcome,
        metadata_json=json.dumps(metadata or {}, sort_keys=True),
        created_at=utcnow(),
    )
    db.add(event)
    return event
