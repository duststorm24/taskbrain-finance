from datetime import UTC, datetime
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from itsdangerous import BadSignature, URLSafeSerializer

from app.core.config import get_settings


password_hasher = PasswordHasher()


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def new_id() -> str:
    return uuid4().hex


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(get_settings().session_secret, salt="taskbrain-finance-session")


def sign_session(user_id: str) -> str:
    return _serializer().dumps({"user_id": user_id})


def verify_session(token: str) -> str | None:
    try:
        payload = _serializer().loads(token)
    except BadSignature:
        return None
    user_id = payload.get("user_id")
    return user_id if isinstance(user_id, str) else None

