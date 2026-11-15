from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy 2.x declarative models.
    Application models will inherit from this Base class in future milestones.
    """
    pass
