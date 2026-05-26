#!/usr/bin/env python3
"""ARQ worker entry point for pipeline generation tasks."""
import asyncio

from arq import run_worker
from arq.connections import RedisSettings

from app.config import settings
from app.services.worker import (
    run_generate_background,
    run_generate_keyframe,
    run_generate_audio,
    run_export_scene,
)


class WorkerSettings:
    functions = [
        run_generate_background,
        run_generate_keyframe,
        run_generate_audio,
        run_export_scene,
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 2
    job_timeout = 600  # 10 minutes max per job


if __name__ == "__main__":
    asyncio.run(run_worker(WorkerSettings))
