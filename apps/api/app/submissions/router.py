"""Submissions router: submit prompts, fetch results, retry failed jobs."""

import logging
import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_current_user_id
from app.auth.models import User
from app.database import get_session
from app.rounds.models import Round
from app.submissions.schemas import CreateSubmissionRequest, GenerationJobResponse, SubmissionResponse, SubmissionWithJobResponse
from app.submissions.service import create_submission, get_submission, retry_job

router = APIRouter(tags=["submissions"])
logger = logging.getLogger(__name__)


@router.post(
    "/rounds/{round_id}/submissions",
    response_model=SubmissionWithJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_prompt(
    request: Request,
    round_id: uuid.UUID,
    body: CreateSubmissionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SubmissionWithJobResponse:
    """Submit a creative prompt for the active round. Enqueues an AI generation job."""
    from app.ws.manager import connection_manager

    result = await create_submission(round_id, body.prompt, current_user.id, session)

    # Broadcast submission created event
    round_ = await session.get(Round, round_id)
    if round_ is not None:
        await connection_manager.broadcast_to_room(
            str(round_.room_id),
            "submission:created",
            {
                "submission_id": str(result.submission.id),
                "participant_id": str(result.submission.participant_id),
                "prompt": result.submission.prompt,
            },
        )
        # Enqueue ARQ job via the shared app-level Redis pool.
        # Wrapped so a transient Redis hiccup, or Redis being unavailable at
        # startup, doesn't crash the request (job is persisted in DB, but
        # won't be processed until Redis is available and the server restarts).
        try:
            redis = request.app.state.redis
            if redis is None:
                raise RuntimeError("Redis pool not initialised (Redis unavailable at startup)")
            await redis.enqueue_job("run_generation_job", str(result.job.id))
            await connection_manager.broadcast_to_room(
                str(round_.room_id),
                "job:queued",
                {"job_id": str(result.job.id), "submission_id": str(result.submission.id)},
            )
        except Exception as exc:
            logger.warning("Failed to enqueue generation job %s: %s", result.job.id, exc)

    return result


@router.get("/submissions/{submission_id}", response_model=SubmissionResponse)
async def get_submission_endpoint(
    submission_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: uuid.UUID = Depends(get_current_user_id),
) -> SubmissionResponse:
    """Fetch a submission and its current generation job status."""
    return await get_submission(submission_id, session)


@router.post("/jobs/{job_id}/retry", response_model=GenerationJobResponse)
async def retry_job_endpoint(
    request: Request,
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GenerationJobResponse:
    """Retry a failed or timed-out generation job.

    Resets the job to `queued`, re-enqueues it in ARQ, and broadcasts
    `job:queued` so all room clients immediately see the updated status.
    """
    from app.ws.manager import connection_manager

    job_response = await retry_job(job_id, current_user.id, session)

    # Use app-level Redis pool — no per-request pool creation
    redis = request.app.state.redis
    if redis is None:
        logger.warning("Redis unavailable — job %s reset to queued but not enqueued.", job_id)
        return job_response
    await redis.enqueue_job("run_generation_job", str(job_id))

    # Broadcast job:queued so all room clients immediately reflect the retry
    from app.submissions.models import Submission
    from sqlalchemy import select

    submission = await session.scalar(
        select(Submission).where(Submission.id == job_response.submission_id)
    )
    if submission is not None:
        from app.rounds.models import Round
        round_ = await session.get(Round, submission.round_id)
        if round_ is not None:
            await connection_manager.broadcast_to_room(
                str(round_.room_id),
                "job:queued",
                {"job_id": str(job_id), "submission_id": str(submission.id)},
            )

    return job_response

