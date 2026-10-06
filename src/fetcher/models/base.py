from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseModel(DeclarativeBase):
    __abstract__ = True

    id: Mapped[int] = mapped_column(
        primary_key=True,
        nullable=False,
        unique=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__dict__})"
