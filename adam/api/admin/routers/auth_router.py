"""
Auth Router — /api/v2/auth/*
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from adam.api.admin.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from adam.api.admin.db import get_db
from adam.api.admin.dependencies import get_current_user
from adam.api.admin.models.user import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    UserResponse,
)

router = APIRouter(prefix="/api/v2/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    db = get_db()
    user = await db.fetch_one(
        "SELECT id, email, full_name, role, organization_id, password_hash, is_active FROM users WHERE email = $1",
        req.email,
    )

    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    access_token = create_access_token(
        str(user["id"]), user["email"], user["role"],
        str(user.get("organization_id") or ""),
    )

    raw_refresh, token_hash, expires_at = create_refresh_token()
    await db.execute(
        "INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at) VALUES ($1, $2, $3, $4)",
        str(uuid.uuid4()), str(user["id"]), token_hash, str(expires_at),
    )

    await db.execute(
        "UPDATE users SET last_login_at = $1 WHERE id = $2",
        str(datetime.now(timezone.utc)), str(user["id"]),
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        user=UserResponse(
            id=str(user["id"]),
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            organization_id=str(user.get("organization_id") or ""),
            is_active=bool(user.get("is_active", True)),
            created_at=str(user.get("created_at", "")),
        ),
    )


@router.post("/refresh")
async def refresh(req: RefreshRequest):
    db = get_db()
    token_hash = hash_refresh_token(req.refresh_token)

    token = await db.fetch_one(
        "SELECT user_id, expires_at, revoked FROM refresh_tokens WHERE token_hash = $1",
        token_hash,
    )

    if not token or token.get("revoked"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = await db.fetch_one(
        "SELECT id, email, role, organization_id FROM users WHERE id = $1",
        str(token["user_id"]),
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Revoke old refresh token
    await db.execute("UPDATE refresh_tokens SET revoked = true WHERE token_hash = $1", token_hash)

    # Issue new tokens
    access_token = create_access_token(
        str(user["id"]), user["email"], user["role"],
        str(user.get("organization_id") or ""),
    )
    raw_refresh, new_hash, expires_at = create_refresh_token()
    await db.execute(
        "INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at) VALUES ($1, $2, $3, $4)",
        str(uuid.uuid4()), str(user["id"]), new_hash, str(expires_at),
    )

    return {"access_token": access_token, "refresh_token": raw_refresh, "token_type": "bearer"}


@router.post("/logout")
async def logout(req: RefreshRequest):
    db = get_db()
    token_hash = hash_refresh_token(req.refresh_token)
    await db.execute("UPDATE refresh_tokens SET revoked = true WHERE token_hash = $1", token_hash)
    return {"status": "logged_out"}


@router.get("/me", response_model=UserResponse)
async def me(user=Depends(get_current_user)):
    return UserResponse(
        id=str(user["id"]),
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        organization_id=str(user.get("organization_id") or ""),
        is_active=bool(user.get("is_active", True)),
        created_at=str(user.get("created_at", "")),
    )


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, user=Depends(get_current_user)):
    db = get_db()
    full_user = await db.fetch_one("SELECT password_hash FROM users WHERE id = $1", str(user["id"]))
    if not full_user or not verify_password(req.current_password, full_user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    new_hash = hash_password(req.new_password)
    await db.execute("UPDATE users SET password_hash = $1, updated_at = $2 WHERE id = $3",
                     new_hash, str(datetime.now(timezone.utc)), str(user["id"]))
    return {"status": "password_changed"}
