# AI 2D Animation Studio — Khung kiến trúc dự án

## 0. Mục tiêu sản phẩm

Xây dựng một hệ thống kiểu **Google Flow lite** chuyên cho phim hoạt hình 2D Trung Quốc:

```text
Ý tưởng / prompt
→ Story Bible
→ nhân vật / bối cảnh / props
→ shot plan
→ keyframe
→ animation
→ audio / lip sync
→ edit / subtitle / export
```

Mục tiêu MVP đầu tiên:

```text
1 main character
+ 1 bối cảnh đô thị tu tiên
+ 1 cảnh 8–15 giây
+ voice / subtitle / camera motion nhẹ
+ export MP4 dọc 9:16
```

---

## 1. Kiến trúc tổng thể

```text
Frontend / Studio UI
        ↓
Backend API Gateway
        ↓
Project Orchestrator
        ↓
Render Queue
        ↓
AI Worker Layer
 ├── Story Bible Worker
 ├── Character Worker
 ├── Background Worker
 ├── Shot Planner Worker
 ├── Keyframe Worker
 ├── Animation Worker
 ├── Audio Worker
 ├── Lip Sync Worker
 └── Composer Worker
        ↓
Asset Store + Database
        ↓
Final Video Export
```

---

## 2. Tech stack đề xuất

### MVP stack

```text
Frontend: Next.js + Tailwind + shadcn/ui
Backend: FastAPI
Queue: Redis + RQ hoặc Celery
Database: PostgreSQL
Asset Storage: local filesystem trước, sau nâng lên MinIO
AI Workflow: ComfyUI API
Video processing: FFmpeg
Audio: edge-tts trước, XTTS sau
Lip sync: MuseTalk / SadTalker / Wav2Lip
```

### Vì sao chọn stack này

- FastAPI dễ vibe code, dễ gọi Python AI tools.
- ComfyUI tận dụng được RTX 3060 12GB.
- FFmpeg cực rẻ, mạnh, phù hợp batch video.
- PostgreSQL đủ tốt cho project, asset, scene, shot, job.
- Redis queue giúp render không block API.

---

## 3. Module chính

## Module 1 — Project Studio

Quản lý toàn bộ project phim.

### Chức năng

```text
Create project
Edit project metadata
Select style
Select aspect ratio
Manage scenes
Manage characters
Render preview
Export final
```

### Entity chính

```json
{
  "id": "project_001",
  "title": "Đô Thị Tu Tiên",
  "style": "2d_chinese_donghua",
  "aspect_ratio": "9:16",
  "default_duration": 8,
  "status": "draft"
}
```

---

## Module 2 — Story Bible / LLM Layer

Đây là não cốt truyện.

### Input

```text
Ý tưởng thô của user
```

### Output

```json
{
  "world": {},
  "characters": [],
  "power_system": {},
  "tone": "urban cultivation, mysterious, dramatic",
  "episodes": [],
  "scene_breakdown": []
}
```

### Chức năng

```text
Generate character sheet
Generate world bible
Generate episode outline
Generate scene breakdown
Generate shot list
Generate prompt package
```

### Lưu ý

MVP chưa cần gọi API đắt tiền. Có thể bắt đầu bằng prompt thủ công hoặc local LLM sau.

---

## Module 3 — Character System

Đây là module quan trọng nhất để giữ consistency.

### Character DNA

```json
{
  "id": "char_main_001",
  "name": "Lâm Hàn",
  "role": "main_protagonist",
  "appearance": {
    "hair": "black layered hair",
    "eyes": "sharp calm dark eyes",
    "outfit": "modern black coat with subtle gold dragon pattern",
    "aura": "hidden golden dragon spiritual energy"
  },
  "personality": {
    "surface": "quiet, ordinary student",
    "hidden": "overpowered heir of ancient clan"
  },
  "style_tokens": [
    "2D Chinese donghua",
    "urban xianxia",
    "handsome male protagonist"
  ],
  "reference_assets": []
}
```

### Chức năng

```text
Generate main character image
Generate expression pack
Generate pose pack
Generate outfit variants
Store reference images
Use IPAdapter / reference image for consistency
Train LoRA later if needed
```

### MVP engine

```text
ComfyUI + SD1.5/Pony/Anything + LoRA 2d_donghua + IPAdapter
```

---

## Module 4 — Asset / Ingredients Store

Kho nguyên liệu giống Google Flow Ingredients.

### Asset types

```text
character
background
prop
pose_reference
style_reference
keyframe
audio
video_clip
subtitle
final_video
```

### Asset metadata

```json
{
  "id": "asset_001",
  "project_id": "project_001",
  "type": "character",
  "path": "storage/projects/project_001/assets/main.png",
  "prompt": "...",
  "model": "sd15_donghua_lora",
  "seed": 123456,
  "tags": ["main", "front_view", "black_coat"],
  "created_at": "..."
}
```

### Vai trò

- Cache asset để không generate lại.
- Reuse nhân vật/bối cảnh qua nhiều shot.
- Là nền cho consistency.

---

## Module 5 — Scene System

Scene là đơn vị cốt truyện lớn.

### Scene entity

