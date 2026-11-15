from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import settings

BACKEND_DIR = Path(__file__).resolve().parent.parent


def test_migration_creates_expected_users_table(tmp_path, monkeypatch) -> None:
    """
    Running the Alembic migration chain against a fresh SQLite database
    creates the expected users table without touching the development database.
    """
    database_url = f"sqlite:///{(tmp_path / 'migration_test.db').as_posix()}"
    monkeypatch.setattr(settings, "DATABASE_URL", database_url)

    alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))

    command.upgrade(alembic_config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)

        assert "users" in inspector.get_table_names()

        columns = {column["name"]: column for column in inspector.get_columns("users")}
        assert set(columns) == {
            "id",
            "email",
            "password_hash",
            "created_at",
            "updated_at",
        }

        assert columns["id"]["nullable"] is False
        assert columns["email"]["nullable"] is False
        assert columns["password_hash"]["nullable"] is False
        assert columns["created_at"]["nullable"] is False
        assert columns["updated_at"]["nullable"] is False

        assert inspector.get_pk_constraint("users")["constrained_columns"] == ["id"]

        email_indexes = [
            index
            for index in inspector.get_indexes("users")
            if index["column_names"] == ["email"]
        ]
        assert email_indexes, "users.email must be indexed"
        assert any(index["unique"] for index in email_indexes), (
            "users.email index must enforce uniqueness"
        )
    finally:
        engine.dispose()
