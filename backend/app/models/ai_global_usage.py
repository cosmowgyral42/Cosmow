from datetime import date

from sqlalchemy import Date, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AIGlobalUsage(Base):
    __tablename__ = "ai_global_usage"

    id: Mapped[int] = mapped_column(primary_key=True)

    usage_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    successful_call_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    reserved_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    __table_args__ = (
        UniqueConstraint(
            "usage_date",
            name="uq_ai_global_usage_date",
        ),
    )
