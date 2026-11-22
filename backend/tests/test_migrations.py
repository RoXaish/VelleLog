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


def test_migration_creates_expected_schedule_exceptions_table(
    tmp_path, monkeypatch
) -> None:
    """
    Running the migration chain up to head creates the schedule_exceptions
    table with expected columns, indexes, check constraints, and cascade delete.
    """
    database_url = f"sqlite:///{(tmp_path / 'migration_exceptions_test.db').as_posix()}"
    monkeypatch.setattr(settings, "DATABASE_URL", database_url)

    alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))

    command.upgrade(alembic_config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        assert "schedule_exceptions" in table_names

        cols = {col["name"]: col for col in inspector.get_columns("schedule_exceptions")}
        assert set(cols) == {
            "id",
            "user_id",
            "date",
            "start_time",
            "end_time",
            "exception_type",
            "private_label",
            "created_at",
            "updated_at",
        }
        assert cols["id"]["nullable"] is False
        assert cols["user_id"]["nullable"] is False
        assert cols["date"]["nullable"] is False
        assert cols["start_time"]["nullable"] is False
        assert cols["end_time"]["nullable"] is False
        assert cols["exception_type"]["nullable"] is False
        assert cols["private_label"]["nullable"] is True
        assert cols["created_at"]["nullable"] is False
        assert cols["updated_at"]["nullable"] is False

        indexes = inspector.get_indexes("schedule_exceptions")
        index_cols = [tuple(idx["column_names"]) for idx in indexes]
        assert ("user_id",) in index_cols
        assert ("user_id", "date") in index_cols

        fks = inspector.get_foreign_keys("schedule_exceptions")
        assert len(fks) == 1
        fk = fks[0]
        assert fk["referred_table"] == "users"
        assert fk["referred_columns"] == ["id"]
        assert fk["constrained_columns"] == ["user_id"]
        assert (fk.get("options") or {}).get("ondelete", "").upper() == "CASCADE"

        check_constraints = inspector.get_check_constraints("schedule_exceptions")
        assert any(
            ck.get("name") == "ck_schedule_exceptions_time_range"
            or ("start_time" in ck.get("sqltext", "") and "end_time" in ck.get("sqltext", ""))
            for ck in check_constraints
        ), "schedule_exceptions must define check constraint on time range"
        assert any(
            ck.get("name") == "ck_schedule_exceptions_type"
            or ("exception_type" in ck.get("sqltext", ""))
            for ck in check_constraints
        ), "schedule_exceptions must define check constraint on exception type"

        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, created_at, updated_at) "
                    "VALUES (1, 'ex_mig_user@example.com', 'hash', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            conn.commit()

            # Valid schedule exception insert succeeds
            conn.execute(
                text(
                    "INSERT INTO schedule_exceptions (user_id, date, start_time, end_time, exception_type, private_label, created_at, updated_at) "
                    "VALUES (1, '2026-11-20', '09:00:00', '11:00:00', 'busy', 'Doctor', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            conn.commit()

            # Invalid type rejected
            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        "INSERT INTO schedule_exceptions (user_id, date, start_time, end_time, exception_type, created_at, updated_at) "
                        "VALUES (1, '2026-11-20', '12:00:00', '13:00:00', 'invalid_type', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                    )
                )

            # Invalid time range (start >= end) rejected
            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        "INSERT INTO schedule_exceptions (user_id, date, start_time, end_time, exception_type, created_at, updated_at) "
                        "VALUES (1, '2026-11-20', '14:00:00', '13:00:00', 'free', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                    )
                )
    finally:
        engine.dispose()


