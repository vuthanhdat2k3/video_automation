# Module 13: Render Queue Optimization & Batch Processing — Implementation Plan

## Overview

Module 13 hoàn thiện render queue với batch job grouping, dependency ordering, intermediate progress reporting, enhanced retry (exponential backoff + per-task config), project-level export, periodic cleanup cron, và cancel/delete endpoint. Tất cả FFmpeg/Python only — không thêm infrastructure dependency mới.

## Current State

| Concern | Actual | Gap |
|---------|--------|-----|
| **Batch grouping** | `generate-all-*` loop-dispatch N orphan jobs | No `batch_id`, no parent tracking |
| **Dependencies** | None — jobs run independently | Cannot express "lipsync needs audio first" |
| **Progress** | WebSocket only `job.completed` / `job.failed` | No intermediate `job.progress` events |
| **Retry** | Global: `max_retries=3`, `retry_delay=30` | No exponential backoff, no transient vs permanent, no per-task config |
| **Project export** | `POST /scenes/{id}/export` only | No `POST /projects/{id}/export` |
| **Cleanup** | `cleanup_old_jobs()` exists, never called | No ARQ cron schedule |
| **Cancel** | Jobs router: `GET` only | No `DELETE /projects/{id}/jobs` |
| **Frontend WS** | `useJobProgress` hook built | Needs to handle new `job.progress` + `job.created` events |
| **Tests** | `test_jobs.py` (8 tests) — CRUD only | No worker/queue integration tests |

---

## Step 13.1 — Database Migration: batch_id, depends_on, retry fields

**File:** `apps/api/alembic/versions/0008_add_job_batch_dependency_retry.py` (NEW)

```sql
ALTER TABLE jobs ADD COLUMN batch_id UUID REFERENCES jobs(id) ON DELETE SET NULL;
ALTER TABLE jobs ADD COLUMN depends_on UUID REFERENCES jobs(id) ON DELETE SET NULL;
ALTER TABLE jobs ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE jobs ADD COLUMN error_type VARCHAR(30);
CREATE INDEX idx_jobs_batch_id ON jobs(batch_id);
CREATE INDEX idx_jobs_depends_on ON jobs(depends_on);
```

**File:** `apps/api/app/models/job.py` (MODIFY)

Add to `JobModel`:
```python
batch_id: Mapped[UUID | None] = mapped_column(
    UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True
)
depends_on: Mapped[UUID | None] = mapped_column(
    UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True
)
retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
error_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
```

**File:** `packages/shared/ai_2d_shared/job.py` (MODIFY)

Add to `JobRead`:
```python
batch_id: UUID | None = None
depends_on: UUID | None = None
retry_count: int = 0
error_type: str | None = None
```

**File:** `packages/shared/ai_2d_shared/enums.py` (MODIFY)

Add to `JobType`:
```python
BATCH = "batch"
```

---

## Step 13.2 — Batch Job Grouping

**Goal:** `generate-all-keyframes` / `generate-all-audio` / project export tạo parent batch job theo dõi aggregate progress. Khi tất cả children complete → parent finalize.

**File:** `apps/api/app/services/batch.py` (NEW)

```python
class BatchJobService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_batch(
        self, project_id: UUID, batch_type: str, children: list[dict],
    ) -> tuple[JobRead, list[JobRead]]:
        """Create parent batch job + N children. Returns (parent, children)."""
        job_svc = JobService(self.db)
        parent = await job_svc.create(project_id, JobType.BATCH, {
            "batch_type": batch_type,
            "total": len(children),
            "completed": 0,
            "failed": 0,
        })
        child_jobs = []
        for c in children:
            cj = await job_svc.create(
                project_id, c["job_type"], c.get("input_data", {}),
                batch_id=parent.id, depends_on=c.get("depends_on"),
            )
            child_jobs.append(cj)
        return parent, child_jobs

    async def on_child_complete(self, child_job_id: UUID) -> JobRead | None:
        """Update parent progress. Returns parent if batch fully done."""
        pass

    async def on_child_failed(self, child_job_id: UUID) -> JobRead | None:
        """Update parent failed count. Returns parent if batch fully done."""
        pass
```

**File:** `apps/api/app/services/worker.py` (MODIFY)