```json
{
  "id": "scene_001",
  "project_id": "project_001",
  "title": "Main xuất hiện dưới mưa",
  "duration": 8,
  "location": "neon city university gate",
  "mood": "mysterious, powerful, cinematic",
  "continuity_state": {
    "weather": "rain",
    "time": "night",
    "main_emotion": "calm but intimidating"
  }
}
```

### Chức năng

```text
Create scene
Break scene into shots
Track scene state
Store continuity info
Extend scene
Jump-to next scene
```

---

## Module 6 — Shot Planner

Shot là đơn vị render video nhỏ nhất.

### Shot entity

```json
{
  "id": "shot_001",
  "scene_id": "scene_001",
  "duration": 8,
  "shot_type": "cinematic_intro",
  "description": "Main stands in rainy neon city, golden dragon aura appears behind him.",
  "camera": {
    "framing": "medium close-up",
    "movement": "slow push-in",
    "angle": "low angle",
    "lens": "85mm cinematic"
  },
  "motion": {
    "character": "coat moves slightly, hair moves in rain",
    "environment": "rain falls, neon reflections shimmer",
    "vfx": "golden dragon aura slowly forms"
  },
  "audio": {
    "dialogue": "Các ngươi... còn chưa đủ tư cách biết ta là ai.",
    "bgm": "dark cinematic chinese fantasy",
    "sfx": ["rain", "spiritual energy hum"]
  }
}
```

### Vai trò

- Biến story thành lệnh render cụ thể.
- Chuẩn hóa camera/motion/style.
- Giúp không phụ thuộc vào prompt tự do.

---

## Module 7 — Prompt Compiler

Chuyển JSON shot thành prompt cho từng engine.

### Input

```json
{
  "character": "char_main_001",
  "scene": "scene_001",
  "shot": "shot_001"
}
```

### Output

```json
{
  "image_prompt": "...",
  "negative_prompt": "...",
  "video_prompt": "...",
  "camera_prompt": "...",
  "audio_prompt": "..."
}
```

### Đây là module rất quan trọng

Không để user prompt đi thẳng vào model. Luôn compile qua cấu trúc:

```text
style
character
environment
camera
motion
emotion
continuity
negative constraints
```

---

## Module 8 — Keyframe Generator

Sinh ảnh đầu/cuối hoặc ảnh chính cho video.

### Chức năng

```text
Generate start frame
Generate end frame
Generate thumbnail frame
Regenerate selected frame
Upscale keyframe
```

### Engine MVP

```text
ComfyUI image workflow
SD1.5/Pony/Anything
IPAdapter reference main character
ControlNet optional
```

---

## Module 9 — Animation Engine

Biến keyframe thành video.

### Shot type routing

```text
Talking head → MuseTalk / SadTalker / Wav2Lip
Slow cinematic → AnimateDiff
Full body action → Wan Animate / cloud later
Static motion → FFmpeg camera motion only
```

### MVP route rẻ nhất

```text
Keyframe image
→ FFmpeg camera zoom/pan
→ rain overlay / aura overlay
→ subtitle
→ audio
→ MP4
```

### Advanced route

```text
Keyframe image
→ AnimateDiff
→ RIFE interpolation
→ RealESRGAN upscale
→ composer
```

---

## Module 10 — Audio Pipeline

### Chức năng

```text
Generate dialogue voice
Generate background music
Generate SFX
Normalize audio
Sync audio to timeline
```

### MVP

```text
edge-tts
local SFX library
free BGM library
FFmpeg audio mixing
```

### Later

```text
XTTS / GPT-SoVITS
RVC voice conversion
MusicGen / Suno external
AudioGen SFX
```

---

## Module 11 — Lip Sync

### Engine options

```text
MuseTalk: tốt cho talking head, nhanh
SadTalker: dễ dùng, hợp portrait
Wav2Lip: ổn định, phổ biến
```

### MVP

Chỉ hỗ trợ:

```text
portrait talking shot
```

Không cố làm full-body lip sync ngay.

---

## Module 12 — Composer / Post-production

Module ghép tất cả lại bằng FFmpeg.

### Chức năng

```text
Combine clips
Add subtitles
Add background music
Add SFX
Add camera motion
Add overlays
Color grading LUT
Export 720p/1080p
```

### FFmpeg tasks

```text
image to video
video concat
audio mix
subtitle burn-in
scale/crop 9:16
fps convert
compression
```

---

## Module 13 — Render Queue

Mọi tác vụ AI/video phải chạy async.

### Job types

```text
GENERATE_CHARACTER
GENERATE_BACKGROUND
GENERATE_KEYFRAME
GENERATE_ANIMATION
GENERATE_VOICE
LIP_SYNC
COMPOSE_VIDEO
EXPORT_FINAL
```

### Job entity

```json
{
  "id": "job_001",
  "type": "GENERATE_KEYFRAME",
  "status": "queued",
  "progress": 0,
  "input": {},
  "output": {},
  "error": null
}
```

---

## 4. Folder structure