def test_migration_creates_expected_schedule_templates_tables(
    tmp_path, monkeypatch
) -> None:
    """
    Running migration chain up to head creates schedule_templates,
    template_busy_blocks, and applied_schedule_templates tables with expected
    columns, foreign keys, indexes, and constraints.
    """
    database_url = f"sqlite:///{(tmp_path / 'migration_templates_test.db').as_posix()}"
    monkeypatch.setattr(settings, "DATABASE_URL", database_url)

    alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))

    command.upgrade(alembic_config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        assert "schedule_templates" in table_names
        assert "template_busy_blocks" in table_names
        assert "applied_schedule_templates" in table_names

        # schedule_templates inspection
        st_cols = {col["name"]: col for col in inspector.get_columns("schedule_templates")}
        assert set(st_cols) == {
            "id",
            "group_id",
            "name",
            "created_by_user_id",
            "created_at",
            "updated_at",
        }
        assert st_cols["id"]["nullable"] is False
        assert st_cols["group_id"]["nullable"] is False
        assert st_cols["name"]["nullable"] is False
        assert st_cols["created_by_user_id"]["nullable"] is True

        st_fks = inspector.get_foreign_keys("schedule_templates")
        st_fk_tables = {fk["referred_table"] for fk in st_fks}
        assert "groups" in st_fk_tables
        assert "users" in st_fk_tables

        # template_busy_blocks inspection
        tbb_cols = {col["name"]: col for col in inspector.get_columns("template_busy_blocks")}
        assert set(tbb_cols) == {
            "id",
            "template_id",
            "weekday",
            "start_time",
            "end_time",
            "created_at",
            "updated_at",
        }
        assert tbb_cols["id"]["nullable"] is False
        assert tbb_cols["template_id"]["nullable"] is False
        assert tbb_cols["weekday"]["nullable"] is False
        assert tbb_cols["start_time"]["nullable"] is False
        assert tbb_cols["end_time"]["nullable"] is False

        tbb_fks = inspector.get_foreign_keys("template_busy_blocks")
        assert len(tbb_fks) == 1
        assert tbb_fks[0]["referred_table"] == "schedule_templates"
        assert (tbb_fks[0].get("options") or {}).get("ondelete", "").upper() == "CASCADE"

        tbb_indexes = inspector.get_indexes("template_busy_blocks")
        tbb_idx_cols = [tuple(idx["column_names"]) for idx in tbb_indexes]
        assert ("template_id",) in tbb_idx_cols
        assert ("template_id", "weekday") in tbb_idx_cols

        # applied_schedule_templates inspection
        ast_cols = {col["name"]: col for col in inspector.get_columns("applied_schedule_templates")}
        assert set(ast_cols) == {
            "id",
            "user_id",
            "template_id",
            "applied_at",
        }
        ast_uqs = inspector.get_unique_constraints("applied_schedule_templates")
        assert any(
            set(uq["column_names"]) == {"user_id", "template_id"} for uq in ast_uqs
        ), "applied_schedule_templates must enforce unique(user_id, template_id)"

        # SQL level constraint enforcement tests
        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, created_at, updated_at) "
                    "VALUES (1, 't_mig_owner@example.com', 'hash', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO groups (id, name, invite_code, owner_id, created_at) "
                    "VALUES (1, 'Test Group', 'inv_code_123', 1, CURRENT_TIMESTAMP)"
                )
            )
            conn.commit()

            # Valid schedule template insert
            conn.execute(
                text(
                    "INSERT INTO schedule_templates (id, group_id, name, created_by_user_id, created_at, updated_at) "
                    "VALUES (1, 1, 'College Timetable', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            conn.commit()

            # Valid template block insert
            conn.execute(
                text(
                    "INSERT INTO template_busy_blocks (id, template_id, weekday, start_time, end_time, created_at, updated_at) "
                    "VALUES (1, 1, 0, '09:00:00', '10:30:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            conn.commit()

            # Invalid weekday (> 6) rejected
            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        "INSERT INTO template_busy_blocks (template_id, weekday, start_time, end_time, created_at, updated_at) "
                        "VALUES (1, 7, '09:00:00', '10:30:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                    )
                )

            # Invalid time range (start >= end) rejected
            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        "INSERT INTO template_busy_blocks (template_id, weekday, start_time, end_time, created_at, updated_at) "
                        "VALUES (1, 1, '11:00:00', '10:30:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                    )
                )

            # Valid template application
            conn.execute(
                text(
                    "INSERT INTO applied_schedule_templates (user_id, template_id, applied_at) "
                    "VALUES (1, 1, CURRENT_TIMESTAMP)"
                )
            )
            conn.commit()

            # Duplicate application rejected
            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        "INSERT INTO applied_schedule_templates (user_id, template_id, applied_at) "
                        "VALUES (1, 1, CURRENT_TIMESTAMP)"
                    )
                )
    finally:
        engine.dispose()

def test_migration_creates_expected_journal_entries_table(
    tmp_path, monkeypatch
) -> None:
    """
    Running the migration chain up to head creates the journal_entries table
    with ownership, ordering indexes, and non-empty content constraints.
    """
    database_url = f"sqlite:///{(tmp_path / 'migration_journal_test.db').as_posix()}"
    monkeypatch.setattr(settings, "DATABASE_URL", database_url)

    alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))

    command.upgrade(alembic_config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        assert "journal_entries" in inspector.get_table_names()

        columns = {
            column["name"]: column
            for column in inspector.get_columns("journal_entries")
        }
        assert set(columns) == {
            "id",
            "user_id",
            "title",
            "content",
            "mood",
            "created_at",
            "updated_at",
        }
        assert columns["id"]["nullable"] is False
        assert columns["user_id"]["nullable"] is False
        assert columns["title"]["nullable"] is False
        assert columns["content"]["nullable"] is False
        assert columns["mood"]["nullable"] is True
        assert columns["created_at"]["nullable"] is False
        assert columns["updated_at"]["nullable"] is False

        foreign_keys = inspector.get_foreign_keys("journal_entries")
        assert len(foreign_keys) == 1
        assert foreign_keys[0]["referred_table"] == "users"
        assert (foreign_keys[0].get("options") or {}).get("ondelete", "").upper() == "CASCADE"

        index_columns = {
            tuple(index["column_names"])
            for index in inspector.get_indexes("journal_entries")
        }
        assert ("user_id",) in index_columns
        assert ("user_id", "created_at") in index_columns
        assert ("user_id", "mood") in index_columns

        check_names = {
            check["name"]
            for check in inspector.get_check_constraints("journal_entries")
        }
        assert "ck_journal_entries_title_length" in check_names
        assert "ck_journal_entries_content_length" in check_names
        assert "ck_journal_entries_mood" in check_names

        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, created_at, updated_at) "
                    "VALUES (1, 'journal_migration@example.com', 'hash', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO journal_entries (user_id, title, content) "
                    "VALUES (1, 'A real entry', 'Words worth keeping.')"
                )
            )
            conn.commit()

            for invalid_title, invalid_content in [
                ("   ", "Valid content"),
                ("Valid title", "   "),
                ("x" * 201, "Valid content"),
            ]:
                with pytest.raises(IntegrityError):
                    conn.execute(
                        text(
                            "INSERT INTO journal_entries (user_id, title, content) "
                            "VALUES (1, :title, :content)"
                        ),
                        {"title": invalid_title, "content": invalid_content},
                    )
                conn.rollback()

            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        "INSERT INTO journal_entries (user_id, title, content, mood) "
                        "VALUES (1, 'Unsupported mood', 'Body', 'ecstatic')"
                    )
                )
            conn.rollback()
    finally:
        engine.dispose()


