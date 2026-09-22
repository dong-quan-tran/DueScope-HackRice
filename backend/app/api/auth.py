"""DueScope application-session routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    get_current_user,
    sha256_hex,
)
from app.db.session import get_db
from app.models.domain import AppSession, User


router = APIRouter(prefix="/auth", tags=["auth"])


class CurrentUserResponse(BaseModel):
    id: str
    email: str | None
    display_name: str | None


class SessionStatusResponse(BaseModel):
    authenticated: bool
    user: CurrentUserResponse


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
            app_session.revoked_at = datetime.now(timezone.utc)
            db.commit()

    clear_session_cookie(response)
    return response
