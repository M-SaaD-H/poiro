"""SQLAlchemy ORM model for scores."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    round_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rounds.id", ondelete="CASCADE"), nullable=False
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), nullable=False
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    is_eliminated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scored_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=False
    )
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    round: Mapped["Round"] = relationship("Round", back_populates="scores")  # type: ignore[name-defined]  # noqa: F821
    participant: Mapped["Participant"] = relationship("Participant", back_populates="scores", foreign_keys=[participant_id])  # type: ignore[name-defined]  # noqa: F821
    submission: Mapped["Submission"] = relationship("Submission", back_populates="score")  # type: ignore[name-defined]  # noqa: F821
    scorer: Mapped["User"] = relationship("User", back_populates="scores_given", foreign_keys=[scored_by])  # type: ignore[name-defined]  # noqa: F821
