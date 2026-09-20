from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.domain import OAuthCredential, OAuthState
from app.repositories.academic import get_or_create_demo_user


SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.readonly",
]

PROVIDER = "google"
OAUTH_STATE_TTL = timedelta(minutes=15)


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise HTTPException(
            status_code=503,
            detail=f"{name} is not configured on the server.",
        )

    return value


def fernet() -> Fernet:
    raw_key = required_env("GOOGLE_TOKEN_ENCRYPTION_KEY")

    try:
        return Fernet(raw_key.encode("utf-8"))
    except (ValueError, TypeError):
        derived_key = base64.urlsafe_b64encode(
            hashlib.sha256(raw_key.encode("utf-8")).digest()
        )
        return Fernet(derived_key)


def encrypt(value: str) -> str:
    return fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt(value: str) -> str:
    try:
        return fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Google credentials cannot be decrypted. "
                "Check GOOGLE_TOKEN_ENCRYPTION_KEY or reconnect Google."
            ),
        ) from exc


def state_hash(state: str) -> str:
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def client_config() -> dict[str, dict[str, Any]]:
    redirect_uri = required_env("GOOGLE_OAUTH_REDIRECT_URI")

    return {
        "web": {
            "client_id": required_env("GOOGLE_CLIENT_ID"),
            "client_secret": required_env("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": (
                "https://www.googleapis.com/oauth2/v1/certs"
            ),
            "redirect_uris": [redirect_uri],
        }
    }


def create_flow() -> Flow:
    return Flow.from_client_config(
        client_config(),
        scopes=SCOPES,
        redirect_uri=required_env("GOOGLE_OAUTH_REDIRECT_URI"),
    )


def save_oauth_state(state: str) -> None:
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        db.execute(
            OAuthState.__table__.delete().where(
                OAuthState.created_at < now - OAUTH_STATE_TTL
            )
        )
        db.add(
            OAuthState(
                provider=PROVIDER,
                state_hash=state_hash(state),
            )
        )
        db.commit()


def consume_oauth_state(state: str) -> bool:
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        record = db.scalar(
            select(OAuthState).where(
                OAuthState.provider == PROVIDER,
                OAuthState.state_hash == state_hash(state),
            )
        )

        if record is None:
            return False

        db.delete(record)
        db.commit()

    created_at = record.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    return now - created_at <= OAUTH_STATE_TTL


def save_credentials(credentials: Credentials) -> None:
    raw_json = credentials.to_json()

    with SessionLocal() as db:
        user = get_or_create_demo_user(db)
        record = db.scalar(
            select(OAuthCredential).where(
                OAuthCredential.user_id == user.id,
                OAuthCredential.provider == PROVIDER,
            )
        )

        if record is None:
            record = OAuthCredential(
                user_id=user.id,
                provider=PROVIDER,
                encrypted_token=encrypt(raw_json),
                scopes=list(credentials.scopes or SCOPES),
                expires_at=credentials.expiry,
            )
            db.add(record)
        else:
            record.encrypted_token = encrypt(raw_json)
            record.scopes = list(credentials.scopes or SCOPES)
            record.expires_at = credentials.expiry

        db.commit()


def get_credentials() -> Credentials:
    with SessionLocal() as db:
        user = get_or_create_demo_user(db)
        record = db.scalar(
            select(OAuthCredential).where(
                OAuthCredential.user_id == user.id,
                OAuthCredential.provider == PROVIDER,
            )
        )

        if record is None:
            raise HTTPException(
                status_code=401,
                detail=(
                    "Google account is not connected. "
                    "Open /api/google/auth/start first."
                ),
            )

        raw_json = decrypt(record.encrypted_token)

    credentials = Credentials.from_authorized_user_info(
        json.loads(raw_json),
        SCOPES,
    )

    if credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except Exception as exc:
            raise HTTPException(
                status_code=401,
                detail=f"Google authorization refresh failed: {exc}",
            ) from exc

        save_credentials(credentials)

    if not credentials.valid:
        raise HTTPException(
            status_code=401,
            detail="Google authorization is invalid. Connect Google again.",
        )

    return credentials


def delete_credentials() -> bool:
    with SessionLocal() as db:
        user = get_or_create_demo_user(db)
        record = db.scalar(
            select(OAuthCredential).where(
                OAuthCredential.user_id == user.id,
                OAuthCredential.provider == PROVIDER,
            )
        )

        if record is None:
            return False

        db.delete(record)
        db.commit()

    return True
