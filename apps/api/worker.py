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
    run_lipsync_shot,
)


class WorkerSettings:
    functions = [
        run_generate_background,
        run_generate_keyframe,
        run_generate_audio,
        run_export_scene,
        run_lipsync_shot,
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 2
    job_timeout = 600
    retry_jobs = True
    max_retries = 3
    retry_delay = 30


if __name__ == "__main__":
    asyncio.run(run_worker(WorkerSettings))
