"""Authentication: login, refresh, and TOTP 2FA enrolment."""
from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_totp_secret,
    totp_provisioning_uri,
    verify_password,
    verify_totp,
)
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active or user.is_deleted:
        raise HTTPException(status_code=403, detail="Account disabled")

    role_key = user.role.key
    requires_2fa = role_key in rbac.REQUIRE_2FA_ROLES

    # Owner/admin must complete 2FA if enrolled; enforce enrolment in production.
    if requires_2fa and user.totp_enabled:
        if not payload.totp_code:
            raise HTTPException(status_code=401, detail="2FA code required")
        if not verify_totp(user.totp_secret or "", payload.totp_code):
            raise HTTPException(status_code=401, detail="Invalid 2FA code")

    extra = {"role": role_key, "org": user.organization_id}
    return TokenResponse(
        access_token=create_access_token(str(user.id), extra),
        refresh_token=create_refresh_token(str(user.id)),
        requires_2fa=requires_2fa and not user.totp_enabled,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = int(data["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    extra = {"role": user.role.key, "org": user.organization_id}
    return TokenResponse(
        access_token=create_access_token(str(user.id), extra),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserOut)
def me(current: CurrentUser = Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=current.user.id,
        full_name=current.user.full_name,
        email=current.user.email,
        role=current.role_key,
        organization_id=current.organization_id,
        branch_ids=current.branch_ids,
        totp_enabled=current.user.totp_enabled,
        sees_all_branches=current.sees_all_branches,
    )


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
def setup_2fa(
    current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> TwoFactorSetupResponse:
    secret = generate_totp_secret()
    current.user.totp_secret = secret
    db.add(current.user)
    db.commit()
    return TwoFactorSetupResponse(
        secret=secret,
        provisioning_uri=totp_provisioning_uri(secret, current.user.email),
    )


@router.post("/2fa/verify")
def verify_2fa(
    payload: TwoFactorVerifyRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not current.user.totp_secret or not verify_totp(current.user.totp_secret, payload.code):
        raise HTTPException(status_code=400, detail="Invalid code")
    current.user.totp_enabled = True
    db.add(current.user)
    db.commit()
    return {"status": "2fa_enabled"}
