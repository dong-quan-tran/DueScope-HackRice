"""DueScope application identity and session routes."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    create_session,
    get_current_user,
    set_session_cookie,
    sha256_hex,
)
from app.core.config import get_settings
from app.core.security import decrypt_secret, encrypt_secret
from app.db.session import get_db
from app.models.domain import AppSession, LoginTransaction, User


router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_PROVIDER = "google_identity"
LOGIN_TTL = timedelta(minutes=10)
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_SCOPES = "openid email profile"


class CurrentUserResponse(BaseModel):
    id: str
    email: str | None
    display_name: str | None


class SessionStatusResponse(BaseModel):
    authenticated: bool
    user: CurrentUserResponse


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def required_google_login_settings() -> tuple[str, str, str]:
    settings = get_settings()

    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured on the server.",
        )

    if not settings.google_login_redirect_uri:
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_LOGIN_REDIRECT_URI is not configured on the server.",
        )

    return (
        settings.google_client_id,
        settings.google_client_secret,
        settings.google_login_redirect_uri,
    )


@router.get("/login")
def start_login(
    db: Session = Depends(get_db),
) -> RedirectResponse:
    client_id, _, redirect_uri = required_google_login_settings()
    now = utc_now()

    db.execute(
        LoginTransaction.__table__.delete().where(
            LoginTransaction.expires_at < now
        )
    )

    state = secrets.token_urlsafe(48)
    nonce = secrets.token_urlsafe(48)

    db.add(
        LoginTransaction(
            provider=GOOGLE_PROVIDER,
            state_hash=sha256_hex(state),
            encrypted_nonce=encrypt_secret(nonce),
            expires_at=now + LOGIN_TTL,
        )
    )
    db.commit()

    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": GOOGLE_SCOPES,
            "state": state,
            "nonce": nonce,
            "access_type": "online",
            "prompt": "select_account",
        }
    )

    return RedirectResponse(url=f"{GOOGLE_AUTH_URI}?{query}", status_code=307)


@router.get("/callback")
def login_callback(
    code: str = Query(...),
    state: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if not state:
        raise HTTPException(status_code=400, detail="Missing login state.")

    now = utc_now()
    transaction = db.scalar(
        select(LoginTransaction).where(
            LoginTransaction.provider == GOOGLE_PROVIDER,
            LoginTransaction.state_hash == sha256_hex(state),
            LoginTransaction.used_at.is_(None),
            LoginTransaction.expires_at > now,
        )
    )

    if transaction is None:
        raise HTTPException(
            status_code=400,
            detail="Login request was not found, expired, or already used.",
        )

    client_id, client_secret, redirect_uri = required_google_login_settings()
    nonce = decrypt_secret(transaction.encrypted_nonce)

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": GOOGLE_AUTH_URI,
                "token_uri": GOOGLE_TOKEN_URI,
                "redirect_uris": [redirect_uri],
            }
        },
        scopes=GOOGLE_SCOPES.split(),
        redirect_uri=redirect_uri,
        autogenerate_code_verifier=False,
    )
    flow.oauth2session.scope = None

    try:
        flow.fetch_token(code=code)
        verified = id_token.verify_oauth2_token(
            flow.credentials.id_token,
            google_requests.Request(),
            client_id,
        )
    except Exception as exc:
        import logging
        import secrets

        request_id = secrets.token_hex(8)
        logging.getLogger(__name__).exception(
            "Google sign-in failed; request_id=%s",
            request_id,
        )
        raise HTTPException(
            status_code=400,
            detail=(
                "Google sign-in failed. Please try again. "
                f"Reference: {request_id}"
            ),
        ) from exc

    if verified.get("nonce") != nonce:
        raise HTTPException(status_code=400, detail="Invalid login nonce.")

    if not verified.get("email_verified") or not verified.get("email"):
        raise HTTPException(
            status_code=400,
            detail="Google did not provide a verified email address.",
        )

    email = str(verified["email"]).lower()
    display_name = str(verified.get("name") or "").strip() or None

    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, display_name=display_name, is_demo=False)
        db.add(user)
    else:
        user.display_name = display_name

    transaction.used_at = now
    db.commit()
    db.refresh(user)

    raw_session_token, app_session = create_session(db, user)

    redirect = RedirectResponse(
        url=f"{get_settings().public_app_url.rstrip('/')}/demo?login=success",
        status_code=303,
    )
    set_session_cookie(redirect, raw_session_token, app_session.expires_at)
    return redirect


@router.get("/me", response_model=SessionStatusResponse)
def get_me(current_user: User = Depends(get_current_user)) -> SessionStatusResponse:
    return SessionStatusResponse(
        authenticated=True,
        user=CurrentUserResponse(
            id=current_user.id,
            email=current_user.email,
            display_name=current_user.display_name,
        ),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> Response:
    if session_token:
        app_session = db.scalar(
            select(AppSession).where(
                AppSession.session_hash == sha256_hex(session_token)
            )
        )
        if app_session and app_session.revoked_at is None:
            app_session.revoked_at = utc_now()
            db.commit()

    clear_session_cookie(response)
    return response



