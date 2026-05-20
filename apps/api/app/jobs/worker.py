"""ARQ worker settings and entry point."""

from arq.connections import RedisSettings

from app.config import get_settings
from app.jobs.tasks import run_generation_job  # noqa: F401 — imported to register with ARQ


def _get_redis_settings() -> RedisSettings:
    settings = get_settings()
    return RedisSettings.from_dsn(settings.redis_url)


class WorkerSettings:
    """ARQ worker configuration.

    Run with: arq app.jobs.worker.WorkerSettings
    """

    functions = [run_generation_job]
    redis_settings = _get_redis_settings()
    max_jobs = 10
    job_timeout = 60  # seconds — outer ARQ timeout (inner task timeout is 30s)
    keep_result = 3600  # keep job results for 1 hour
    queue_name = "arq:default"
