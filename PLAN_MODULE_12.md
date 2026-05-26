# Module 12: Advanced Post-Production — Implementation Plan

## Overview

Module 12 hoàn thiện pipeline video export với post-production chuyên nghiệp: color grading (LUT, colorbalance, eq), VFX overlays (rain, spiritual aura, glow), character shadow compositing, advanced transitions (curtain, wipe, slide) qua FFmpeg `xfade`, và unified `filter_complex` pipeline — tất cả trong một lần FFmpeg duy nhất.

## Current State

- exporter.py hiện dùng multi-pass: tạo từng clip → concat → merge audio + subtitle
- camera.py đã có filter chain cho camera motion
- subtitle.py đã có ASS generation + overlay filter
- audio_mixer.py đã có narration + BGM mixing
- SceneModel có `transition_style` nhưng chỉ hỗ trợ "fade" (dùng `-f concat`, không dùng `xfade`)
- ShotModel có `camera_json`, `motion_json`, `audio_json` trong JSONB
- ProjectModel có `aspect_ratio`, `default_font`, `subtitle_enabled`
- Chưa có color grading, VFX overlay, character shadow, advanced transitions

Key constraint: **FFmpeg-only** — không thêm external dependency mới.

---

## Architecture Decision

Chọn **unified `filter_complex` pipeline** (single FFmpeg pass):

- Mỗi post-production concern là service riêng trả về FFmpeg filter string
- Exporter build một `filter_complex` graph duy nhất
- Một lần FFmpeg encode → nhanh hơn, không mất chất lượng do re-encode
- Fallback multi-pass nếu `filter_complex` quá phức tạp hoặc lỗi

---

## Step 12.1 — Color Grading Service

**File:** `apps/api/app/services/color_grade.py` (NEW)

| Method | FFmpeg Filter | Use Case |
|--------|--------------|----------|
| `lut3d` | `lut3d=file=/path/to/lut.cube` | Áp dụng LUT .cube file |
| `colorbalance` | `colorbalance=rs=...:gs=...:bs=...:rh=...:gh=...:bh=...` | Chỉnh shadow/midtone/highlight |
| `eq` | `eq=brightness=...:contrast=...:saturation=...:gamma=...` | Brightness/contrast/saturation |

```python
class ColorGradeService:
    @staticmethod
    def get_filter_string(
        lut_path: str | None = None,
        colorbalance: dict | None = None,
        eq_params: dict | None = None,
    ) -> str:
        """Return FFmpeg filter chain: eq → colorbalance → lut3d.
        Returns empty string if no grading configured."""
```

---

## Step 12.2 — VFX Overlay Service

**File:** `apps/api/app/services/vfx_overlay.py` (NEW)

### Rain overlay

Dùng rain overlay loop MP4 bundled trong `storage/vfx/rain_overlay.mp4` (grayscale, dùng `colorkey` cho alpha). Loop với `stream_loop=-1`, overlay với opacity giảm.

### Spiritual aura / glow

Dùng `gblur` + `overlay` với `blend=screen`:

```
split → gblur=sigma=20 → colorize (optional) → overlay/blend=screen với original
```

```python
class VFXOverlayService:
    @staticmethod
    def get_rain_filter(width: int, height: int, opacity: float = 0.3) -> str:
        """Filter_complex snippet cho rain overlay."""

    @staticmethod
    def get_aura_filter(intensity: float = 0.5, color: str = "gold") -> str:
        """Filter_complex snippet cho spiritual aura glow."""

    @staticmethod
    def get_overlay_filter(
        overlay_input_label: str,
        x: int = 0, y: int = 0,
        opacity: float = 1.0,
    ) -> str:
        """Generic overlay compositing filter."""
```

---

## Step 12.3 — Shadow Generation Service

**File:** `apps/api/app/services/shadow.py` (NEW)

Tạo drop shadow cho character bằng FFmpeg filters:

