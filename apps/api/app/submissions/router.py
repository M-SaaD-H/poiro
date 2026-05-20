"""Submissions router: submit prompts, fetch results, retry failed jobs."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_current_user_id
from app.auth.models import User
from app.database import get_session
from app.submissions.schemas import CreateSubmissionRequest, GenerationJobResponse, SubmissionResponse, SubmissionWithJobResponse
from app.submissions.service import create_submission, get_submission, retry_job

router = APIRouter(tags=["submissions"])


@router.post(
    "/rounds/{round_id}/submissions",
    response_model=SubmissionWithJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_prompt(
    round_id: uuid.UUID,
    body: CreateSubmissionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SubmissionWithJobResponse:
    """Submit a creative prompt for the active round. Enqueues an AI generation job."""
    from app.ws.manager import connection_manager
    import arq

    result = await create_submission(round_id, body.prompt, current_user.id, session)
    await session.commit()

    # Broadcast submission created event
    round_ = await session.get(__import__("app.rounds.models", fromlist=["Round"]).Round, round_id)
    if round_ is not None:
        await connection_manager.broadcast_to_room(
            str(round_.room_id),
            "submission:created",
            {
                "submission_id": str(result.submission.id),
                "participant_id": str(result.submission.participant_id),
            },
        )
        # Enqueue ARQ job
        from app.config import get_settings
        settings = get_settings()
        redis = await arq.create_pool(arq.connections.RedisSettings.from_dsn(settings.redis_url))
        await redis.enqueue_job("run_generation_job", str(result.job.id))
        await redis.aclose()

        await connection_manager.broadcast_to_room(
            str(round_.room_id),
            "job:queued",
            {"job_id": str(result.job.id), "submission_id": str(result.submission.id)},
        )

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
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GenerationJobResponse:
    """Retry a failed or timed-out generation job."""
    import arq
    from app.config import get_settings

    job_response = await retry_job(job_id, current_user.id, session)
    await session.commit()

    settings = get_settings()
    redis = await arq.create_pool(arq.connections.RedisSettings.from_dsn(settings.redis_url))
    await redis.enqueue_job("run_generation_job", str(job_id))
    await redis.aclose()

    return job_response
