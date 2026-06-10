from sqlalchemy.orm import Session

from app.core.security import hash_password, new_id, utcnow
from app.db.models import User


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.lower()).one_or_none()


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.query(User).filter(User.id == user_id).one_or_none()


def create_user(db: Session, *, email: str, display_name: str, password: str, timezone: str = "America/Chicago") -> User:
    now = utcnow()
    user = User(
        id=new_id(),
        email=email.lower(),
        display_name=display_name,
        password_hash=hash_password(password),
        timezone=timezone,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.flush()
    return user

