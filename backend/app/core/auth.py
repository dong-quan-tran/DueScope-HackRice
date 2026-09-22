"""Application session helpers and authenticated-user dependencies."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import new_session_token, session_expires_at, sha256_hex
from app.db.session import get_db
from app.models.domain import AppSession, User


SESSION_COOKIE_NAME = "duescope_session"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_session(db: Session, user: User) -> tuple[str, AppSession]:
    """Create and persist an opaque server-side session for a user."""
    raw_token = new_session_token()
    session = AppSession(
        user_id=user.id,
        session_hash=sha256_hex(raw_token),
        expires_at=session_expires_at(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return raw_token, session


def set_session_cookie(response: Response, raw_token: str, expires_at: datetime) -> None:
    """Set the secure HttpOnly application-session cookie."""
    max_age = max(0, int((expires_at - utc_now()).total_seconds()))
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=max_age,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )


def get_current_user(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the opaque session cookie."""
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in is required.",
        )

    session = db.scalar(
        select(AppSession).where(
            AppSession.session_hash == sha256_hex(session_token),
            AppSession.revoked_at.is_(None),
            AppSession.expires_at > utc_now(),
        )
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session is invalid or expired. Sign in again.",
        )

    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your account no longer exists. Sign in again.",
        )

    return user