In `_complete_job` / `_fail_job`, gọi `BatchJobService.on_child_complete/failed`. Nếu parent finalize → broadcast `job.completed` cho parent:

```python
async def _complete_job(job_id, project_id, output_data=None):
    # ... existing complete logic ...
    async with async_session_factory() as db:
        batch_svc = BatchJobService(db)
        parent = await batch_svc.on_child_complete(UUID(job_id))
    if parent:
        await manager.broadcast(UUID(project_id), {
            "type": "job.completed", "job": parent.model_dump(),
        })
```

**File:** `apps/api/app/services/queue.py` (MODIFY)

`dispatch_job` hỗ trợ `batch_id` và `depends_on`:
```python
async def dispatch_job(db, project_id, job_type, task_name,
                       batch_id=None, depends_on=None, **task_kwargs) -> JobRead:
    job_svc = JobService(db)
    job = await job_svc.create(project_id, job_type, task_kwargs,
                               batch_id=batch_id, depends_on=depends_on)
    # ... enqueue ...
    return job
```

**File:** `apps/api/app/services/job.py` (MODIFY)

`create` method hỗ trợ `batch_id` và `depends_on`:
```python
async def create(self, project_id, job_type, input_data=None,
                 batch_id=None, depends_on=None) -> JobRead:
    job = JobModel(
        project_id=project_id, type=job_type,
        input_json=input_data or {}, status="pending",
        batch_id=batch_id, depends_on=depends_on,
    )
    ...
```

**File:** `apps/api/app/routers/shots.py` (MODIFY)

Refactor `generate_scene_all_keyframes` và `generate_scene_all_audio` dùng `BatchJobService`:

```python
@router.post("/scenes/{scene_id}/generate-all-keyframes")
async def generate_scene_all_keyframes(scene_id, db):
    shots = ...
    batch_svc = BatchJobService(db)
    children = [
        {"task_name": "run_generate_keyframe", "job_type": "generate_keyframe",
         "input_data": {"shot_id": str(shot.id)}}
        for shot in shots
    ]
    parent, child_jobs = await batch_svc.create_batch(
        project_id=scene.project_id, batch_type="generate_all_keyframes",
        children=children,
    )
    # Enqueue all children
    queue = await get_queue()
    for child, shot in zip(child_jobs, shots):
        await queue.enqueue_job(
            "run_generate_keyframe", _job_id=str(child.id),
            project_id=str(scene.project_id), shot_id=str(shot.id),
        )
    return {"data": {"batch_id": str(parent.id), "job_ids": [str(c.id) for c in child_jobs]}}
```

---

## Step 13.3 — Dependency Ordering

**Goal:** Job với `depends_on` set sẽ không execute cho tới khi dependency `completed`. Worker check trước khi execute và requeue nếu dependency chưa sẵn sàng.

**File:** `apps/api/app/services/dependency.py` (NEW)

```python
class DependencyChecker:
    @staticmethod
    async def is_ready(db: AsyncSession, depends_on: UUID) -> bool:
        result = await db.execute(select(JobModel).where(JobModel.id == depends_on))
        dep = result.scalar_one_or_none()
        return dep is not None and dep.status == "completed"

    @staticmethod
    async def is_blocked(db: AsyncSession, depends_on: UUID) -> bool:
        result = await db.execute(select(JobModel).where(JobModel.id == depends_on))
        dep = result.scalar_one_or_none()
        return dep is not None and dep.status == "failed"

class DependencyFailedError(Exception):
    pass

class RequeueWithDelayError(Exception):
    def __init__(self, delay: int = 30):
        self.delay = delay
        super().__init__(f"Requeue with {delay}s delay")
```

**File:** `apps/api/app/services/worker.py` (MODIFY)

Add `_check_dependency` gọi từ mỗi task function:

```python
async def _check_dependency(ctx, project_id: str) -> None:
    job_id = ctx.get("job_id")
    async with async_session_factory() as db:
        job = await db.get(JobModel, UUID(job_id))
        if not job or not job.depends_on:
            return
        if await DependencyChecker.is_blocked(db, job.depends_on):
            await _fail_job(job_id, project_id, f"Dependency {job.depends_on} failed")
            raise DependencyFailedError(f"Dependency {job.depends_on} failed")
        if not await DependencyChecker.is_ready(db, job.depends_on):
            raise RequeueWithDelayError(30)
```

