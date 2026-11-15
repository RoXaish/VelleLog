import pytest
from sqlalchemy import Column, ForeignKey, Integer, String, Table, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import SessionLocal, engine, get_db
from tests.conftest import test_engine


def test_sqlite_connection_works() -> None:
    """
    1. SQLite connection works:
    Verify that the database engine connects and executes basic SQL queries.
    """
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar()
        assert result == 1


def test_foreign_key_pragma_is_enabled() -> None:
    """
    2. Foreign key PRAGMA is enabled:
    Verify that the connection event listener enables foreign keys (PRAGMA foreign_keys = ON)
    on both the application engine and test engine.
    """
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys;")).scalar() == 1

    with test_engine.connect() as test_connection:
        assert test_connection.execute(text("PRAGMA foreign_keys;")).scalar() == 1


def test_invalid_foreign_key_insertion_is_rejected(db_session: Session) -> None:
    """
    3. An actual invalid foreign-key insertion is rejected:
    Verify that SQLite actively enforces foreign keys by ensuring an insertion
    with a non-existent foreign key fails with IntegrityError, while valid foreign keys succeed.
    """
    parent_table = Table(
        "test_fk_parents",
        Base.metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(50), nullable=False),
    )
    child_table = Table(
        "test_fk_children",
        Base.metadata,
        Column("id", Integer, primary_key=True),
        Column("parent_id", Integer, ForeignKey("test_fk_parents.id"), nullable=False),
    )

    Base.metadata.create_all(bind=test_engine, tables=[parent_table, child_table])

    try:
        # Attempt to insert a child referencing a non-existent parent_id=999
        with pytest.raises(IntegrityError):
            db_session.execute(child_table.insert().values(id=1, parent_id=999))
            db_session.commit()

        db_session.rollback()

        # Insert a valid parent, then child insertion must succeed
        db_session.execute(parent_table.insert().values(id=1, name="Parent 1"))
        db_session.commit()

        db_session.execute(child_table.insert().values(id=1, parent_id=1))
        db_session.commit()

        # Verify child was inserted
        child_count = db_session.execute(
            text("SELECT COUNT(*) FROM test_fk_children WHERE parent_id = 1")
        ).scalar()
        assert child_count == 1
    finally:
        Base.metadata.drop_all(bind=test_engine, tables=[child_table, parent_table])
        Base.metadata.remove(child_table)
        Base.metadata.remove(parent_table)


def test_database_sessions_can_be_created_and_closed() -> None:
    """
    4. Database sessions can be created and closed:
    Verify that database sessions can be instantiated, active during use,
    and closed cleanly, including the get_db dependency.
    """
    # Manual SessionLocal creation and closing
    session = SessionLocal()
    assert session.is_active
    session.rollback()
    session.close()

    # get_db FastAPI dependency lifecycle
    db_gen = get_db()
    dep_session = next(db_gen)
    assert dep_session is not None
    assert dep_session.is_active

    try:
        next(db_gen)
    except StopIteration:
        pass


def test_database_isolation_does_not_modify_development_db(db_session: Session) -> None:
    """
    5. Test database operations do not modify the development database:
    Verify that operations on the test session use the isolated in-memory engine
    and do not write tables or records to the development database.
    """
    temp_table = Table(
        "test_isolation_check",
        Base.metadata,
        Column("id", Integer, primary_key=True),
        Column("data", String(50)),
    )

    # Create table only on the isolated test engine
    Base.metadata.create_all(bind=test_engine, tables=[temp_table])

    try:
        # Insert record into isolated test database
        db_session.execute(temp_table.insert().values(id=1, data="isolated_data"))
        db_session.commit()

        # Verify it exists in the test session
        test_count = db_session.execute(
            text("SELECT COUNT(*) FROM test_isolation_check")
        ).scalar()
        assert test_count == 1

        # Inspect the development database: table must NOT exist there
        dev_inspector = inspect(engine)
        dev_tables = dev_inspector.get_table_names()
        assert "test_isolation_check" not in dev_tables
    finally:
        Base.metadata.drop_all(bind=test_engine, tables=[temp_table])
        Base.metadata.remove(temp_table)
