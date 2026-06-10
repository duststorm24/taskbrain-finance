from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import SESSION_COOKIE, current_user
from app.core.config import get_settings
from app.core.encryption import decrypt_secret, encrypt_secret
from app.core.security import generate_totp_secret, make_totp_uri, sign_session, utcnow, verify_password, verify_totp_code
from app.db.models import User
from app.db.repositories import create_user, get_user_by_email
from app.db.session import get_db
from app.schemas.auth import (
    AdminUserUpdateRequest,
    LoginRequest,
    MfaDisableRequest,
    MfaEnableRequest,
    MfaSetupResponse,
    MfaStatusResponse,
    RegisterRequest,
    SessionResponse,
    UserListResponse,
    UserResponse,
)


router = APIRouter()


@router.post("/register", response_model=SessionResponse)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> SessionResponse:
    if get_user_by_email(db, payload.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    user = create_user(
        db,
        email=payload.email,
        display_name=payload.display_name,
        password=payload.password,
        timezone=payload.timezone,
    )
    db.commit()
    _set_session_cookie(response, user.id)
    return _session_response(user)


@router.post("/login", response_model=SessionResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> SessionResponse:
    user = get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not active")
    if user.mfa_enabled:
        if not payload.totp_code:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticator code required")
        _verify_user_totp(user, payload.totp_code)

    user.last_login_at = utcnow()
    user.updated_at = utcnow()
    db.commit()
    _set_session_cookie(response, user.id)
    return _session_response(user)


@router.post("/logout")
def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@router.get("/session", response_model=SessionResponse)
def session(user: User = Depends(current_user)) -> SessionResponse:
    return _session_response(user)


@router.get("/mfa/status", response_model=MfaStatusResponse)
def mfa_status(user: User = Depends(current_user)) -> MfaStatusResponse:
    return MfaStatusResponse(enabled=bool(user.mfa_enabled), enabled_at=user.mfa_enabled_at)


@router.post("/mfa/setup", response_model=MfaSetupResponse)
def mfa_setup(user: User = Depends(current_user), db: Session = Depends(get_db)) -> MfaSetupResponse:
    secret = generate_totp_secret()
    user.mfa_totp_secret_encrypted = encrypt_secret(secret)
    user.mfa_enabled = 0
    user.mfa_enabled_at = None
    user.updated_at = utcnow()
    db.commit()
    return MfaSetupResponse(secret=secret, otpauth_uri=make_totp_uri(secret, account_name=user.email))


@router.post("/mfa/enable", response_model=MfaStatusResponse)
def mfa_enable(
    payload: MfaEnableRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> MfaStatusResponse:
    if not user.mfa_totp_secret_encrypted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start MFA setup before enabling MFA")
    _verify_user_totp(user, payload.totp_code)
    now = utcnow()
    user.mfa_enabled = 1
    user.mfa_enabled_at = now
    user.updated_at = now
    db.commit()
    return MfaStatusResponse(enabled=True, enabled_at=now)


@router.post("/mfa/disable", response_model=MfaStatusResponse)
def mfa_disable(
    payload: MfaDisableRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> MfaStatusResponse:
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    _verify_user_totp(user, payload.totp_code)
    user.mfa_enabled = 0
    user.mfa_totp_secret_encrypted = None
    user.mfa_enabled_at = None
    user.updated_at = utcnow()
    db.commit()
    return MfaStatusResponse(enabled=False, enabled_at=None)


@router.get("/users", response_model=UserListResponse)
def list_users(user: User = Depends(current_user), db: Session = Depends(get_db)) -> UserListResponse:
    _require_owner(user)
    rows = db.query(User).order_by(User.created_at.asc()).all()
    return UserListResponse(users=[_user_response(row) for row in rows])


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    payload: AdminUserUpdateRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    _require_owner(user)
    target = db.query(User).filter(User.id == user_id).one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    next_role = payload.role or target.role
    next_status = payload.status or target.status
    last_active_owner = target.role == "owner" and target.status == "active" and _active_owner_count(db) <= 1
    if last_active_owner and (next_role != "owner" or next_status != "active"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove the last active owner")
    if target.id == user.id and next_status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot disable your own account")

    target.role = next_role
    if target.status != next_status:
        target.status = next_status
        target.deactivated_at = utcnow() if next_status == "disabled" else None
    target.updated_at = utcnow()
    db.commit()
    db.refresh(target)
    return _user_response(target)


def _set_session_cookie(response: Response, user_id: str) -> None:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        sign_session(user_id),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=60 * 60 * 24 * 14,
    )


def _session_response(user: User) -> SessionResponse:
    return SessionResponse(user=_user_response(user))


def _user_response(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


def _verify_user_totp(user: User, code: str) -> None:
    if not user.mfa_totp_secret_encrypted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA is not configured")
    if not verify_totp_code(decrypt_secret(user.mfa_totp_secret_encrypted), code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authenticator code")


def _require_owner(user: User) -> None:
    if user.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner access required")


def _active_owner_count(db: Session) -> int:
    return db.query(User).filter(User.role == "owner", User.status == "active").count()