Mỗi task function thêm dòng đầu:
```python
async def run_lipsync_shot(ctx, project_id: str, shot_id: str) -> bool:
    await _check_dependency(ctx, project_id)
    # ... existing logic ...
```

**File:** `apps/api/app/routers/shots.py` (MODIFY)

`generate_shot_lipsync` tự động tìm audio job gần nhất làm dependency:

```python
@router.post("/shots/{shot_id}/generate-lipsync")
async def generate_shot_lipsync(shot_id, db):
    # Find most recent completed audio job for this shot
    audio_job_result = await db.execute(
        select(JobModel)
        .where(JobModel.type == "generate_audio")
        .where(JobModel.status == "completed")
        .where(JobModel.input_json["shot_id"].astext == str(shot_id))
        .order_by(JobModel.created_at.desc())
        .limit(1)
    )
    audio_job = audio_job_result.scalar_one_or_none()

    job = await dispatch_job(
        db=db, project_id=scene.project_id,
        job_type="lipsync", task_name="run_lipsync_shot",
        shot_id=shot_id,
        depends_on=audio_job.id if audio_job else None,
    )
```

---

## Step 13.4 — Intermediate Progress Updates

**Goal:** Workers broadcast `job.progress` events qua WebSocket trong quá trình generation. Frontend hiển thị live progress bar.

**File:** `apps/api/app/services/worker.py` (MODIFY)

Add helper:
```python
async def _update_progress(job_id: str | None, project_id: str, progress: float) -> None:
    if not job_id:
        return
    async with async_session_factory() as db:
        svc = JobService(db)
        result = await svc.update_status(UUID(job_id), "in_progress", progress)
    await manager.broadcast(UUID(project_id), {
        "type": "job.progress",
        "job": result.model_dump(),
    })
```

Annotate mỗi task với progress checkpoints:

| Task | Checkpoints |
|------|-------------|
| `run_generate_background` | 0.1 (start), 0.5 (prompt), 0.9 (image done) |
| `run_generate_keyframe` | 0.1 (start), 0.3 (prompt), 0.7 (image), 0.9 (saved) |
| `run_generate_audio` | 0.1 (start), 0.5 (TTS called), 0.9 (saved) |
| `run_export_scene` | 0.1 (start), 0.3 (clips built), 0.6 (ffmpeg done), 0.9 (saved) |
| `run_lipsync_shot` | 0.1 (start), 0.4 (assets loaded), 0.8 (MuseTalk done), 0.95 (saved) |

```python
async def run_generate_keyframe(ctx, project_id: str, shot_id: str) -> bool:
    job_id = ctx.get("job_id")
    await _check_dependency(ctx, project_id)
    await _update_progress(job_id, project_id, 0.1)

    async with async_session_factory() as db:
        kf_svc = KeyframeGenService(db)
        await _update_progress(job_id, project_id, 0.3)
        png, prompt = await kf_svc.generate_for_shot(UUID(shot_id))
        await _update_progress(job_id, project_id, 0.7)

        # ... save asset ...
        await _update_progress(job_id, project_id, 0.9)

    await _complete_job(job_id, project_id, ...)
```

**File:** `apps/dashboard/src/hooks/useJobProgress.ts` (MODIFY)

Thêm `job.progress` handling (nếu chưa có):
```typescript
interface JobEvent {
  type: 'init' | 'job.completed' | 'job.failed' | 'job.created' | 'job.progress';
  job?: JobRead;
  jobs?: JobRead[];
}
```

---

## Step 13.5 — Enhanced Retry với Exponential Backoff

**Goal:** Per-task retry config, phân biệt transient vs permanent errors, exponential backoff.

**File:** `apps/api/app/services/retry.py` (NEW)

