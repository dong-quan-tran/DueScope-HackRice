from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import normalize_database_url


def test_normalize_neon_postgresql_url_for_psycopg_v3() -> None:
    input_url = "postgresql://user:password@host.neon.tech/neondb?sslmode=require"

    assert normalize_database_url(input_url) == (
        "postgresql+psycopg://user:password@host.neon.tech/neondb?sslmode=require"
    )


def test_normalize_legacy_postgres_url_for_psycopg_v3() -> None:
    input_url = "postgres://user:password@host.example.com/database"

    assert normalize_database_url(input_url) == (
        "postgresql+psycopg://user:password@host.example.com/database"
    )


def test_keep_sqlite_url_unchanged() -> None:
    input_url = "sqlite:///./duescope.db"

    assert normalize_database_url(input_url) == input_url
