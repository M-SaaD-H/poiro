"""Submission business logic: create submissions and enqueue generation jobs."""

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums import JobStatus, RoundStatus
from app.rooms.models import Participant, Room
from app.rounds.models import Round
from app.submissions.models import GenerationJob, Submission
from app.submissions.schemas import GenerationJobResponse, SubmissionResponse, SubmissionWithJobResponse

logger = logging.getLogger(__name__)


async def _get_participant(
    room_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession,
) -> Participant:
    """Fetch the Participant record for a user in a room."""
    participant = await session.scalar(
        select(Participant).where(
            Participant.room_id == room_id,
            Participant.user_id == user_id,
        )
    )
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this room.",
        )
    if participant.is_eliminated:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Eliminated participants cannot submit.",
        )
    return participant


async def create_submission(
    round_id: uuid.UUID,
    prompt: str,
    user_id: uuid.UUID,
    session: AsyncSession,
) -> SubmissionWithJobResponse:
    """Create a submission for the current round and enqueue an AI generation job."""
    round_ = await session.get(Round, round_id)
    if round_ is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Round not found.")
    if round_.status != RoundStatus.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submissions are only accepted during an active round.",
        )

    participant = await _get_participant(round_.room_id, user_id, session)

    # Enforce one submission per participant per round
    existing = await session.scalar(
        select(Submission).where(
            Submission.round_id == round_id,
            Submission.participant_id == participant.id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted for this round.",
        )

    submission = Submission(
        round_id=round_id,
        participant_id=participant.id,
        prompt=prompt,
    )
    session.add(submission)
    await session.flush()

    job = GenerationJob(
        submission_id=submission.id,
        status=JobStatus.queued,
    )
    session.add(job)
    await session.flush()

    logger.info("Submission %s created, job %s queued", submission.id, job.id)

    job_response = GenerationJobResponse(
        id=job.id,
        submission_id=job.submission_id,
        status=job.status,
        error_message=job.error_message,
        enqueued_at=job.enqueued_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        retry_count=job.retry_count,
    )
    return SubmissionWithJobResponse(
        submission=SubmissionResponse(
            id=submission.id,
            round_id=submission.round_id,
            participant_id=submission.participant_id,
            prompt=submission.prompt,
            generated_output=submission.generated_output,
            created_at=submission.created_at,
            generation_job=job_response,
        ),
        job=job_response,
    )


async def get_submission(submission_id: uuid.UUID, session: AsyncSession) -> SubmissionResponse:
    """Fetch a single submission with its generation job."""
    stmt = (
        select(Submission)
        .where(Submission.id == submission_id)
        .options(selectinload(Submission.generation_job))
    )
    submission = await session.scalar(stmt)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")
    return SubmissionResponse.model_validate(submission)


async def retry_job(job_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession) -> GenerationJobResponse:
    """Reset a failed job to queued status so it can be re-enqueued."""
    job = await session.get(GenerationJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    if job.status not in (JobStatus.failed, JobStatus.timed_out):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only failed or timed-out jobs can be retried.",
        )

    # Verify ownership: user must be the participant who submitted
    stmt = (
        select(Submission)
        .where(Submission.id == job.submission_id)
        .options(selectinload(Submission.participant))
    )
    submission = await session.scalar(stmt)
    if submission is None or submission.participant.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only retry your own submissions.",
        )

    job.status = JobStatus.queued
    job.error_message = None
    job.retry_count += 1
    await session.flush()
    logger.info("Job %s queued for retry (attempt %d)", job_id, job.retry_count)
    return GenerationJobResponse.model_validate(job)
