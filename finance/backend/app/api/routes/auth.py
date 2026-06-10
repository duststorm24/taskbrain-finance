from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import SESSION_COOKIE, current_user
from app.core.security import sign_session, verify_password
from app.db.models import User
from app.db.repositories import create_user, get_user_by_email
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, SessionResponse, UserResponse


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
    response.set_cookie(
        SESSION_COOKIE,
        sign_session(user.id),
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 14,
    )
    return SessionResponse(user=UserResponse.model_validate(user))


@router.post("/login", response_model=SessionResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> SessionResponse:
    user = get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    response.set_cookie(
        SESSION_COOKIE,
        sign_session(user.id),
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 14,
    )
    return SessionResponse(user=UserResponse.model_validate(user))


@router.post("/logout")
def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@router.get("/session", response_model=SessionResponse)
def session(user: User = Depends(current_user)) -> SessionResponse:
    return SessionResponse(user=UserResponse.model_validate(user))

