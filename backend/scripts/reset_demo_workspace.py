"""Reset only the deterministic DueScope demo workspace."""

from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models.domain import AcademicEvent, Course, Source, User
from app.repositories.academic import DEMO_USER_EMAIL


def main() -> None:
    with SessionLocal() as db:
        demo_user = db.query(User).filter(User.email == DEMO_USER_EMAIL).one_or_none()

        if demo_user is not None:
            db.execute(delete(AcademicEvent).where(AcademicEvent.user_id == demo_user.id))
            db.execute(delete(Source).where(Source.user_id == demo_user.id))
            db.execute(delete(Course).where(Course.user_id == demo_user.id))
            db.delete(demo_user)
            db.commit()

    print("Demo workspace reset. It will be re-seeded on the next workspace request.")


if __name__ == "__main__":
    main()
