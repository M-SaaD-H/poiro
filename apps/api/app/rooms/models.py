"""SQLAlchemy ORM models for rooms and participants."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import RoomStatus


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(6), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    challenge_prompt: Mapped[str] = mapped_column(String(2000), nullable=False)
    host_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[RoomStatus] = mapped_column(
        Enum(RoomStatus, name="roomstatus"), default=RoomStatus.waiting, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    host: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User", back_populates="hosted_rooms", foreign_keys=[host_id]
    )
    participants: Mapped[list["Participant"]] = relationship(
        "Participant", back_populates="room", cascade="all, delete-orphan"
    )
    rounds: Mapped[list["Round"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Round", back_populates="room", cascade="all, delete-orphan"
    )


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (UniqueConstraint("room_id", "user_id", name="uq_participant_room_user"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    room_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_eliminated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    room: Mapped[Room] = relationship("Room", back_populates="participants")
    user: Mapped["User"] = relationship("User", back_populates="participations")  # type: ignore[name-defined]  # noqa: F821
    submissions: Mapped[list["Submission"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Submission", back_populates="participant"
    )
    scores: Mapped[list["Score"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Score", back_populates="participant", foreign_keys="Score.participant_id"
    )
