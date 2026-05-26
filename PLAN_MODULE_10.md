# Module 10: Animation & Audio Enhancement — Implementation Plan

## Overview

Module 10 nâng cấp export từ slideshow tĩnh thành video có chuyển động: camera motion (pan, zoom, tilt) theo `CameraConfig`, crossfade transitions giữa các shot, và subtitle overlay. MVP target: 1 main character + 1 background + 1 scene 8-15 giây với voice, subtitle, light camera motion, export 9:16 vertical MP4.

## Current State

- Export tạo slideshow tĩnh từ keyframes + audio
- `CameraConfig` có `angle`, `framing`, `movement`, `lens` — nhưng chưa dùng khi export
- `AudioConfig` có `background_music`, `sound_effects` — chưa dùng
- TTS narration đã có
- Chưa có subtitle, camera effect, transition

---

## Step 10.1 — Camera Motion Service

**File:** `apps/api/app/services/camera.py` (NEW)

Map `CameraConfig.movement` sang FFmpeg filter:

| Movement | FFmpeg filter | Effect |
|----------|--------------|--------|
| `static` | none | Fixed frame |
| `pan_left` | `crop + overlay` | Slow pan left |
| `pan_right` | `crop + overlay` | Slow pan right |
| `tilt_up` | `crop + overlay` | Tilt upward |
| `tilt_down` | `crop + overlay` | Tilt downward |
| `zoom_in` | `scale + crop` | Ken Burns zoom in |
| `zoom_out` | `scale + crop` | Ken Burns zoom out |
| `dolly` | `zoom + perspective` | Dolly zoom |
| `handheld` | `random + crop` | Subtle shake |

```python
class CameraMotionService:
    def get_filters(shot: ShotModel, width: int, height: int, fps: int) -> list[str]:
        """Return FFmpeg video filter chain for camera motion."""
```

---

## Step 10.2 — Subtitle Overlay Service

**File:** `apps/api/app/services/subtitle.py` (NEW)

- Parse `shot.description` / TTS text làm subtitle
- Generate `.ass` (Advanced SubStation Alpha) hoặc `.srt` file
- FFmpeg overlay: `subtitles=subs.ass:force_style=...`

```python
class SubtitleService:
    def generate_subs(shots: list[ShotModel]) -> bytes:
        """Generate ASS subtitle file from shot scripts."""
    def get_overlay_filter(sub_path: str) -> str:
        """FFmpeg filter string for subtitle overlay."""
```

Style: Chinese-friendly font, yellow/white text, black stroke, bottom-center.

---

## Step 10.3 — Transition Effects

**File:** `apps/api/app/services/exporter.py` (MODIFY)

| Transition | FFmpeg | Duration |
|-----------|--------|----------|
| `cut` | concat | 0s (default) |
| `fade` | `fade=in:st=0:d=0.5,fade=out:st=dur-0.5:d=0.5` | 0.5s |
| `dissolve` | `xfade=transition=fade:duration=0.5` | 0.5s |

Configurable per scene via `SceneModel.continuity.transition_style`.

---

## Step 10.4 — Background Music Mixing

**File:** `apps/api/app/services/audio.py` (NEW)

- Read `AudioConfig.background_music` — path to music file or URL
- Mix: narration (voice) + background music + sound effects
- FFmpeg audio filter: `amix=inputs=2:duration=first:dropout_transition=2,volume=0.3`

```python
class AudioMixer:
    def mix_audio(voice_path: str, music_path: str | None, volume: float) -> bytes:
        """Mix voice narration with background music. Returns mixed audio bytes."""
```

---

## Step 10.5 — Export Pipeline Upgrade

**File:** `apps/api/app/services/exporter.py` (MODIFY)

Updated `_assemble_video` flow:

```
For each shot:
    1. Load keyframe PNG
    2. Apply camera motion filters → video clip
    3. Apply fade/dissolve transition between clips
After video assembly:
    4. Generate subtitle overlay
    5. Mix audio (narration + background music)
    6. Merge video + audio + subtitles
    7. Output MP4
```

---

## Step 10.6 — Configuration Migration

**File:** `apps/api/alembic/versions/0006_add_transition_style.py` (NEW)

Add to `scenes` table:
- `transition_style: str = "fade"`

Add to `projects` table:
- `default_font: str = "Noto Sans SC"`
- `subtitle_enabled: bool = False`

---

## Step 10.7 — Tests

**File:** `apps/api/tests/test_camera.py` (NEW)
- Camera motion filter generation per movement type
- Empty config → static (no filter)
- Resolution scaling in filters

**File:** `apps/api/tests/test_subtitle.py` (NEW)
- ASS subtitle generation from shot text
- Timestamp calculation from duration_seconds
- Style injection for Chinese fonts

**File:** `apps/api/tests/test_audio_mixer.py` (NEW)
- Narration + background music mixing via ffmpeg pipe
- Volume normalization

**Target:** ~12 tests

---

## Files Summary

| File | Action |
|------|--------|
| `apps/api/app/services/camera.py` | NEW |
| `apps/api/app/services/subtitle.py` | NEW |
| `apps/api/app/services/audio_mixer.py` | NEW |
| `apps/api/app/services/exporter.py` | MODIFY — camera + subs + transitions |
| `apps/api/alembic/versions/0006_add_transition_style.py` | NEW |
| `apps/api/tests/test_camera.py` | NEW |
| `apps/api/tests/test_subtitle.py` | NEW |
| `apps/api/tests/test_audio_mixer.py` | NEW |

---

## Deliverables Checkpoint

```text
□ Camera motion FFmpeg filters per movement type
□ Subtitle generation (ASS format, Chinese font)
□ Crossfade/dissolve transitions between shots
□ Background music mixing with voice narration
□ Export pipeline: camera + subs + music + voice → MP4
□ Migration 0006 for transition_style + font config
□ ~12 tests
```

---

## Next: Module 11 — Lip Sync & Character Animation

MuseTalk / Wav2Lip integration for talking head animation from character portrait + TTS audio.
