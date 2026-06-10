from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.models import User
from app.db.session import get_db
from app.services.sync_service import sync_user_finances


router = APIRouter()


@router.post("")
def run_sync(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    sync_run = sync_user_finances(db, user.id, trigger="manual")
    db.commit()
    return {
        "id": sync_run.id,
        "status": sync_run.status,
        "accounts_synced": sync_run.accounts_synced,
        "transactions_added": sync_run.transactions_added,
        "transactions_modified": sync_run.transactions_modified,
        "transactions_removed": sync_run.transactions_removed,
        "started_at": sync_run.started_at,
        "finished_at": sync_run.finished_at,
        "metadata": sync_run.metadata_json,
    }
