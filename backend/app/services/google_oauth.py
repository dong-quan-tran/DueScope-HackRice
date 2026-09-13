from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials


ROOT_DIR = Path(__file__).resolve().parents[3]
CREDENTIALS_PATH = ROOT_DIR / "backend" / "credentials.json"
TOKEN_PATH = ROOT_DIR / "backend" / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.readonly",
]

REDIRECT_URI = "http://127.0.0.1:8001/api/google/auth/callback"


def ensure_credentials_file() -> None:
    if not CREDENTIALS_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Google OAuth credentials are missing. Download a Desktop OAuth "
                "client JSON file from Google Cloud Console and save it as "
                "backend/credentials.json."
            ),
        )


def create_flow() -> Flow:
    ensure_credentials_file()

    flow = Flow.from_client_secrets_file(
        str(CREDENTIALS_PATH),
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    return flow


def authorization_url() -> tuple[str, str]:
    flow = create_flow()

    url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    return url, state


def save_credentials(credentials: Credentials) -> None:
    TOKEN_PATH.write_text(credentials.to_json(), encoding="utf-8")


def get_credentials() -> Credentials:
    if not TOKEN_PATH.exists():
        raise HTTPException(
            status_code=401,
            detail="Google account is not connected. Open /api/google/auth/start first.",
        )

    credentials = Credentials.from_authorized_user_file(
        str(TOKEN_PATH),
        SCOPES,
    )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        save_credentials(credentials)

    if not credentials.valid:
        raise HTTPException(
            status_code=401,
            detail="Google authorization is invalid. Connect Google again.",
        )

    return credentials
