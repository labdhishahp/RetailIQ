"""Password hashing and JWT issuing/verification.

Uses PBKDF2-HMAC-SHA256 from the standard library rather than bcrypt so the
backend has no binary wheel dependency (it must run on a serverless runtime).
"""

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings

_ITERATIONS = 240_000
_ALGO = "pbkdf2_sha256"

# Generated once per process when no secret is configured: local development
# keeps working, while tokens become invalid across restarts.
_FALLBACK_SECRET = secrets.token_urlsafe(48)


def _secret() -> str:
    return settings.jwt_secret or _FALLBACK_SECRET


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{_ALGO}${_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_b64, hash_b64 = stored.split("$")
        if algo != _ALGO:
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), base64.b64decode(salt_b64), int(iterations)
        )
        return hmac.compare_digest(dk, base64.b64decode(hash_b64))
    except (ValueError, TypeError):
        return False


def create_access_token(*, subject: str, role: str, expires_minutes: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=expires_minutes or settings.access_token_minutes)
    payload = {"sub": subject, "role": role, "iat": now, "exp": expires, "type": "access"}
    return jwt.encode(payload, _secret(), algorithm=settings.jwt_algorithm)


def create_refresh_token(*, subject: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": subject, "iat": now, "exp": now + timedelta(days=14), "type": "refresh"}
    return jwt.encode(payload, _secret(), algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Raises jwt.PyJWTError on any invalid/expired token."""
    return jwt.decode(token, _secret(), algorithms=[settings.jwt_algorithm])
