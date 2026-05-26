# Module 6: Audio & Export — Implementation Plan

## Overview

Module 6 tạo audio narration + background music cho từng shot, sync vào timeline, và export thành video `.mp4` từ keyframes + audio. Output là file `.wav` hoặc `.mp3` trong `audio/`, và file `.mp4` trong `exports/`.

**Dependencies cần cài:** `edge-tts`, `openai` (SDK để gọi TTS OpenAI-compatible), FFmpeg

---

## Step 6.1 — Install Dependencies

```bash
uv add edge-tts openai
sudo apt-get install -y ffmpeg
```

---

## Step 6.2 — Shot Schema Updates

**File:** `packages/shared/ai_2d_shared/shot.py` (MODIFY)

Thêm vào `ShotRead`:
- `audio_asset_id: UUID | None = None`
- `video_export_id: UUID | None = None`

**File:** `apps/api/app/models/shot.py` (MODIFY)

Thêm columns + migration 0005:
- `audio_asset_id: UUID | None` → FK assets
- `video_export_id: UUID | None` → FK assets

---

## Step 6.3 — TTS Service

**File:** `apps/api/app/services/tts.py` (NEW)

**Interface:**

```python
class TTSService:
    def __init__(self, provider: str = "edge_tts")
    async def generate_speech(self, text: str, voice: str = "vi-VN-NamMinhNeural") -> bytes
        """Generate speech audio from text. Returns WAV/MP3 bytes."""
```

**Providers:**
- `edge_tts` — free, Vietnamese voices available, no API key
- `openai` — OpenAI-compatible TTS endpoint

**Prompt assembly:** `shot.description` if available, else `AudioConfig.voice_profile`

---

## Step 6.4 — Audio Generation Endpoint

**Files:**
- `apps/api/app/routers/shots.py` (MODIFY) — add endpoint
- `apps/api/app/services/tts.py` (included)

**Endpoint:** `POST /api/v1/shots/{id}/generate-audio`
- Generates TTS from shot description
- Saves to `audio/` via `asset_utils.save_generated_asset`
- Sets `shot.audio_asset_id`

---

## Step 6.5 — Batch Audio Generation

**Endpoint:** `POST /api/v1/scenes/{id}/generate-all-audio`
- Queues audio generation for all shots in scene sequentially
- Tracks progress via JobModel

---

## Step 6.6 — Export Service

**File:** `apps/api/app/services/exporter.py` (NEW)

**Logic:**
1. Collect keyframes + audio from all shots in a scene
2. For each shot: create still frame from keyframe PNG padded to `duration_seconds`
3. Concat all frames → video track
4. Concat all audio → audio track
5. Merge video + audio → `exports/scene_{id}_{timestamp}.mp4`

**FFmpeg commands:**
- Frame to video clip: `ffmpeg -loop 1 -i frame.png -t {duration} -c:v libx264 clip.mp4`
- Concat clips: `ffmpeg -f concat -i filelist.txt -c copy merged.mp4`
- Merge audio: `ffmpeg -i merged.mp4 -i audio.wav -c:v copy -c:a aac output.mp4`

---

## Step 6.7 — Export Endpoint

**Endpoint:** `POST /api/v1/scenes/{id}/export`
- Calls export service
- Saves `.mp4` to `exports/` via `AssetModel(type=EXPORT)`
- Returns `{ export_url, file_path }`

---

## Step 6.8 — Tests

**File:** `apps/api/tests/test_audio.py` (NEW)

- TTS service prompt construction (mocked edge_tts)
- generate-audio endpoint → verifies asset created
- generate-all-audio → verifies progress
- export service → mocks FFmpeg subprocess

**File:** `apps/api/tests/test_exporter.py` (NEW)

- Export collects correct files
- FFmpeg command construction correct
- Handles missing keyframe gracefully

**Target:** ~10 tests

---

## Files Summary

| File | Action |
|------|--------|
| `packages/shared/ai_2d_shared/shot.py` | MODIFY — audio_asset_id, video_export_id |
| `apps/api/app/models/shot.py` | MODIFY — 2 columns |
| `apps/api/alembic/versions/0005_add_shot_audio_video.py` | NEW |
| `apps/api/app/services/tts.py` | NEW |
| `apps/api/app/services/exporter.py` | NEW |
| `apps/api/app/routers/shots.py` | MODIFY — 3 endpoints |
| `apps/api/tests/test_audio.py` | NEW |
| `apps/api/tests/test_exporter.py` | NEW |

---

## Deliverables Checkpoint

```text
□ Shot model: audio_asset_id, video_export_id
□ TTS service (edge_tts + openai)
□ Audio generation endpoint
□ Batch audio generation
□ FFmpeg-based video export
□ Export endpoint → .mp4 file
□ Tests (~10 tests)
```

---

## Next: Module 7 — Frontend / UI

React-based dashboard: project manager, story bible editor, character DNA editor, timeline/storyboard viewer, generation controls.
