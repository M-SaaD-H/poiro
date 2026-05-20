"""Shared enumerations used across models and job system."""

import enum


class RoomStatus(str, enum.Enum):
    waiting = "waiting"
    active = "active"
    completed = "completed"


class RoundStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    scoring = "scoring"
    completed = "completed"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    timed_out = "timed_out"
