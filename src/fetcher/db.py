import pydantic
import sqlalchemy


def get_engine(db_url: pydantic.AnyUrl) -> sqlalchemy.engine.Engine:
    """
    Create a SQLAlchemy engine instance.

    Args:
        db_url (pydantic.AnyUrl): The database URL.

    Returns:
        sqlalchemy.engine.Engine: The SQLAlchemy engine instance.
    """
    return sqlalchemy.create_engine(
        url=str(db_url),
    )