def test_migration_creates_tags_and_entry_tag_relationships(
    tmp_path, monkeypatch
) -> None:
    """
    The tags migration creates user-owned tags, a cascading association table,
    and enforces tag name constraints.
    """
    database_url = f"sqlite:///{(tmp_path / 'migration_tags_test.db').as_posix()}"
    monkeypatch.setattr(settings, "DATABASE_URL", database_url)

    alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))

    command.upgrade(alembic_config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())
        assert "tags" in table_names
        assert "journal_entry_tags" in table_names

        tag_columns = {
            column["name"]: column for column in inspector.get_columns("tags")
        }
        assert set(tag_columns) == {
            "id",
            "user_id",
            "name",
            "created_at",
            "updated_at",
        }
        assert tag_columns["id"]["nullable"] is False
        assert tag_columns["user_id"]["nullable"] is False
        assert tag_columns["name"]["nullable"] is False

        tag_foreign_keys = inspector.get_foreign_keys("tags")
        assert len(tag_foreign_keys) == 1
        assert tag_foreign_keys[0]["referred_table"] == "users"
        assert (
            (tag_foreign_keys[0].get("options") or {}).get("ondelete", "").upper()
            == "CASCADE"
        )

        tag_indexes = {
            (tuple(index["column_names"]), index["unique"])
            for index in inspector.get_indexes("tags")
        }
        assert (("user_id",), False) in tag_indexes
        assert (("user_id", "name"), False) in tag_indexes
        assert (
            tuple(inspector.get_unique_constraints("tags")[0]["column_names"])
            == ("user_id", "name")
        )

        tag_checks = {
            check["name"] for check in inspector.get_check_constraints("tags")
        }
        assert "ck_tags_name_length" in tag_checks

        link_columns = {
            column["name"]: column
            for column in inspector.get_columns("journal_entry_tags")
        }
        assert set(link_columns) == {"journal_entry_id", "tag_id"}
        assert link_columns["journal_entry_id"]["nullable"] is False
        assert link_columns["tag_id"]["nullable"] is False
        assert inspector.get_pk_constraint("journal_entry_tags")[
            "constrained_columns"
        ] == ["journal_entry_id", "tag_id"]

        link_foreign_keys = {
            foreign_key["referred_table"]: foreign_key
            for foreign_key in inspector.get_foreign_keys("journal_entry_tags")
        }
        assert set(link_foreign_keys) == {"journal_entries", "tags"}
        for foreign_key in link_foreign_keys.values():
            assert (
                (foreign_key.get("options") or {}).get("ondelete", "").upper()
                == "CASCADE"
            )

        link_index_columns = {
            tuple(index["column_names"])
            for index in inspector.get_indexes("journal_entry_tags")
        }
        assert ("tag_id",) in link_index_columns

        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, created_at, updated_at) "
                    "VALUES (1, 'tag_migration@example.com', 'hash', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO journal_entries (id, user_id, title, content, mood) "
                    "VALUES (1, 1, 'Tagged entry', 'Body', 'calm')"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO tags (id, user_id, name) "
                    "VALUES (1, 1, 'Reflection')"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO journal_entry_tags (journal_entry_id, tag_id) "
                    "VALUES (1, 1)"
                )
            )
            conn.commit()

            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        "INSERT INTO tags (user_id, name) "
                        "VALUES (1, 'Reflection')"
                    )
                )
            conn.rollback()

            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        "INSERT INTO tags (user_id, name) "
                        "VALUES (1, '   ')"
                    )
                )
            conn.rollback()

            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        "INSERT INTO journal_entry_tags "
                        "(journal_entry_id, tag_id) VALUES (1, 1)"
                    )
                )
            conn.rollback()
    finally:
        engine.dispose()