```
[input] split [orig][shadow_src];
[shadow_src] format=rgba, colorchannelmixer=aa=0.5 [shadow_alpha];
[shadow_alpha] gblur=sigma=3 [shadow_blur];
[bg][shadow_blur] overlay=x=5:y=5 [bg_with_shadow];
[bg_with_shadow][orig] overlay=x=0:y=0 [out]
```

```python
class ShadowService:
    @staticmethod
    def get_shadow_filter(
        input_label: str,
        shadow_color: str = "black@0.5",
        offset_x: int = 5,
        offset_y: int = 5,
        blur_sigma: int = 3,
    ) -> str:
        """Drop shadow filter_complex snippet."""
```

---

## Step 12.4 — Advanced Transition Service

**File:** `apps/api/app/services/transition.py` (NEW)

Thay `-f concat` bằng FFmpeg `xfade`, hỗ trợ 14 kiểu transition:

| Transition | `xfade` param |
|-----------|---------------|
| `fade` | `transition=fade` |
| `dissolve` | `transition=fade` + longer duration |
| `fadeblack` | `transition=fadeblack` |
| `fadewhite` | `transition=fadewhite` |
| `wipeleft` | `transition=wipeleft` |
| `wiperight` | `transition=wiperight` |
| `wipeup` | `transition=wipeup` |
| `wipedown` | `transition=wipedown` |
| `slideleft` | `transition=slideleft` |
| `slideright` | `transition=slideright` |
| `slideup` | `transition=slideup` |
| `slidedown` | `transition=slidedown` |
| `circlecrop` | `transition=circlecrop` |
| `radial` | `transition=radial` |

```python
class TransitionService:
    XFADE_MAP = {
        "fade": "fade", "dissolve": "fade",
        "fadeblack": "fadeblack", "fadewhite": "fadewhite",
        "wipeleft": "wipeleft", "wiperight": "wiperight",
        "wipeup": "wipeup", "wipedown": "wipedown",
        "slideleft": "slideleft", "slideright": "slideright",
        "slideup": "slideup", "slidedown": "slidedown",
        "circlecrop": "circlecrop", "radial": "radial",
    }

    @classmethod
    def build_xfade_chain(
        cls,
        segment_labels: list[str],
        transition_styles: list[str],
        segment_durations: list[float],
        transition_duration: float = 0.5,
    ) -> tuple[str, str]:
        """Build xfade filter_complex chain.
        For N segments with N-1 transitions:
          [s0][s1]xfade=transition=fade:duration=0.5:offset=3.5[x1]
          [x1][s2]xfade=transition=wipeleft:duration=0.5:offset=6.5[x2]
        Returns (filter_string, last_output_label).
        """
```

---

## Step 12.5 — Unified Export Pipeline (filter_complex)

**File:** `apps/api/app/services/exporter.py` (MODIFY — major refactor)

### Before (multi-pass):
```
For each shot → ffmpeg frame → clip_N.mp4  (pass N)
ffmpeg -f concat → merged.mp4              (pass N+1)
ffmpeg -i merged.mp4 -i audio → output.mp4  (pass N+2)
```

### After (single pass):
```
ffmpeg \
  -loop 1 -t dur0 -i frame_0.png \
  -loop 1 -t dur1 -i frame_1.png \
  -i narration.mp3 \
  -i bgm.mp3 \
  -filter_complex "
    [0:v]scale=W:H,camera_filters,...,shadow[s0];
    [1:v]scale=W:H,camera_filters,...,shadow[s1];
    [s0][s1]xfade=transition=fade:duration=0.5:offset=3.5[x1];
    [x1]eq=...,colorbalance=...,lut3d=...,rain_overlay,subtitles[v];
    [2:a][3:a]amix=inputs=2:duration=first[a]
  " \
  -map "[v]" -map "[a]" -c:v libx264 -c:a aac output.mp4
```

```python
async def _assemble_video(self, work_dir, scene, project, shots, width, height):
    """Build unified filter_complex pipeline.
    
    Phase 1: Input preparation — load frames/video → input args
    Phase 2: Per-segment filters — scale + camera + shadow
    Phase 3: xfade chain — transitions between segments
    Phase 4: Post-filters — color grade + VFX overlays + subtitles
    Phase 5: Audio mix — narration + BGM
    Phase 6: Single FFmpeg invocation
    """
```

