#!/usr/bin/env python3
"""ARQ worker entry point for pipeline generation tasks."""
import asyncio

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
            "cleanup-old-jobs",
            cleanup_cron_task,
            month={1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12},
            day=set(range(1, 32)),
            weekday=set(range(7)),
            hour={0, 6, 12, 18},
            minute={0},
            second={0},
            microsecond=0,
            run_at_startup=True,
            unique=True,
            job_id=None,
            timeout_s=300,
            keep_result_s=None,
            keep_result_forever=False,
            max_tries=None,
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
