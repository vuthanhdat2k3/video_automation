# Module 8: Pipeline Orchestration — Implementation Plan

## Overview

Module 8 triển khai job queue + worker system để xử lý generation bất đồng bộ thay vì synchronous in-request. Dùng **arq** (Redis-based async task queue, lightweight, không cần Celery broker) + Redis pool. Tất cả generation endpoints sẽ dispatch jobs → poll status → nhận kết quả.

## Current State

- JobModel + JobService (CRUD + lifecycle) đã có trong DB
- Redis chạy trên port 6379 (docker-compose) nhưng chưa có client
- 6 JobType enums đã định nghĩa
- Generation endpoints đang chạy **synchronous** — block request cho tới khi xong
- Chưa có jobs router (frontend gọi `GET /projects/{id}/jobs` → 404)

---

## Step 8.1 — Dependencies

```bash
uv add arq redis[hiredis]
```

- **arq**: async Redis-based task queue (lightweight alternative to Celery)
- **redis**: Redis client với hiredis parser cho performance

---

## Step 8.2 — Redis Client Singleton

**File:** `apps/api/app/services/redis.py` (NEW)

```python
from redis.asyncio import Redis

_pool: Redis | None = None

async def get_redis() -> Redis:
    global _pool
    if _pool is None:
        _pool = Redis.from_url(settings.redis_url, decode_responses=False)
    return _pool
```

Reuse connection pool. `decode_responses=False` vì arq serialize bằng pickle.

---

## Step 8.3 — ARQ Worker Definition

**File:** `apps/api/app/services/worker.py` (NEW)

Define async task functions cho từng JobType:
- `run_generate_background(project_id, shot_id, scene_id)` → BackgroundGenService → save asset → update JobModel
- `run_generate_keyframe(project_id, shot_id, scene_id)` → KeyframeGenService → save asset → update JobModel
- `run_generate_audio(project_id, shot_id)` → TTSService → save asset → update JobModel  
- `run_export_scene(project_id, scene_id)` → ExportService → save mp4 → update JobModel

Each function:
1. Gets a fresh AsyncSession from the session factory
2. Runs generation logic
3. Updates JobModel (status="completed", progress=1.0) or (status="failed", error=str)
4. Updates ShotModel (background_asset_id / keyframe_asset_id / audio_asset_id)

**ARQ WorkerSettings**:
```python
class WorkerSettings:
    functions = [run_generate_background, run_generate_keyframe, run_generate_audio, run_export_scene]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 2  # limit concurrency (GPU-bound ComfyUI)
```

---

## Step 8.4 — ARQ Client + Job Dispatcher

**File:** `apps/api/app/services/queue.py` (NEW)

```python
from arq import ArqRedis

_queue: ArqRedis | None = None

async def get_queue() -> ArqRedis:
    global _queue
    if _queue is None:
        _queue = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _queue

async def dispatch_job(db: AsyncSession, project_id: UUID, job_type: JobType, **kwargs) -> JobRead:
    # 1. Create JobModel via JobService (status="pending")
    # 2. Enqueue arq task with job_id in args
    # 3. Return JobRead for polling
```

---

## Step 8.5 — Jobs Router

**File:** `apps/api/app/routers/jobs.py` (NEW)

| Endpoint | Description |
|----------|-------------|
| `GET /projects/{id}/jobs` | List all jobs for project |
| `GET /jobs/{id}` | Single job detail (status, progress, result) |
| `DELETE /projects/{id}/jobs` | Cancel/delete pending jobs |

---

## Step 8.6 — Refactor Generation Endpoints → Async Dispatch

**File:** `apps/api/app/routers/shots.py` (MODIFY)

Thay vì run synchronous, mỗi endpoint dispatch arq task:

| Endpoint | Before (sync) | After (async dispatch) |
|----------|---------------|------------------------|
| `POST /shots/{id}/generate-background` | Block until ComfyUI done | Returns `{ job_id }` immediately |
| `POST /shots/{id}/generate-keyframe` | Block until done | Returns `{ job_id }` |
| `POST /shots/{id}/generate-audio` | Block until TTS done | Returns `{ job_id }` |
| `POST /scenes/{id}/generate-all-keyframes` | Sequential loop | Creates 1 batch job + N sub-tasks |
| `POST /scenes/{id}/generate-all-audio` | Sequential loop | Creates 1 batch job + N sub-tasks |
| `POST /scenes/{id}/export` | Block until FFmpeg done | Returns `{ job_id }` |

