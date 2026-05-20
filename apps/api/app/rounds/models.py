"""SQLAlchemy ORM model for rounds."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import RoundStatus


class Round(Base):
    __tablename__ = "rounds"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    room_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[RoundStatus] = mapped_column(
        Enum(RoundStatus, name="roundstatus"), default=RoundStatus.pending, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    room: Mapped["Room"] = relationship("Room", back_populates="rounds")  # type: ignore[name-defined]  # noqa: F821
    submissions: Mapped[list["Submission"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Submission", back_populates="round", cascade="all, delete-orphan"
    )
    scores: Mapped[list["Score"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Score", back_populates="round", cascade="all, delete-orphan"
    )
