from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

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


def test_migration_creates_expected_groups_and_memberships_tables(
    tmp_path, monkeypatch
) -> None:
    """
    Running the migration chain up to head creates the groups and
    group_memberships tables with expected columns, indexes, and constraints.
    """
    database_url = f"sqlite:///{(tmp_path / 'migration_groups_test.db').as_posix()}"
    monkeypatch.setattr(settings, "DATABASE_URL", database_url)

    alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))

    command.upgrade(alembic_config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        assert "groups" in table_names
        assert "group_memberships" in table_names

        # Inspect 'groups' columns
        group_cols = {col["name"]: col for col in inspector.get_columns("groups")}
        assert set(group_cols) == {
            "id",
            "name",
            "invite_code",
            "owner_id",
            "created_at",
        }
        assert group_cols["id"]["nullable"] is False
        assert group_cols["name"]["nullable"] is False
        assert group_cols["invite_code"]["nullable"] is False
        assert group_cols["owner_id"]["nullable"] is False
        assert group_cols["created_at"]["nullable"] is False

        # Inspect 'groups' indexes (invite_code unique index)
        group_indexes = inspector.get_indexes("groups")
        invite_code_index = next(
            (idx for idx in group_indexes if idx["column_names"] == ["invite_code"]),
            None,
        )
        assert invite_code_index is not None, "groups.invite_code must be indexed"
        assert bool(invite_code_index["unique"]) is True, "groups.invite_code must be unique"

        # Inspect 'group_memberships' columns
        membership_cols = {
            col["name"]: col for col in inspector.get_columns("group_memberships")
        }
        assert set(membership_cols) == {
            "id",
            "group_id",
            "user_id",
            "role",
            "joined_at",
        }
        assert membership_cols["id"]["nullable"] is False
        assert membership_cols["group_id"]["nullable"] is False
        assert membership_cols["user_id"]["nullable"] is False
        assert membership_cols["role"]["nullable"] is False
        assert membership_cols["joined_at"]["nullable"] is False

        # Inspect unique constraint on (group_id, user_id)
        unique_constraints = inspector.get_unique_constraints("group_memberships")
        has_uq = any(
            set(uq["column_names"]) == {"group_id", "user_id"}
            for uq in unique_constraints
        )
        assert has_uq, "group_memberships must enforce unique (group_id, user_id)"

        # Inspect check constraint restricting role to 'owner' and 'member'
        check_constraints = inspector.get_check_constraints("group_memberships")
        assert any(
            ck.get("name") == "ck_group_memberships_role"
            or ("owner" in ck.get("sqltext", "") and "member" in ck.get("sqltext", ""))
            for ck in check_constraints
        ), "group_memberships must define a CHECK constraint on role"

        # Verify check constraint is actively enforced by the migrated database
        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, created_at, updated_at) "
                    "VALUES (1, 'mig_owner@example.com', 'hash', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO groups (id, name, invite_code, owner_id, created_at) "
                    "VALUES (1, 'Migrated Group', 'MIGCODE123', 1, CURRENT_TIMESTAMP)"
                )
            )
            conn.commit()

            # Invalid role rejected
            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        "INSERT INTO group_memberships (group_id, user_id, role, joined_at) "
                        "VALUES (1, 1, 'admin', CURRENT_TIMESTAMP)"
                    )
                )

            # Valid role accepted
            conn.execute(
                text(
                    "INSERT INTO group_memberships (group_id, user_id, role, joined_at) "
                    "VALUES (1, 1, 'owner', CURRENT_TIMESTAMP)"
                )
            )
            conn.commit()
    finally:
        engine.dispose()


def test_migration_creates_expected_busy_blocks_table(
    tmp_path, monkeypatch
) -> None:
    """
    Running the migration chain up to head creates the busy_blocks table
    with correct columns, indexes, foreign keys, and check constraints.
    """
    database_url = f"sqlite:///{(tmp_path / 'migration_busy_blocks_test.db').as_posix()}"
    monkeypatch.setattr(settings, "DATABASE_URL", database_url)

    alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))

    command.upgrade(alembic_config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        assert "busy_blocks" in table_names

        # Inspect columns
        cols = {col["name"]: col for col in inspector.get_columns("busy_blocks")}
        assert set(cols) == {
            "id",
            "user_id",
            "weekday",
            "start_time",
            "end_time",
            "private_label",
            "created_at",
            "updated_at",
        }
        assert cols["id"]["nullable"] is False
        assert cols["user_id"]["nullable"] is False
        assert cols["weekday"]["nullable"] is False
        assert cols["start_time"]["nullable"] is False
        assert cols["end_time"]["nullable"] is False
        assert cols["private_label"]["nullable"] is True
        assert cols["created_at"]["nullable"] is False
        assert cols["updated_at"]["nullable"] is False

        # Inspect indexes
        indexes = inspector.get_indexes("busy_blocks")
        index_cols = [tuple(idx["column_names"]) for idx in indexes]
        assert ("user_id",) in index_cols
        assert ("user_id", "weekday") in index_cols

        # Inspect foreign keys
        fks = inspector.get_foreign_keys("busy_blocks")
        assert len(fks) == 1
        fk = fks[0]
        assert fk["referred_table"] == "users"
        assert fk["referred_columns"] == ["id"]
        assert fk["constrained_columns"] == ["user_id"]
        assert (fk.get("options") or {}).get("ondelete", "").upper() == "CASCADE"

        # Inspect check constraints
        check_constraints = inspector.get_check_constraints("busy_blocks")
        assert any(
            ck.get("name") == "ck_busy_blocks_weekday"
            or ("weekday" in ck.get("sqltext", ""))
            for ck in check_constraints
        ), "busy_blocks must define check constraint on weekday"
        assert any(
            ck.get("name") == "ck_busy_blocks_time_range"
            or ("start_time" in ck.get("sqltext", "") and "end_time" in ck.get("sqltext", ""))
            for ck in check_constraints
        ), "busy_blocks must define check constraint on time range"

        # Verify enforcement via direct SQL operations
        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, created_at, updated_at) "
                    "VALUES (1, 'bb_mig_user@example.com', 'hash', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            conn.commit()

            # Valid busy block insert succeeds
            conn.execute(
                text(
                    "INSERT INTO busy_blocks (user_id, weekday, start_time, end_time, private_label, created_at, updated_at) "
                    "VALUES (1, 0, '09:00:00', '10:00:00', 'Valid Block', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            conn.commit()

            # Invalid weekday (> 6) rejected
            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        "INSERT INTO busy_blocks (user_id, weekday, start_time, end_time, created_at, updated_at) "
                        "VALUES (1, 7, '09:00:00', '10:00:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                    )
                )

            # Invalid time range (start_time >= end_time) rejected
            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        "INSERT INTO busy_blocks (user_id, weekday, start_time, end_time, created_at, updated_at) "
                        "VALUES (1, 1, '11:00:00', '10:00:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                    )
                )
    finally:
        engine.dispose()
