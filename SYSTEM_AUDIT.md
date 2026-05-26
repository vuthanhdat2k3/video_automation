# Pipeline Video Automation — System Completion Audit

**Date**: 2026-05-26
**Revision**: post-Module 13

---

## Tổng quan

| Hạng mục | Trạng thái |
|----------|-----------|
| Total Modules (planned) | 13 |
| Modules Implemented | 13 ✅ |
| API Endpoints | 44/44 ✅ |
| Worker Tasks (registered) | 5/7 ⚠️ |
| Database Migrations | 8/8 ✅ |
| Test Suite | 137 passed, 2 skipped, 1 warning |
| Frontend Pages | 8/8 ✅ |
| CLI Tooling | Minimal (2 scripts) ⚠️ |

---

## 1. Back-end: Những gì đã hoàn thành

### Database (PostgreSQL)
- 8 migrations (`0001` → `0008`) phủ toàn bộ schema
- Models: `Project`, `Character`, `Scene`, `Shot`, `Job`, `Asset`
- Migration 0008 bổ sung `batch_id`, `depends_on`, `retry_count`, `error_type` cho `jobs`

### API Routers (44 endpoints)
- **Projects**: CRUD + export dự án (batch tất cả scene + concat cuối)
- **Scenes**: CRUD + reorder + timeline
- **Shots**: CRUD + reorder + generate background/keyframe/audio + batch generate-all + export scene + lipsync (auto-depend audio)
- **Characters**: CRUD + generate image/expression + set primary asset
- **Assets**: List, download, delete
- **Story Bible**: Generate/regenerate/materialize (LLM)
- **Jobs**: List, get status, cancel pending/in-progress
- **WebSocket**: Per-project live push (job progress broadcast)
- **Health**: GET liveness check

### Services (28 files)
| Service | Module | Status |
|---------|--------|--------|
| `project.py` | 1 | ✅ Hoàn chỉnh |
| `story.py` | 2 | ✅ Hoàn chỉnh (LLM integration) |
| `character.py` | 3 | ✅ Hoàn chỉnh |
| `scene.py` | 4 | ✅ Hoàn chỉnh |
| `shot.py` | 4 | ✅ Hoàn chỉnh |
| `background_gen.py` | 5 | ✅ Hoàn chỉnh (ComfyUI) |
| `keyframe_gen.py` | 5 | ✅ Hoàn chỉnh (ComfyUI) |
| `tts.py` | 6 | ✅ Hoàn chỉnh (edge_tts) |
| `exporter.py` | 6 | ✅ Hoàn chỉnh (FFmpeg MP4) |
| `redis.py` | 8 | ✅ Hoàn chỉnh |
| `websocket.py` | 9 | ✅ Hoàn chỉnh |
| `cleanup.py` | 9 | ✅ Hoàn chỉnh |
| `job.py` | 8 | ✅ Hoàn chỉnh |
| `queue.py` | 8 | ✅ Hoàn chỉnh (ARQ dispatch) |
| `worker.py` | 8 | ⚠️ Thiếu 2 task (xem mục 3) |
| `batch.py` | 13 | ✅ Hoàn chỉnh |
| `dependency.py` | 13 | ✅ Hoàn chỉnh |
| `retry.py` | 13 | ✅ Hoàn chỉnh |
| `prompts.py` | 2 | ✅ Hoàn chỉnh |
| `comfyui.py` | 3,5 | ✅ Hoàn chỉnh |
| `character_gen.py` | 3 | ✅ Hoàn chỉnh |
| `storage.py` | - | ✅ Hoàn chỉnh (shared) |

### Post-production Services (EXIST but EMPTY)
| Service | File | Trạng thái |
|---------|------|-----------|
| Camera motion | `services/camera.py` | ❌ Import-only skeleton, no logic |
| Subtitle overlay | `services/subtitle.py` | ❌ Import-only skeleton, no logic |
| Transition xfade | `services/transition.py` | ❌ Import-only skeleton, no logic |
| Audio mixer | `services/audio_mixer.py` | ❌ Import-only skeleton, no logic |
| Color grading | `services/color_grade.py` | ❌ Import-only skeleton, no logic |
| Character shadow | `services/shadow.py` | ❌ Import-only skeleton, no logic |
| VFX overlay | `services/vfx_overlay.py` | ❌ Import-only skeleton, no logic |
| Lip sync | `services/lipsync.py` | ✅ Có logic (MuseTalk wrapper + fallback) |

---

## 2. CRITICAL: Missing Worker Tasks

### `run_concat_project` — **KHÔNG TỒN TẠI**

- Được dispatch từ `POST /api/v1/projects/{id}/export`
- Có retry config trong `retry.py`
- **Không có function body trong `worker.py`**
- **Không được đăng ký trong `WorkerSettings.functions`**
- **Kết quả**: Runtime error khi export project