Response format: `{ "data": { "job_id": str }, "error": null }`

Frontend polls `GET /jobs/{job_id}` for status/progress.

---

## Step 8.7 — FastAPI Startup/Shutdown

**File:** `apps/api/app/main.py` (MODIFY)

```python
@app.on_event("startup")
async def startup():
    await get_redis()
    await get_queue()

@app.on_event("shutdown")
async def shutdown():
    # close redis pool
```

---

## Step 8.8 — Worker Entry Point

**File:** `apps/api/worker.py` (NEW)

```python
#!/usr/bin/env python3
"""ARQ worker for pipeline generation tasks."""
from arq import run_worker
from app.services.worker import WorkerSettings
import asyncio

if __name__ == "__main__":
    asyncio.run(run_worker(WorkerSettings))
```

Run with: `uv run python worker.py` (separate process from API server)

---

## Step 8.9 — docker-compose Updates

**File:** `docker-compose.yml` (MODIFY)

```yaml
worker:
  build: ./apps/api
  command: uv run python worker.py
  depends_on: [redis, db]
  environment: *api-env
```

---

## Step 8.10 — Tests

**File:** `apps/api/tests/test_jobs.py` (NEW)

- `POST /shots/{id}/generate-keyframe` returns `{ job_id }`
- `GET /jobs/{id}` shows `status: "pending"` → then `"completed"` after worker runs
- `GET /projects/{id}/jobs` lists jobs
- Worker task integration test (mock ComfyUI + arq pool)
- Batch dispatch creates correct count of jobs

**File:** `apps/api/tests/test_queue.py` (NEW)
- `dispatch_job` creates JobModel with correct type
- Worker task updates ShotModel.background_asset_id on completion

**Target:** ~12 tests

---

## Files Summary

| File | Action |
|------|--------|
| `apps/api/app/services/redis.py` | NEW — Redis connection pool |
| `apps/api/app/services/worker.py` | NEW — arq task functions |
| `apps/api/app/services/queue.py` | NEW — arq client + dispatch |
| `apps/api/app/routers/jobs.py` | NEW — jobs CRUD router |
| `apps/api/app/routers/shots.py` | MODIFY — all gen endpoints → async dispatch |
| `apps/api/app/main.py` | MODIFY — startup/shutdown, register jobs router |
| `apps/api/worker.py` | NEW — worker entry point |
| `docker-compose.yml` | MODIFY — add worker service |
| `apps/api/tests/test_jobs.py` | NEW |
| `apps/api/tests/test_queue.py` | NEW |

---

## Deliverables Checkpoint

```text
□ arq + redis[hiredis] installed
□ Redis client singleton
□ ARQ worker with 4 task functions
□ Job dispatch via arq enqueue
□ Jobs router (list/get/delete)
□ Generation endpoints return {job_id}
□ FastAPI startup/shutdown lifecycle
□ Worker entry point
□ docker-compose worker service
□ ~12 tests
```

---

## Architecture Diagram

```
┌──────────┐    POST /shots/.../generate-*     ┌───────────────────┐
│ Frontend │ ──────────────────────────────────→│   FastAPI Server  │
│ (React)  │                                    │                   │
│          │←─── { job_id } ────────────────────│ dispatch_job()    │
│          │                                    │ → arq.enqueue()   │
│          │    GET /jobs/{id} (poll)           │       │           │
│          │ ──────────────────────────────────→ │       │           │
│          │←─── { status, progress } ──────────│ JobService.get()  │
└──────────┘                                    └───────┼───────────┘
                                                       │
                                                  Redis Queue
                                                       │
                                              ┌────────▼──────────┐
                                              │   ARQ Worker      │
                                              │                   │
                                              │ run_*_task()      │
                                              │ → Generation Svc  │
                                              │ → ComfyUI / TTS   │
                                              │ → Save Asset      │
                                              │ → Update JobModel │
                                              └───────────────────┘
```