```python
class ErrorClass(str, Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"

TRANSIENT_PATTERNS = [
    "timeout", "connection refused", "out of memory",
    "CUDA out of memory", "temporarily unavailable",
]
PERMANENT_PATTERNS = [
    "not found", "invalid", "unsupported", "permission denied",
]

def classify_error(error: Exception) -> ErrorClass:
    msg = str(error).lower()
    for pat in PERMANENT_PATTERNS:
        if pat in msg:
            return ErrorClass.PERMANENT
    return ErrorClass.TRANSIENT

TASK_RETRY_CONFIG = {
    "run_generate_background": {"max_retries": 3, "base_delay": 30, "backoff": 2.0},
    "run_generate_keyframe":   {"max_retries": 3, "base_delay": 30, "backoff": 2.0},
    "run_generate_audio":      {"max_retries": 3, "base_delay": 15, "backoff": 2.0},
    "run_export_scene":        {"max_retries": 2, "base_delay": 30, "backoff": 2.0},
    "run_lipsync_shot":        {"max_retries": 2, "base_delay": 60, "backoff": 2.0},
}

def get_retry_delay(task_name: str, retry_count: int) -> int:
    config = TASK_RETRY_CONFIG.get(task_name, {"base_delay": 30, "backoff": 2.0})
    return config["base_delay"] * (config["backoff"] ** retry_count)
```

**File:** `apps/api/app/services/worker.py` (MODIFY)

Wrap error handling cho mỗi task — mỗi task dùng pattern giống nhau. Extract thành wrapper function để tránh lặp code:

```python
async def _handle_task_error(ctx, project_id: str, job_id: str, task_name: str, error: Exception):
    error_class = classify_error(error)
    config = TASK_RETRY_CONFIG.get(task_name, {"max_retries": 3, "base_delay": 30, "backoff": 2.0})
    retry_count = ctx.get("job_try", 0)

    async with async_session_factory() as db:
        await db.execute(
            update(JobModel).where(JobModel.id == UUID(job_id))
            .values(error_type=error_class.value, retry_count=retry_count)
        )
        await db.commit()

    if error_class == ErrorClass.PERMANENT or retry_count >= config["max_retries"]:
        await _fail_job(job_id, project_id, f"Max retries exceeded: {error}")
    raise
```

**File:** `apps/api/worker.py` (MODIFY)

Giữ `retry_jobs = True` nhưng giảm global `max_retries` xuống 1 (application-level retry logic trong `retry.py`):

```python
class WorkerSettings:
    # ... existing config ...
    retry_jobs = True
    max_retries = 10          # Allow application-level retry decisions; we control max in retry.py
    retry_delay = 5           # Small constant delay; exponential backoff handled in retry.py
```

---

## Step 13.6 — DELETE /projects/{id}/jobs + Project-Level Export

**File:** `apps/api/app/routers/jobs.py` (MODIFY)

```python
@router.delete("/projects/{project_id}/jobs", response_model=dict)
async def cancel_project_jobs(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """Cancel all pending/queued/in-progress jobs for a project."""
    result = await db.execute(
        select(JobModel).where(
            JobModel.project_id == project_id,
            JobModel.status.in_(["pending", "queued", "in_progress"]),
        )
    )
    jobs = result.scalars().all()
    for job in jobs:
        job.status = "cancelled"
        job.error = "Cancelled by user"
    await db.commit()
    return {"data": {"cancelled": len(jobs)}, "error": None}
```

**File:** `apps/api/app/routers/projects.py` (MODIFY)

```python
@router.post("/projects/{project_id}/export", response_model=dict, status_code=status.HTTP_201_CREATED)
async def export_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """Export entire project: dispatch scene exports as batch, concat after."""
    scene_result = await db.execute(
        select(SceneModel).where(SceneModel.project_id == project_id).order_by(SceneModel.order_index)
    )
    scenes = scene_result.scalars().all()
    if not scenes:
        raise NotFoundException("No scenes to export")

    batch_svc = BatchJobService(db)
    children = [
        {"task_name": "run_export_scene", "job_type": "export",
         "input_data": {"scene_id": str(s.id)}}
        for s in scenes
    ]
    parent, child_jobs = await batch_svc.create_batch(
        project_id=project_id, batch_type="export_project", children=children,
    )

    queue = await get_queue()
    for child, scene in zip(child_jobs, scenes):
        await queue.enqueue_job(
            "run_export_scene", _job_id=str(child.id),
            project_id=str(project_id), scene_id=str(scene.id),
        )

    # Concatenation job depends on batch parent completing
    concat_job = await dispatch_job(
        db=db, project_id=project_id,
        job_type="export", task_name="run_concat_project",
        project_id=project_id, depends_on=parent.id,
    )

    return {"data": {"batch_id": str(parent.id), "concat_job_id": str(concat_job.id),
                     "scene_count": len(scenes)}, "error": None}
```

