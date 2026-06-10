from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


class EncryptionConfigError(RuntimeError):
    pass


def _fernet() -> Fernet:
    key = get_settings().token_encryption_key
    if not key or key == "replace-with-fernet-key":
        raise EncryptionConfigError("TASKBRAIN_FINANCE_TOKEN_ENCRYPTION_KEY is not configured")
    return Fernet(key.encode("utf-8"))


def encrypt_secret(value: str) -> str:
    if not value:
        raise ValueError("Cannot encrypt an empty secret")
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise EncryptionConfigError("Stored secret could not be decrypted") from exc

