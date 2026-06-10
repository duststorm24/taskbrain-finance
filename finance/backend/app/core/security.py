import base64
import hashlib
import hmac
import secrets
import struct
import time
from datetime import UTC, datetime
from urllib.parse import quote
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


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def make_totp_uri(secret: str, *, account_name: str, issuer: str = "TaskBrain Finance") -> str:
    label = f"{issuer}:{account_name}"
    return f"otpauth://totp/{quote(label)}?secret={secret}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"


def verify_totp_code(secret: str, code: str, *, valid_window: int = 1) -> bool:
    normalized_code = "".join(character for character in code if character.isdigit())
    if len(normalized_code) != 6:
        return False
    current_counter = int(time.time() // 30)
    for offset in range(-valid_window, valid_window + 1):
        expected = _totp_at(secret, current_counter + offset)
        if hmac.compare_digest(expected, normalized_code):
            return True
    return False


def _totp_at(secret: str, counter: int) -> str:
    key = _decode_totp_secret(secret)
    message = struct.pack(">Q", counter)
    digest = hmac.new(key, message, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{code_int % 1_000_000:06d}"


def _decode_totp_secret(secret: str) -> bytes:
    normalized = secret.strip().replace(" ", "").upper()
    padding = "=" * ((8 - len(normalized) % 8) % 8)
    return base64.b32decode(normalized + padding)


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
