"""SQLAlchemy ORM models for submissions and generation jobs."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import JobStatus


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("round_id", "participant_id", name="uq_submission_round_participant"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    round_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rounds.id", ondelete="CASCADE"), nullable=False
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), nullable=False
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    generated_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    round: Mapped["Round"] = relationship("Round", back_populates="submissions")  # type: ignore[name-defined]  # noqa: F821
    participant: Mapped["Participant"] = relationship("Participant", back_populates="submissions")  # type: ignore[name-defined]  # noqa: F821
    generation_job: Mapped["GenerationJob | None"] = relationship(
        "GenerationJob", back_populates="submission", uselist=False
    )
    score: Mapped["Score | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Score", back_populates="submission", uselist=False
    )


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="jobstatus"), default=JobStatus.queued, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    enqueued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    submission: Mapped[Submission] = relationship("Submission", back_populates="generation_job")