---

## Step 12.6 — Configuration & Migration

**File:** `apps/api/alembic/versions/0007_add_post_production_config.py` (NEW)

Add to `scenes`:
- `grade_json: JSONB = '{}'` — `{ "lut_path": null, "colorbalance": {...}, "eq": {...} }`
- `vfx_json: JSONB = '{}'` — `{ "rain": { "enabled": false, "opacity": 0.3 }, "aura": { "enabled": false, "intensity": 0.5, "color": "gold" } }`
- `shadow_enabled: bool = False`

Add to `shots`:
- `overlay_json: JSONB = '{}'` — `{ "overlays": [{ "asset_id": "...", "x": 0, "y": 0, "opacity": 1.0 }] }`

**File:** `packages/shared/ai_2d_shared/scene.py` (MODIFY)

```python
class GradeConfig(BaseModel):
    lut_path: str | None = None
    colorbalance: dict | None = None
    eq: dict | None = None

class VFXConfig(BaseModel):
    rain: dict | None = None    # { "enabled": bool, "opacity": float }
    aura: dict | None = None    # { "enabled": bool, "intensity": float, "color": str }
```

**File:** `apps/api/app/models/scene.py` (MODIFY) — add `grade_json`, `vfx_json`, `shadow_enabled`

**File:** `apps/api/app/models/shot.py` (MODIFY) — add `overlay_json`

**Asset:** `storage/vfx/rain_overlay.mp4` (NEW) — 2s loopable rain overlay

---

## Step 12.7 — Tests

**File:** `apps/api/tests/test_post_production.py` (NEW)

1. `test_color_grade_lut3d` — `get_filter_string(lut_path="test.cube")` → contains `lut3d=`
2. `test_color_grade_eq` — eq params → contains `eq=brightness=...`
3. `test_color_grade_combined` — all three → filter order eq → colorbalance → lut3d
4. `test_vfx_rain_filter` — contains `overlay`, `colorkey`
5. `test_vfx_aura_filter` — contains `gblur`, `blend=screen`
6. `test_transition_xfade_map` — all 14 styles map to valid xfade values
7. `test_transition_xfade_chain` — 3 segments + 2 transitions → correct filter chain

**Target:** ~7 tests

---

## Files Summary

| File | Action |
|------|--------|
| `apps/api/app/services/color_grade.py` | NEW |
| `apps/api/app/services/vfx_overlay.py` | NEW |
| `apps/api/app/services/shadow.py` | NEW |
| `apps/api/app/services/transition.py` | NEW |
| `apps/api/app/services/exporter.py` | MODIFY — unified filter_complex pipeline |
| `apps/api/alembic/versions/0007_add_post_production_config.py` | NEW |
| `apps/api/app/models/scene.py` | MODIFY — grade_json, vfx_json, shadow_enabled |
| `apps/api/app/models/shot.py` | MODIFY — overlay_json |
| `packages/shared/ai_2d_shared/scene.py` | MODIFY — GradeConfig, VFXConfig |
| `storage/vfx/rain_overlay.mp4` | NEW — bundled rain loop asset |
| `apps/api/tests/test_post_production.py` | NEW |

---

## Deliverables Checkpoint

```text
□ ColorGradeService — lut3d, colorbalance, eq FFmpeg filter generation
□ VFXOverlayService — rain particles, spiritual aura glow, generic overlay compositing
□ ShadowService — drop shadow via split/gblur/colorchannelmixer
□ TransitionService — 14 xfade transition types with chain builder
□ Exporter refactored to unified filter_complex pipeline (single FFmpeg pass)
□ Migration 0007 — grade_json, vfx_json, shadow_enabled, overlay_json
□ GradeConfig + VFXConfig Pydantic models
□ Bundled rain overlay MP4 in storage/vfx/
□ ~7 tests
```

---

## Next: Module 13 — Render Queue Optimization

Batch processing, parallel scene rendering, progress dashboard.