**File:** `apps/api/app/services/worker.py` (MODIFY)

Add `run_concat_project` task:
```python
async def run_concat_project(ctx, project_id: str) -> bool:
    """Concatenate all scene exports into final project MP4."""
    job_id = ctx.get("job_id")
    await _check_dependency(ctx, project_id)
    await _update_progress(job_id, project_id, 0.1)

    async with async_session_factory() as db:
        # Load all completed exports for this project (from batch job output)
        job = await db.get(JobModel, UUID(job_id))
        batch_job = await db.get(JobModel, job.depends_on)

        await _update_progress(job_id, project_id, 0.3)

        # Collect export asset paths from batch job children
        child_result = await db.execute(
            select(JobModel).where(JobModel.batch_id == job.depends_on)
        )
        children = child_result.scalars().all()
        export_paths = []
        for child in children:
            if child.output_json and child.output_json.get("asset_id"):
                asset = await db.get(AssetModel, UUID(child.output_json["asset_id"]))
                if asset:
                    export_paths.append(storage.get_asset_path(UUID(project_id), asset.path))

        await _update_progress(job_id, project_id, 0.5)

        # FFmpeg concat
        import tempfile, asyncio, subprocess
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            filelist = tmp / "filelist.txt"
            output = tmp / f"project_{project_id}_final.mp4"

            with open(filelist, "w") as f:
                for p in export_paths:
                    f.write(f"file '{p}'\n")

            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(filelist), "-c", "copy", str(output),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            await proc.wait()

            await _update_progress(job_id, project_id, 0.9)

            mp4_bytes = output.read_bytes()
            asset = await save_generated_asset(
                db=db, project_id=UUID(project_id),
                asset_type=AssetType.EXPORT.value,
                filename=f"project_{project_id}_final.mp4",
                data=mp4_bytes,
                metadata={"project_id": project_id, "scene_count": len(export_paths)},
            )
            await db.commit()

    await _complete_job(job_id, project_id, {"asset_id": str(asset.id)})
    return True
```

**File:** `apps/api/worker.py` (MODIFY)

Add `run_concat_project` to `WorkerSettings.functions`.

---

## Step 13.7 — Periodic Cleanup via ARQ Cron

**Goal:** Gọi `cleanup_old_jobs()` định kỳ mỗi 6 giờ qua ARQ cron job.

**File:** `apps/api/app/services/cleanup.py` (MODIFY)

```python
async def cleanup_cron_task(ctx) -> None:
    """ARQ cron task: clean up completed/failed jobs older than 7 days."""
    async with async_session_factory() as db:
        deleted = await cleanup_old_jobs(db, max_age_hours=168)
        logger.info("cleanup_cron_task completed", extra={"deleted_count": deleted})
```

**File:** `apps/api/worker.py` (MODIFY)

```python
from app.services.cleanup import cleanup_cron_task

class WorkerSettings:
    functions = [..., cleanup_cron_task]
    cron_jobs = [
        CronJob(
            task=cleanup_cron_task,
            run_every=timedelta(hours=6),
            run_at_startup=True,
        ),
    ]
```

---

## Step 13.8 — Tests

**File:** `apps/api/tests/test_batch.py` (NEW)

1. `test_create_batch_parent_and_children` — `BatchJobService.create_batch(3 children)` → parent `type="batch"`, 3 children with `batch_id`
2. `test_batch_progress_aggregation` — 3 children complete → parent progress 1.0, status "completed"
3. `test_batch_partial_failure` — 1 failed + 2 completed → parent still "completed" with failed count
4. `test_child_with_dependency_requeues` — Child with unresolved `depends_on` raises `RequeueWithDelayError`
5. `test_child_with_failed_dependency_aborts` — Child with failed `depends_on` → `_fail_job` called with dependency error
6. `test_progress_updates_broadcast` — `_update_progress(0.5)` → WebSocket broadcast with `job.progress` event
7. `test_retry_classify_transient` — `classify_error(TimeoutError("connection refused"))` → `TRANSIENT`
8. `test_retry_classify_permanent` — `classify_error(ValueError("not found"))` → `PERMANENT`
9. `test_cancel_jobs_endpoint` — `DELETE /projects/{id}/jobs` → all pending jobs status "cancelled"
10. `test_project_export_creates_batch` — `POST /projects/{id}/export` → returns `batch_id` + `concat_job_id`

