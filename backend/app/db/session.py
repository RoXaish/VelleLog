from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Engine configuration
connect_args: dict[str, Any] = {}

# SQLite requires check_same_thread=False when used in multithreaded environments like FastAPI.
# Other database engines (e.g., PostgreSQL) do not require this.
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

# SQLite does not enforce foreign keys by default.
# Enable foreign key constraint checking on every new SQLite DBAPI connection.
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session per request
    and guarantees it is closed after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