### `cleanup_cron_task` — **KHÔNG TỒN TẠI**

- Được đề cập trong PLAN_MODULE_13
- **Không được implement**

### Đã fix trong lần review này

- `Path` import missing trong `worker.py` (dùng trong `run_lipsync_shot` nhưng không import)

---

## 3. Front-end: Những gì còn thiếu

### Đã có (8 pages)
- `ProjectList` — CRUD projects ✅
- `StoryEditor` — generate/regenerate/materialize ✅
- `CharacterList` + `CharacterEditor` ✅
- `Timeline` — scenes→shots grid, batch generate, WS live ✅
- `ShotEditor` — per-shot generate + export ✅
- `ExportPanel` — per-scene readiness check + export ✅

### Còn thiếu
| Feature | Priority |
|---------|----------|
| **Lip Sync trigger button** (backend có endpoint `POST /shots/{id}/generate-lipsync`) | HIGH |
| **Progress bars** (backend có WebSocket progress broadcast, frontend chưa hiển thị) | HIGH |
| **Download exported MP4** (backend trả asset, frontend không có link tải) | HIGH |
| **Project-level export button** (`POST /projects/{id}/export` có backend, không có UI) | MEDIUM |
| **Batch parent status UI** (backend có `BatchJobService`, frontend không hiển thị) | MEDIUM |
| **Post-production controls** (Camera/Subtitle/Transition/Color Grade/VFX — backend chưa có logic thật) | LOW |
| Responsive/mobile layout | LOW |
| E2E tests (Playwright) | LOW |
| Unit tests (Vitest) | LOW |

---

## 4. CLI Tooling

Hiện tại chỉ có 2 script thủ công:
- `scripts/generate_story.py` (argparse)
- `scripts/seed_demo_project.py` (raw Python)

**Không có**:
- `apps/cli/` directory
- `click` hoặc `typer` framework
- `console_scripts` entry points trong `pyproject.toml`
- Migration CLI wrapper ngoài `alembic upgrade head`

---

## 5. Testing

| Category | Status |
|----------|--------|
| API unit tests | 137 passing ✅ |
| Frontend tests | **0** ❌ |
| E2E tests | **0** ❌ |
| Worker integration tests | **0** ❌ |
| WebSocket integration tests | **0** ❌ |
| DB migration tests | **0** ❌ |
| Redis/ARQ integration | **0** ❌ |

---

## 6. Infrastructure / DevOps

| Item | Status |
|------|--------|
| `docker-compose.yml` (API + Redis + PostgreSQL) | Có |
| `Dockerfile` (API) | Có |
| `docker-compose.dashboard.yml` | Có |
| `Dockerfile.dashboard` | Có |
| CI/CD pipeline | **Không có** |
| Pre-commit hooks | **Không có** |
| Environment config (.env pattern) | Có |
| Monitoring/Logging (structured) | Cơ bản (Python logging) |

---

## 7. Kết luận & Kế hoạch bổ sung

### Hệ thống đã hoàn thiện ~75-80%
Backend CRUD + generation pipeline + export pipeline hoạt động. Worker tasks cơ bản đầy đủ (generate background, keyframe, audio, export scene, lipsync). Frontend dashboard hoạt động cho workflows chính.

### Các việc cần làm để hoàn thiện

#### Khẩn cấp (breaking)
1. **Implement `run_concat_project`** — thêm function body vào `worker.py` + đăng ký trong `WorkerSettings.functions`
2. **Implement `cleanup_cron_task`** (optionally schedule với ARQ cron)

#### Quan trọng (user-facing)
3. **Frontend: Lip Sync button** trong ShotEditor
4. **Frontend: Progress bars** hiển thị từ WebSocket data
5. **Frontend: Download link** sau khi export hoàn tất
6. **Frontend: Project-level export button** trong ExportPanel

#### Nâng cao (post-production)
7. Wire post-production services vào export pipeline:
   - `subtitle.py` — render SRT overlay bằng FFmpeg
   - `transition.py` — xfade giữa các shot
   - `audio_mixer.py` — mix BGM + SFX
   - `camera.py` — Ken Burns / pan-zoom effect
   - `color_grade.py` — apply LUT / color matrix
   - `shadow.py` — drop shadow trên character layer
   - `vfx_overlay.py` — rain/aura/glow effects

#### CLI
8. Xây dựng `apps/cli/` với `click` hoặc `typer`:
   - `pipeline project create/list/delete`
   - `pipeline story generate`
   - `pipeline export`
   - `pipeline batch`
   - `pipeline seed`

#### Testing
9. Thêm frontend test (Vitest + React Testing Library)
10. Thêm E2E test (Playwright)
11. Thêm worker integration test
12. Thêm WebSocket integration test

#### DevOps
13. CI/CD pipeline (GitHub Actions)
14. Pre-commit hooks (lint, typecheck, test)