**Target:** ~10 tests

---

## Files Summary

| File | Action |
|------|--------|
| `apps/api/alembic/versions/0008_add_job_batch_dependency_retry.py` | NEW — migration |
| `apps/api/app/models/job.py` | MODIFY — batch_id, depends_on, retry_count, error_type |
| `apps/api/app/services/batch.py` | NEW — batch parent/child lifecycle |
| `apps/api/app/services/dependency.py` | NEW — dependency checker |
| `apps/api/app/services/retry.py` | NEW — error classification + exponential backoff |
| `apps/api/app/services/worker.py` | MODIFY — progress updates, dependency check, retry wrap, run_concat_project |
| `apps/api/app/services/queue.py` | MODIFY — batch_id + depends_on in dispatch |
| `apps/api/app/services/job.py` | MODIFY — batch_id + depends_on in create |
| `apps/api/app/services/cleanup.py` | MODIFY — cron task wrapper |
| `apps/api/app/routers/jobs.py` | MODIFY — DELETE cancel endpoint |
| `apps/api/app/routers/projects.py` | MODIFY — POST /projects/{id}/export |
| `apps/api/app/routers/shots.py` | MODIFY — batch dispatch, lip-sync auto-dependency |
| `apps/api/worker.py` | MODIFY — add run_concat_project + cron_jobs |
| `packages/shared/ai_2d_shared/job.py` | MODIFY — batch_id, depends_on, retry_count, error_type |
| `packages/shared/ai_2d_shared/enums.py` | MODIFY — JobType.BATCH |
| `apps/dashboard/src/hooks/useJobProgress.ts` | MODIFY — handle job.progress event |
| `apps/api/tests/test_batch.py` | NEW — ~10 tests |

---

## Deliverables Checkpoint

```text
□ Migration 0008 — batch_id, depends_on, retry_count, error_type on jobs
□ BatchJobService — parent batch creation + child progress aggregation
□ DependencyChecker — prerequisite validation before task execution
□ Auto-dependency: lipsync → audio job
□ Intermediate progress updates via WebSocket (5 checkpoints per task type)
□ Error classification (transient vs permanent) + exponential backoff retry
□ Per-task retry config (max_retries, base_delay, backoff multiplier)
□ DELETE /projects/{id}/jobs — cancel pending jobs
□ POST /projects/{id}/export — project-level batch export + concat
□ run_concat_project worker task — FFmpeg concat all scene exports
□ ARQ cron: cleanup_old_jobs every 6 hours
□ Frontend useJobProgress updated for job.progress event
□ ~10 tests
```

---

## Architecture Diagram (Updated)

```
┌──────────────┐  POST /shots/{id}/generate-*
│   Frontend   │ ────────────────────────────┐
│  (React +    │                              │
│   WebSocket) │  WS /projects/{id}          ▼
│              │◄────────────────────┌───────────────┐
│ useJobProgress                    │  FastAPI       │
│  - job.progress                  │   dispatch_job │
│  - job.completed                 │   → batch parent│
│  - job.failed                    │   → N children │
└──────────────┘                   └───┬───────────┘
                                       │
                                  Redis Queue
                                       │
                               ┌───────▼──────────────┐
                               │   ARQ Worker (max=2) │
                               │                      │
                               │ 1. _check_dependency │
                               │ 2. _update_progress  │
                               │ 3. run_*_task()     │
                               │ 4. classify_error    │
                               │ 5. _complete_job     │
                               │    → Batch.on_child  │
                               │    → WS broadcast    │
                               └──────────────────────┘
                                       │
                               ┌───────▼──────────────┐
                               │   Cron (every 6h)    │
                               │   cleanup_old_jobs() │
                               └──────────────────────┘
```
