#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import get_settings  # noqa: E402
from app.core.security import utcnow  # noqa: E402
from app.db.models import User  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.audit_log import log_event  # noqa: E402


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Disable stale non-owner TaskBrain Finance users.")
    parser.add_argument("--days", type=int, default=get_settings().inactive_user_disable_days)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cutoff = datetime.now(UTC) - timedelta(days=args.days)
    disabled: list[str] = []
    candidates: list[str] = []

    with SessionLocal() as db:
        users = db.query(User).filter(User.status == "active", User.role != "owner").all()
        for user in users:
            last_activity = parse_timestamp(user.last_login_at) or parse_timestamp(user.created_at)
            if last_activity and last_activity <= cutoff:
                candidates.append(user.email)
                if not args.dry_run:
                    user.status = "disabled"
                    user.deactivated_at = utcnow()
                    user.updated_at = utcnow()
                    log_event(
                        db,
                        action="user.auto_deprovisioned",
                        target_user_id=user.id,
                        metadata={"reason": "inactive", "inactive_days": args.days},
                    )
                    disabled.append(user.email)
        if not args.dry_run:
            db.commit()

    mode = "would disable" if args.dry_run else "disabled"
    print(f"{mode} {len(disabled) if not args.dry_run else len(candidates)} inactive non-owner user(s)")
    for email in disabled if not args.dry_run else candidates:
        print(f"- {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
