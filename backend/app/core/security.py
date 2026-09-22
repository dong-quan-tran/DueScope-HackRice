"""Security helpers for app sessions and encrypted provider credentials."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


SESSION_TTL_DAYS = 14


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def session_expires_at() -> datetime:
    return utc_now() + timedelta(days=SESSION_TTL_DAYS)


def new_session_token() -> str:
    """Return an opaque, URL-safe token suitable for an HttpOnly cookie."""
    return secrets.token_urlsafe(48)


def new_oauth_state() -> str:
    """Return an opaque OAuth state value."""
    return secrets.token_urlsafe(48)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fernet() -> Fernet:
    key = get_settings().token_encryption_key
    if not key:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is required for credential encryption.")
    try:
        return Fernet(key.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is not a valid Fernet key.") from exc


def encrypt_secret(value: str) -> str:
    """Encrypt a provider token or PKCE verifier for database storage."""
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    """Decrypt a provider token or PKCE verifier from database storage."""
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except (InvalidToken, TypeError, ValueError) as exc:
        raise RuntimeError("Stored secret could not be decrypted.") from exc
