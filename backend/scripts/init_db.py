"""Create DueScope database tables for local development."""

from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import Base, engine
import app.models  # noqa: F401


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("DueScope database tables are ready.")


if __name__ == "__main__":
    main()
