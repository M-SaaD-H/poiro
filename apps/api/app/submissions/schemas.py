"""Pydantic v2 schemas for submission and generation job payloads."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.enums import JobStatus


class CreateSubmissionRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=300)


class GenerationJobResponse(BaseModel):
    id: uuid.UUID
    submission_id: uuid.UUID
    status: JobStatus
    error_message: str | None
    enqueued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    retry_count: int

    model_config = {"from_attributes": True}


class SubmissionResponse(BaseModel):
    id: uuid.UUID
    round_id: uuid.UUID
    participant_id: uuid.UUID
    prompt: str
    generated_output: str | None
    created_at: datetime
    generation_job: GenerationJobResponse | None = None

    model_config = {"from_attributes": True}


class SubmissionWithJobResponse(BaseModel):
    submission: SubmissionResponse
    job: GenerationJobResponse
