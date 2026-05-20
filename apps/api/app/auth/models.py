"""SQLAlchemy ORM model for the public users profile table.

This table mirrors identity data from Supabase Auth (auth.users).
The `id` is the UUID issued by Supabase Auth — never generated locally.
Passwords are managed entirely by Supabase Auth; no hashed_password column.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    # Must match auth.users.id — provided by Supabase Auth, not generated here.
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    hosted_rooms: Mapped[list["Room"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Room", back_populates="host", foreign_keys="Room.host_id"
    )
    participations: Mapped[list["Participant"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Participant", back_populates="user"
    )
    scores_given: Mapped[list["Score"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Score", back_populates="scorer", foreign_keys="Score.scored_by"
    )
