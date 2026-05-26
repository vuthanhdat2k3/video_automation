# Module 5: Keyframe & Background Generation — Implementation Plan

## Overview

Module 5 tạo background images từ scene continuity state và keyframe images cho từng shot, dùng character reference assets để giữ consistency. Output là background và keyframe PNG files lưu trong storage + DB asset records liên kết với shots.

Slug: 5kfr

---

## Step 5.1 — Database Migration

**File:** `apps/api/alembic/versions/0004_add_shot_asset_links.py` (NEW)

```sql
ALTER TABLE shots ADD COLUMN background_asset_id UUID REFERENCES assets(id) ON DELETE SET NULL;
ALTER TABLE shots ADD COLUMN keyframe_asset_id UUID REFERENCES assets(id) ON DELETE SET NULL;
ALTER TABLE shots ADD COLUMN generation_prompt TEXT;
ALTER TABLE shots ADD COLUMN generation_params JSONB DEFAULT '{}';
```

---

## Step 5.2 — Shot Model Updates

**File:** `apps/api/app/models/shot.py` (MODIFY)

Thêm columns:
- `background_asset_id: Mapped[UUID | None]` → FK assets
- `keyframe_asset_id: Mapped[UUID | None]` → FK assets
- `generation_prompt: Mapped[str | None]` → prompt đã dùng
- `generation_params: Mapped[dict]` → seed/steps/cfg etc.

---

## Step 5.3 — Background Generation Service

**File:** `apps/api/app/services/background_gen.py` (NEW)

**Logic:**
- Input: `scene_id` → SceneModel.continuity (lighting, mood, time_of_day, location, weather) + project.style
- Build prompt: `[style] [time_of_day] [weather] [location], [lighting] lighting, [mood] mood, distant background, no characters, high quality, detailed`
- Tạo ComfyUI workflow `background_gen.json` (đơn giản txt2img)
- Mở rộng `ComfyUIClient.generate_image()` để hỗ trợ custom workflow
- Save → storage `backgrounds/` + AssetModel(type=BACKGROUND)
- Set `shot.background_asset_id`

**Endpoint:** `POST /api/v1/shots/{id}/generate-background`

---

## Step 5.4 — Keyframe Generation Service

**File:** `apps/api/app/services/keyframe_gen.py` (NEW)

**Logic:**
- Input: `shot_id` → ShotModel + SceneModel.continuity + CharacterModel (từ project)
- Build prompt từ shot description + character DNA + scene continuity
- Nếu có character reference asset → dùng IPAdapter/ControlNet để giữ consistency (phase 2 — MVP dùng txt2img có character description trong prompt)
- ComfyUI workflow: `keyframe_gen.json` (txt2img với prompt đầy đủ)
- Save → storage `keyframes/` + AssetModel(type=KEYFRAME)
- Set `shot.keyframe_asset_id`, `shot.generation_prompt`, `shot.status = 'keyframe_generated'`

**Endpoint:** `POST /api/v1/shots/{id}/generate-keyframe`

---

## Step 5.5 — Batch Generation

**File:** `apps/api/app/services/keyframe_gen.py` (MODIFY)

**Logic:**
- `POST /scenes/{id}/generate-all-keyframes` → duyệt shots, generate từng keyframe tuần tự
- `POST /projects/{id}/generate-all-backgrounds` → duyệt scenes, generate background cho scene đầu tiên của mỗi scene
- Track progress qua JobModel (status + progress)

**Endpoints:**
- `POST /api/v1/scenes/{id}/generate-all-keyframes`
- `POST /api/v1/projects/{id}/generate-all-backgrounds`

---

## Step 5.6 — Timeline Extension

**File:** `apps/api/app/services/timeline.py` (MODIFY)

Enrich timeline response với:
- `keyframe_url` ở mỗi shot entry (nếu có)
- `background_url` ở mỗi scene entry (nếu có)
- `generation_status` enum: draft → keyframe_generated → complete

---

## Step 5.7 — Tests

**File:** `apps/api/tests/test_keyframe_gen.py` (NEW)

- Mock ComfyUIClient → test prompt generation từ shot + scene + character
- test keyframe image được save đúng storage path
- test shot.keyframe_asset_id được link
- test background generation từ continuity state
- test batch generation progress tracking
- test timeline enrichment với URLs
- test 404 cho shot không tồn tại

**Target:** ~8 tests

---

## File Summary

| File | Action |
|------|--------|
| `apps/api/alembic/versions/0004_add_shot_asset_links.py` | NEW |
| `apps/api/app/models/shot.py` | MODIFY — 4 columns |
| `apps/api/app/services/comfyui/workflows/background_gen.json` | NEW |
| `apps/api/app/services/comfyui/workflows/keyframe_gen.json` | NEW |
| `apps/api/app/services/comfyui/client.py` | MODIFY — thêm `generate_with_workflow()` |
| `apps/api/app/services/background_gen.py` | NEW |
| `apps/api/app/services/keyframe_gen.py` | NEW |
| `apps/api/app/services/timeline.py` | MODIFY — enrich với URLs |
| `apps/api/app/routers/shots.py` | MODIFY — 2 generate endpoints |
| `apps/api/tests/test_keyframe_gen.py` | NEW |

---

## Deliverables Checkpoint

```text
□ Shot model: background + keyframe asset links
□ Background generation from continuity state
□ Keyframe generation from shot + character DNA
□ Batch generation endpoints
□ Timeline enriched with generated asset URLs
□ Tests (~8 tests)
```

---

## Next: Module 6 — Audio & Export

TTS narration per shot, background music selection, audio timeline sync, video export pipeline (frames → video).
