# Module 9: WebSocket Progress & Resilience — Implementation Plan

## Overview

Module 9 hoàn thiện pipeline orchestration với WebSocket push cho real-time job status (thay polling), retry policy cho worker tasks, structured logging, và job cleanup. Frontend nhận live updates qua WebSocket thay vì poll `GET /jobs/{id}`.

---

## Step 9.1 — WebSocket Service

**File:** `apps/api/app/services/websocket.py` (NEW)

```python
class JobProgressManager:
    """Manages WebSocket connections per project for job progress updates."""
    _connections: dict[str, set[WebSocket]]  # project_id -> connected clients

    async def connect(project_id: UUID, ws: WebSocket) -> None
    async def disconnect(project_id: UUID, ws: WebSocket) -> None
    async def broadcast(project_id: UUID, event: dict) -> None
```

Events: `job.created`, `job.progress`, `job.completed`, `job.failed`.

---

## Step 9.2 — WebSocket Router

**File:** `apps/api/app/routers/ws.py` (NEW)

**Endpoint:** `WS /api/v1/ws/projects/{project_id}`
- Accept WebSocket connection
- Send initial state (all active jobs for project)
- Stream updates as jobs progress

---

## Step 9.3 — Integrate WebSocket into Worker Tasks

**File:** `apps/api/app/services/worker.py` (MODIFY)

After job lifecycle transitions, push events through `JobProgressManager`:
- `_complete_job` → broadcast `job.completed`
- `_fail_job` → broadcast `job.failed`
- During generation (if measurable progress) → broadcast `job.progress`

---

## Step 9.4 — Retry Policy

**File:** `apps/api/app/services/worker.py` (MODIFY)

Define per-task retry config via ARQ's built-in `max_retries`:

```python
# WorkerSettings
retry_jobs: True
max_retries: 3
retry_delay: 30  # seconds between retries
```

Per-task overrides via `@arq.task` decorator or explicit retry raise in code.

---

## Step 9.5 — Structured Logging

**File:** `apps/api/app/logging.py` (NEW)

- JSON-formatted structured logs
- Request ID injection via middleware
- Log levels: DEBUG (development), INFO (production)
- Key events: `job_enqueued`, `job_started`, `job_completed`, `job_failed`, `job_retry`

---

## Step 9.6 — Frontend WebSocket Hook

**File:** `apps/dashboard/src/hooks/useJobProgress.ts` (NEW)

```ts
function useJobProgress(projectId: string) {
    // Connect to WS /api/v1/ws/projects/{projectId}
    // Returns: { jobs: JobWithProgress[], connected: boolean }
    // Auto-reconnect on disconnect
}
```

---

## Step 9.7 — Dashboard Updates

**Files:** MODIFY
- `Timeline.tsx` — replace polling with WebSocket live updates
- `ShotEditor.tsx` — live progress badges via WebSocket
- `ExportPanel.tsx` — real-time export progress

Replace existing `useQuery` polling intervals with WebSocket-driven state.

---

## Step 9.8 — Job Cleanup

**File:** `apps/api/app/services/cleanup.py` (NEW)

Background task on worker startup:
- Clean jobs older than 7 days (configurable)
- Delete associated asset files from storage
- Run on worker startup + periodic (every hour)

```python
async def cleanup_old_jobs(ctx, max_age_hours: int = 168):
    # Delete jobs older than max_age_hours
    # Remove orphaned assets
```

---

## Step 9.9 — Tests

**File:** `apps/api/tests/test_websocket.py` (NEW)

- WebSocket connect/disconnect
- Broadcast on job create/completion/failure
- Client receives correct event format

**File:** `apps/api/tests/test_retry.py` (NEW)

- Worker task retries on transient failure
- Max retries exceeded → job.status = "failed"
- Retry delay works correctly

**Target:** ~10 tests

---

## Files Summary

| File | Action |
|------|--------|
| `apps/api/app/services/websocket.py` | NEW — WebSocket manager |
| `apps/api/app/routers/ws.py` | NEW — WebSocket endpoint |
| `apps/api/app/services/worker.py` | MODIFY — WS broadcast + retry config |
| `apps/api/app/logging.py` | NEW — structured logging |
| `apps/api/app/main.py` | MODIFY — register WS router |
| `apps/api/app/services/cleanup.py` | NEW — job cleanup |
| `apps/dashboard/src/hooks/useJobProgress.ts` | NEW — WebSocket hook |
| `apps/dashboard/src/pages/Timeline.tsx` | MODIFY — live updates |
| `apps/dashboard/src/pages/ShotEditor.tsx` | MODIFY — live updates |
| `apps/dashboard/src/pages/ExportPanel.tsx` | MODIFY — live updates |
| `apps/api/tests/test_websocket.py` | NEW |
| `apps/api/tests/test_retry.py` | NEW |

---

## Deliverables Checkpoint

```text
□ WebSocket manager per project
□ WS /api/v1/ws/projects/{id} endpoint
□ Worker tasks broadcast job lifecycle events
□ ARQ retry policy (3 retries, 30s delay)
□ Structured JSON logging
□ Frontend useJobProgress hook
□ Dashboard live updates (no more polling)
□ Job cleanup for old records
□ ~10 tests
```
