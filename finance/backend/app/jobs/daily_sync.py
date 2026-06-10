from app.db.session import SessionLocal
from app.services.sync_service import sync_user_finances


def main() -> None:
    db = SessionLocal()
    try:
        # MVP placeholder: users are wired after initial auth bootstrap.
        del db
    finally:
        pass


if __name__ == "__main__":
    main()

