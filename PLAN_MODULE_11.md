# Module 11: Lip Sync & Talking Portrait — Implementation Plan

## Overview

Module 11 thêm lip sync cho character portrait — tạo video talking head từ keyframe character portrait + TTS audio narration. Dùng MuseTalk (mạnh + nhanh nhất hiện tại cho talking head) hoặc Wav2Lip làm fallback. Output là video clip `.mp4` có chuyển động môi đồng bộ với audio.

## Current State

- Keyframe character portrait có sẵn (từ ComfyUI SDXL GGUF)
- Audio narration có sẵn (từ edge-tts)
- Export pipeline đã có camera motion + subtitle + audio merge
- Chưa có lip sync

---

## Step 11.1 — MuseTalk Installation

```bash
# Clone MuseTalk
git clone https://github.com/TMElyralab/MuseTalk.git ~/pipeline/MuseTalk
cd ~/pipeline/MuseTalk
pip install -r requirements.txt
pip install --no-build-isolation -e .
```

**Requirements:**
- PyTorch 2.0+ with CUDA
- FFmpeg
- RTX 3060 12GB đủ để chạy

---

## Step 11.2 — MuseTalk Wrapper Service

**File:** `apps/api/app/services/lipsync.py` (NEW)

```python
class LipSyncService:
    def __init__(self, model_path: str = "MuseTalk", device: str = "cuda"):
        self.model = self._load_model()

    async def generate_talking_head(
        self,
        image_path: Path,      # Character portrait PNG
        audio_path: Path,       # TTS narration MP3/WAV
        output_path: Path,      # Output MP4
        fps: int = 25,
    ) -> Path:
        """Generate talking head video from portrait + audio."""

    @staticmethod
    def needs_lipsync(shot: ShotModel) -> bool:
        """Check if shot has dialogue that would benefit from lip sync."""
        return bool(shot.description and shot.keyframe_asset_id)
```

**Integration points:**
- Input: character keyframe asset (from `shot.keyframe_asset_id`) + audio asset (from `shot.audio_asset_id`)
- Output: `video_clip` asset stored via `save_generated_asset`
- Set `shot.video_export_id` to the lip-synced clip

---

## Step 11.3 — Lip Sync Job Task

**File:** `apps/api/app/services/worker.py` (MODIFY)

Add new ARQ task:

```python
async def run_lipsync_shot(ctx, project_id: str, shot_id: str) -> bool:
    """Generate lip-synced talking head for a shot."""
    # 1. Load shot.keyframe_asset → PNG path
    # 2. Load shot.audio_asset → audio path
    # 3. Call LipSyncService.generate_talking_head()
    # 4. Save output MP4 as asset, set shot.video_export_id
    # 5. Mark job completed via WebSocket broadcast
```

**File:** `apps/api/worker.py` (MODIFY)

Add `run_lipsync_shot` to `WorkerSettings.functions`.

---

## Step 11.4 — Lip Sync Endpoint

**File:** `apps/api/app/routers/shots.py` (MODIFY)

```python
@router.post("/shots/{shot_id}/generate-lipsync", response_model=dict)
async def generate_lipsync(shot_id: UUID, db: AsyncSession = Depends(get_db)):
    """Dispatch lip sync generation for a shot."""
    # Dispatch run_lipsync_shot task via dispatch_job
    # Returns { job_id }
```

---

## Step 11.5 — Export Pipeline Integration

**File:** `apps/api/app/services/exporter.py` (MODIFY)

In `_assemble_video`, for shots with `video_export_id` (lip-synced clips), use the generated video instead of creating a still frame:

```python
if shot.video_export_id:
    # Use pre-generated lip-sync video
    clip_path = load_video_asset(shot.video_export_id)
else:
    # Generate still frame clip with camera motion
```

---

## Step 11.6 — Configuration / Enums

**File:** `packages/shared/ai_2d_shared/enums.py` (MODIFY)

Add to `JobType`:
```python
LIPSYNC = "lipsync"
```

---

## Step 11.7 — Tests

**File:** `apps/api/tests/test_lipsync.py` (NEW)

- `LipSyncService.needs_lipsync() → True` when shot has description + keyframe
- `LipSyncService.needs_lipsync() → False` when no description or no keyframe
- `POST /shots/{id}/generate-lipsync` returns `{ job_id }` (mocked MuseTalk)
- Exporter skips still frame when `video_export_id` is set (mocked)
- Lip sync worker task lifecycle (create → complete via WebSocket)

**Target:** ~6 tests

---

## Files Summary

| File | Action |
|------|--------|
| `apps/api/app/services/lipsync.py` | NEW — MuseTalk wrapper |
| `apps/api/app/services/worker.py` | MODIFY — add `run_lipsync_shot` |
| `apps/api/worker.py` | MODIFY — register lipsync task |
| `apps/api/app/routers/shots.py` | MODIFY — add `generate-lipsync` endpoint |
| `apps/api/app/services/exporter.py` | MODIFY — use lip-sync video clips |
| `packages/shared/ai_2d_shared/enums.py` | MODIFY — add `JobType.LIPSYNC` |
| `apps/api/tests/test_lipsync.py` | NEW |

---

## Deliverables Checkpoint

```text
□ MuseTalk installed and wrapper service created
□ run_lipsync_shot ARQ worker task
□ POST /shots/{id}/generate-lipsync endpoint → { job_id }
□ Exporter uses lip-sync video when available
□ LIPSYNC job type added to enums
□ ~6 tests
```

---

## Next: Module 12 — Advanced Post-Production

Color grading (LUT), rain/aura overlays, character shadows, transition effects (curtain, wipe, slide), final compositing pipeline.