```text
ai-2d-flow/
├── apps/
│   ├── web/                    # Next.js studio UI
│   └── api/                    # FastAPI backend
├── packages/
│   ├── shared/                 # shared types/schema
│   └── prompt-templates/       # prompt compiler templates
├── workers/
│   ├── story-worker/
│   ├── image-worker/
│   ├── animation-worker/
│   ├── audio-worker/
│   ├── lipsync-worker/
│   └── composer-worker/
├── workflows/
│   └── comfyui/                # ComfyUI workflow JSON
├── storage/
│   ├── projects/
│   ├── models/
│   ├── cache/
│   └── exports/
├── infra/
│   ├── docker-compose.yml
│   └── nginx/
├── scripts/
│   ├── setup_models.py
│   ├── render_test_scene.py
│   └── seed_demo_project.py
└── README.md
```

---

## 5. Database schema MVP

### projects

```sql
id
name
style
aspect_ratio
status
created_at
updated_at
```

### characters

```sql
id
project_id
name
role
character_json
reference_asset_id
created_at
updated_at
```

### scenes

```sql
id
project_id
title
description
duration
continuity_json
created_at
updated_at
```

### shots

```sql
id
scene_id
order_index
duration
shot_json
status
created_at
updated_at
```

### assets

```sql
id
project_id
type
path
metadata_json
created_at
updated_at
```

### jobs

```sql
id
project_id
type
status
progress
input_json
output_json
error
created_at
updated_at
```

---

## 6. API MVP

```text
POST   /projects
GET    /projects
GET    /projects/{id}

POST   /projects/{id}/characters
POST   /characters/{id}/generate-image

POST   /projects/{id}/scenes
POST   /scenes/{id}/shots
POST   /shots/{id}/compile-prompt

POST   /shots/{id}/generate-keyframe
POST   /shots/{id}/generate-animation
POST   /shots/{id}/generate-audio
POST   /shots/{id}/compose

GET    /jobs/{id}
GET    /assets/{id}
GET    /projects/{id}/exports
```

---

## 7. MVP đầu tiên nên build

### MVP 0 — không cần AI nặng

```text
Create project
Create character JSON
Create scene JSON
Create shot JSON
Compile prompt
Use 1 uploaded image as keyframe
Generate voice by edge-tts
FFmpeg zoom/pan + subtitle + audio
Export 8s MP4
```

Mục tiêu: chứng minh pipeline end-to-end.

---

### MVP 1 — thêm image generation

```text
ComfyUI generate main character image
ComfyUI generate background
Generate keyframe
Export video with camera motion
```

---

### MVP 2 — thêm animation

```text
AnimateDiff / MuseTalk
RIFE interpolation
Composer final
```

---

### MVP 3 — thêm consistency

```text
IPAdapter reference main character
Asset reuse
Scene state memory
Prompt compiler nâng cấp
```

---

## 8. Nguyên tắc tối ưu chi phí

```text
1. Không generate lại asset đã có.
2. Clip ngắn 4–8 giây.
3. Dùng FFmpeg motion khi có thể.
4. Dùng image-to-video thay vì text-to-video.
5. Render local trước, cloud chỉ dùng cho batch lớn.
6. Cache prompt, seed, workflow, output.
7. Tách shot type để chọn engine rẻ nhất.
```

---

## 9. Shot routing cost policy

```text
if shot_type == "dialogue_closeup":
    engine = "musetalk"
elif shot_type == "cinematic_slow":
    engine = "animatediff"
elif shot_type == "static_intro":
    engine = "ffmpeg_motion"
elif shot_type == "complex_action":
    engine = "cloud_wan_later"
```

---

## 10. Demo project đầu tiên

### Title

```text
Đô Thị Tu Tiên: Thiếu Gia Ẩn Thân
```

### Main character

```text
Lâm Hàn — nam chính đẹp trai, sinh viên bình thường ngoài mặt, thực ra là người thừa kế gia tộc tu tiên cổ đại. Tóc đen layer, áo khoác đen, ánh mắt lạnh, long khí vàng ẩn sau lưng.
```

### Scene 1

```text
Đêm mưa trước cổng đại học trong thành phố neon. Lâm Hàn đứng im, long khí vàng hiện ra sau lưng, đám thiếu gia xung quanh bắt đầu sợ hãi.
```

### Shot 1

```text
Duration: 8s
Camera: slow push-in, medium close-up
Motion: rain, coat flutter, golden dragon aura forming
Dialogue: “Các ngươi... còn chưa đủ tư cách biết ta là ai.”
Output: vertical 9:16 MP4
```

---

## 11. Thứ tự code khuyến nghị

```text
1. Define schemas Pydantic
2. Create FastAPI CRUD
3. Create storage manager
4. Create job queue
5. Create prompt compiler
6. Create FFmpeg composer
7. Add edge-tts
8. Add ComfyUI client
9. Add animation worker
10. Add frontend studio
```

---

## 12. Definition of Done cho bản đầu

Bản đầu được xem là thành công nếu:

```text
User nhập concept
→ hệ thống tạo project
→ có character sheet
→ có shot JSON
→ compile ra prompt
→ dùng một ảnh keyframe
→ sinh audio
→ tạo video 8 giây có zoom, mưa, subtitle, nhạc nền
→ export MP4
```

