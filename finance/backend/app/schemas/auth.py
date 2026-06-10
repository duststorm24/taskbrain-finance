from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=256)
    timezone: str = "America/Chicago"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    totp_code: str | None = Field(default=None, min_length=6, max_length=16)


class MfaEnableRequest(BaseModel):
    totp_code: str = Field(min_length=6, max_length=16)


class MfaDisableRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)
    totp_code: str = Field(min_length=6, max_length=16)


class MfaSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str


class MfaStatusResponse(BaseModel):
    enabled: bool
    enabled_at: str | None = None


class AdminUserUpdateRequest(BaseModel):
    role: str | None = Field(default=None, pattern="^(owner|member)$")
    status: str | None = Field(default=None, pattern="^(active|disabled)$")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    display_name: str
    timezone: str
    role: str
    status: str
    mfa_enabled: bool
    created_at: str
    last_login_at: str | None
    deactivated_at: str | None


class SessionResponse(BaseModel):
    user: UserResponse


class UserListResponse(BaseModel):
    users: list[UserResponse]
