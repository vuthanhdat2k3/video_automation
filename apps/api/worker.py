#!/usr/bin/env python3
"""ARQ worker entry point for pipeline generation tasks."""
import asyncio
from datetime import timedelta

from arq import run_worker
from arq.connections import RedisSettings
from arq.cron import CronJob

from app.config import settings
from app.services.worker import (
    run_generate_background,
    run_generate_keyframe,
    run_generate_audio,
    run_export_scene,
    run_lipsync_shot,
    run_concat_project,
)
from app.services.cleanup import cleanup_cron_task


class WorkerSettings:
    functions = [
        run_generate_background,
        run_generate_keyframe,
        run_generate_audio,
        run_export_scene,
        run_lipsync_shot,
        run_concat_project,
        cleanup_cron_task,
    ]
    cron_jobs = [
        CronJob(
            task=cleanup_cron_task,
            run_every=timedelta(hours=6),
            run_at_startup=True,
        ),
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 2
    job_timeout = 600
    retry_jobs = True
    max_retries = 3
    retry_delay = 30


if __name__ == "__main__":
    asyncio.run(run_worker(WorkerSettings))
