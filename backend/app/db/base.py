from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy 2.x declarative models.
    """
    pass


# Import models so they register with Base.metadata for Alembic and tests.
# Kept at the bottom to avoid circular import issues during model definition.
import app.models  # noqa: E402,F401
