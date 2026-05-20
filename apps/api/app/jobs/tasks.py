"""ARQ async task: run AI generation for a queued job."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.ai import get_ai_provider
from app.ai.base import ProviderError
from app.database import AsyncSessionLocal
from app.enums import JobStatus
from app.submissions.models import GenerationJob, Submission

logger = logging.getLogger(__name__)

_JOB_TIMEOUT_SECONDS = 30


async def _broadcast(room_id: str, event: str, data: dict) -> None:
    """Helper to broadcast a WebSocket event from within the ARQ worker."""
    from app.ws.manager import connection_manager
    await connection_manager.broadcast_to_room(room_id, event, data)


async def run_generation_job(ctx: dict, job_id: str) -> None:
    """ARQ task entry point. Manages the full generation lifecycle for a job.

    Lifecycle:
        queued → running → completed | failed | timed_out

    Args:
        ctx: ARQ worker context (unused directly).
        job_id: The UUID string of the GenerationJob to process.
    """
    job_uuid = uuid.UUID(job_id)
    logger.info("Starting generation job %s", job_id)

    async with AsyncSessionLocal() as session:
        # Fetch job with submission and its room via round
        stmt = (
            select(GenerationJob)
            .where(GenerationJob.id == job_uuid)
            .options(
                selectinload(GenerationJob.submission).selectinload(Submission.round)
            )
        )
        job = await session.scalar(stmt)

        if job is None:
            logger.error("Job %s not found in database", job_id)
            return

        submission = job.submission
        round_ = submission.round

        # Fetch room for challenge context and room_id (for WS broadcast)
        from app.rooms.models import Room
        room = await session.get(Room, round_.room_id)
        if room is None:
            logger.error("Room for job %s not found", job_id)
            return

        room_id_str = str(room.id)

        # Transition → running
        job.status = JobStatus.running
        job.started_at = datetime.now(timezone.utc)
        await session.commit()
        await _broadcast(room_id_str, "job:running", {"job_id": job_id})

        # Run generation with timeout
        provider = get_ai_provider()
        try:
            generated_output = await asyncio.wait_for(
                provider.generate(submission.prompt, room.challenge_prompt),
                timeout=_JOB_TIMEOUT_SECONDS,
            )

            # Re-fetch to avoid stale state after await
            job = await session.get(GenerationJob, job_uuid)
            submission = await session.get(Submission, submission.id)
            if job is None or submission is None:
                return

            submission.generated_output = generated_output
            job.status = JobStatus.completed
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()

            logger.info("Job %s completed successfully", job_id)
            await _broadcast(
                room_id_str,
                "job:completed",
                {
                    "job_id": job_id,
                    "submission_id": str(submission.id),
                    "output": generated_output,
                },
            )

        except asyncio.TimeoutError:
            job = await session.get(GenerationJob, job_uuid)
            if job:
                job.status = JobStatus.timed_out
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()
            logger.warning("Job %s timed out after %ds", job_id, _JOB_TIMEOUT_SECONDS)
            await _broadcast(room_id_str, "job:timed_out", {"job_id": job_id})

        except ProviderError as exc:
            job = await session.get(GenerationJob, job_uuid)
            if job:
                job.status = JobStatus.failed
                job.error_message = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()
            logger.error("Job %s failed: %s", job_id, exc)
            await _broadcast(
                room_id_str,
                "job:failed",
                {"job_id": job_id, "error_message": str(exc)},
            )

        except Exception as exc:
            job = await session.get(GenerationJob, job_uuid)
            if job:
                job.status = JobStatus.failed
                job.error_message = f"Unexpected error: {exc}"
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()
            logger.exception("Unexpected error in job %s", job_id)
            await _broadcast(
                room_id_str,
                "job:failed",
                {"job_id": job_id, "error_message": "An unexpected error occurred."},
            )
