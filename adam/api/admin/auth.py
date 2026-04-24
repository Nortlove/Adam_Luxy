"""
JWT Authentication + Password Hashing
========================================

Short-lived access tokens (15 min) + long-lived refresh tokens (7 days).
Passwords hashed with bcrypt via passlib.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

JWT_SECRET = os.environ.get("JWT_SECRET", "informativ-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with salt (bcrypt alternative without C dependency)."""
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}:{h.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    try:
        salt, stored_hash = password_hash.split(":")
        h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
        return hmac.compare_digest(h.hex(), stored_hash)
    except (ValueError, AttributeError):
        return False


def create_access_token(user_id: str, email: str, role: str, org_id: Optional[str] = None) -> str:
    """Create a short-lived JWT access token."""
    import json
    import base64

    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "org_id": org_id,
        "exp": now + ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "iat": now,
        "jti": uuid.uuid4().hex,
    }

    return _encode_jwt(payload)


def create_refresh_token() -> tuple[str, str, datetime]:
    """Create a refresh token. Returns (raw_token, token_hash, expires_at)."""
    raw_token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return raw_token, token_hash, expires_at


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a JWT access token."""
    try:
        payload = _decode_jwt(token)
        if payload is None:
            return None
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def hash_refresh_token(raw_token: str) -> str:
    """Hash a raw refresh token for database storage."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


# Simple JWT implementation without PyJWT dependency
def _encode_jwt(payload: Dict[str, Any]) -> str:
    import json
    import base64

    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{message}.{sig_b64}"


def _decode_jwt(token: str) -> Optional[Dict[str, Any]]:
    import json
    import base64

    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, sig_b64 = parts

        # Verify signature
        message = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).digest()
        actual_sig = base64.urlsafe_b64decode(sig_b64 + "==")
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        # Decode payload
        payload_json = base64.urlsafe_b64decode(payload_b64 + "==")
        return json.loads(payload_json)
    except Exception:
        return None
