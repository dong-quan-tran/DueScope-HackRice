from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from sqlalchemy import select

from app.core.security import decrypt_secret, encrypt_secret
from app.db.session import SessionLocal
from app.models.domain import OAuthCredential, OAuthTransaction


SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.readonly",
]

PROVIDER = "google"
OAUTH_TRANSACTION_TTL = timedelta(minutes=15)


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise HTTPException(
            status_code=503,
            detail=f"{name} is not configured on the server.",
        )
    return value


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
    flow = Flow.from_client_config(
        client_config(),
        scopes=SCOPES,
        redirect_uri=required_env("GOOGLE_OAUTH_REDIRECT_URI"),
        autogenerate_code_verifier=False,
    )
    flow.oauth2session.scope = None
    return flow


def save_oauth_transaction(user_id: str, state: str, code_verifier: str) -> None:
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        db.execute(
            OAuthTransaction.__table__.delete().where(
                OAuthTransaction.expires_at < now
            )
        )
        db.add(
            OAuthTransaction(
                user_id=user_id,
                provider=PROVIDER,
                purpose="connect",
                state_hash=state_hash(state),
                encrypted_code_verifier=encrypt_secret(code_verifier),
                expires_at=now + OAUTH_TRANSACTION_TTL,
            )
        )
        db.commit()


def consume_oauth_transaction(state: str) -> tuple[str, str] | None:
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        record = db.scalar(
            select(OAuthTransaction).where(
                OAuthTransaction.provider == PROVIDER,
                OAuthTransaction.purpose == "connect",
                OAuthTransaction.state_hash == state_hash(state),
                OAuthTransaction.used_at.is_(None),
                OAuthTransaction.expires_at > now,
            )
        )

        if record is None:
            return None

        record.used_at = now
        user_id = record.user_id
        code_verifier = decrypt_secret(record.encrypted_code_verifier)
        db.commit()

    return user_id, code_verifier


def save_credentials(user_id: str, credentials: Credentials) -> None:
    raw_json = credentials.to_json()

    with SessionLocal() as db:
        record = db.scalar(
            select(OAuthCredential).where(
                OAuthCredential.user_id == user_id,
                OAuthCredential.provider == PROVIDER,
            )
        )

        if record is None:
            record = OAuthCredential(
                user_id=user_id,
                provider=PROVIDER,
                encrypted_token=encrypt_secret(raw_json),
                scopes=list(credentials.scopes or SCOPES),
                expires_at=credentials.expiry,
            )
            db.add(record)
        else:
            record.encrypted_token = encrypt_secret(raw_json)
            record.scopes = list(credentials.scopes or SCOPES)
            record.expires_at = credentials.expiry

        db.commit()


def get_credentials(user_id: str) -> Credentials:
    with SessionLocal() as db:
        record = db.scalar(
            select(OAuthCredential).where(
                OAuthCredential.user_id == user_id,
                OAuthCredential.provider == PROVIDER,
            )
        )

        if record is None:
            raise HTTPException(
                status_code=401,
                detail="Google account is not connected. Connect Google first.",
            )

        raw_json = decrypt_secret(record.encrypted_token)

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

        save_credentials(user_id, credentials)

    if not credentials.valid:
        raise HTTPException(
            status_code=401,
            detail="Google authorization is invalid. Connect Google again.",
        )

    return credentials


def delete_credentials(user_id: str) -> bool:
    with SessionLocal() as db:
        record = db.scalar(
            select(OAuthCredential).where(
                OAuthCredential.user_id == user_id,
                OAuthCredential.provider == PROVIDER,
            )
        )

        if record is None:
            return False

        db.delete(record)
        db.commit()

    return True

