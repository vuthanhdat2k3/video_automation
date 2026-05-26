# AI 2D Animation Studio — AGENT.md

## Project Overview

AI 2D Animation Studio is a **Google Flow lite** system for producing 2D Chinese donghua animated films. The pipeline transforms raw ideas/prompts into finished animated videos through a structured, modular workflow.

### Mission

```text
Ý tưởng / prompt
→ Story Bible → Characters/Backgrounds/Props → Shot Plan
→ Keyframe → Animation → Audio/Lip Sync → Edit/Subtitle/Export
```

### MVP Target

- 1 main character + 1 urban xianxia background + 1 scene (8–15s)
- Voice, subtitles, light camera motion
- Export 9:16 vertical MP4

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js + Tailwind + shadcn/ui | Studio UI |
| Backend | FastAPI (Python) | API Gateway + Orchestrator |
| Queue | Redis + RQ or Celery | Async render jobs |
| Database | PostgreSQL | Project, character, scene, shot, job state |
| Asset Storage | Local filesystem → MinIO later | Images, audio, video assets |
| AI Engine | ComfyUI API | Image generation, animation |
| Video | FFmpeg | Composition, camera motion, export |
| Audio | edge-tts → XTTS later | Voice generation |
| Lip Sync | MuseTalk / Wav2Lip | Talking head animation |

### Why This Stack

- **FastAPI** — easy Python integration with AI tools, async-native
- **ComfyUI** — leverages local RTX 3060 12GB efficiently
- **FFmpeg** — cheap, powerful, batch-capable
- **PostgreSQL** — robust relational data for structured animation pipeline
- **Redis** — prevents API blocking during render jobs

---

## Project Structure

```text
ai-2d-flow/
├── apps/
│   ├── web/                     # Next.js Studio UI
│   └── api/                     # FastAPI backend
├── packages/
│   ├── shared/                  # Shared types & schemas (Pydantic → TypeScript)
│   └── prompt-templates/        # Prompt compiler templates
├── workers/
│   ├── story-worker/            # Story Bible generation
│   ├── image-worker/            # Keyframe & character generation
│   ├── animation-worker/        # Animation (AnimateDiff, MuseTalk)
│   ├── audio-worker/            # TTS, BGM, SFX
│   ├── lipsync-worker/          # Lip sync processing
│   └── composer-worker/         # FFmpeg video assembly
├── workflows/
│   └── comfyui/                 # ComfyUI workflow JSON files
├── storage/                     # Asset storage root
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

## Module Map

| # | Module | Responsibility |
|---|--------|---------------|
| 1 | **Project Studio** | CRUD projects, metadata, style, aspect ratio |
| 2 | **Story Bible / LLM** | Generate world, characters, episodes, scene breakdown from prompt |
| 3 | **Character System** | Character DNA, image gen, expression packs, LoRA training |
| 4 | **Asset Store** | Ingredients storage, caching, reuse across shots |
| 5 | **Scene System** | Scene as story unit, continuity state tracking |
| 6 | **Shot Planner** | Shot breakdown with camera, motion, audio specs |
| 7 | **Prompt Compiler** | JSON shot → structured prompts for each engine |
| 8 | **Keyframe Generator** | ComfyUI image gen for start/end/thumb frames |
| 9 | **Animation Engine** | Keyframe → video via AnimateDiff, MuseTalk, FFmpeg |
| 10 | **Audio Pipeline** | TTS dialogue, BGM, SFX, mixing |
| 11 | **Lip Sync** | Portrait talking head sync (MuseTalk/Wav2Lip) |
| 12 | **Composer** | FFmpeg clip assembly, subtitles, color grading, export |
| 13 | **Render Queue** | Async job management, progress tracking |

---

## Database Schema (MVP)

### projects
```sql
id UUID PRIMARY KEY
name VARCHAR
style VARCHAR
aspect_ratio VARCHAR DEFAULT '9:16'
status VARCHAR DEFAULT 'draft'
created_at TIMESTAMP
updated_at TIMESTAMP
```

### characters
```sql
id UUID PRIMARY KEY
project_id UUID FK → projects
name VARCHAR
role VARCHAR
character_json JSONB
reference_asset_id UUID FK → assets
created_at TIMESTAMP
updated_at TIMESTAMP
```

### scenes
```sql
id UUID PRIMARY KEY
project_id UUID FK → projects
title VARCHAR
description TEXT
duration INT DEFAULT 8
continuity_json JSONB
created_at TIMESTAMP
updated_at TIMESTAMP
```

### shots
```sql
id UUID PRIMARY KEY
scene_id UUID FK → scenes
order_index INT
duration INT DEFAULT 8
shot_json JSONB
status VARCHAR DEFAULT 'draft'
created_at TIMESTAMP
updated_at TIMESTAMP
```

### assets
```sql
id UUID PRIMARY KEY
project_id UUID FK → projects
type VARCHAR
path VARCHAR
metadata_json JSONB
created_at TIMESTAMP
updated_at TIMESTAMP
```

### jobs
```sql
id UUID PRIMARY KEY
project_id UUID FK → projects
type VARCHAR
status VARCHAR DEFAULT 'queued'
progress INT DEFAULT 0
input_json JSONB
output_json JSONB
error TEXT
created_at TIMESTAMP
updated_at TIMESTAMP
```

---

## API Design (MVP)

```text
Projects:
  POST   /api/v1/projects
  GET    /api/v1/projects
  GET    /api/v1/projects/{id}
  PATCH  /api/v1/projects/{id}

Characters:
  POST   /api/v1/projects/{id}/characters
  GET    /api/v1/projects/{id}/characters
  POST   /api/v1/characters/{id}/generate-image

Scenes:
  POST   /api/v1/projects/{id}/scenes
  GET    /api/v1/scenes/{id}

Shots:
  POST   /api/v1/scenes/{id}/shots
  POST   /api/v1/shots/{id}/compile-prompt
  POST   /api/v1/shots/{id}/generate-keyframe
  POST   /api/v1/shots/{id}/generate-animation
  POST   /api/v1/shots/{id}/generate-audio
  POST   /api/v1/shots/{id}/compose

Jobs:
  GET    /api/v1/jobs/{id}

Assets:
  GET    /api/v1/assets/{id}
  GET    /api/v1/projects/{id}/exports
```

---

## Coding Conventions

### Python (FastAPI)
- **Pydantic v2** for all schemas — strict validation, no loose dicts
- UUIDs as primary keys for all entities
- Async endpoints with `async def` where I/O occurs
- Service layer pattern: routers → services → repositories
- Use `alembic` for database migrations
- Environment config via `pydantic-settings`
- Type hints on ALL functions, no exceptions
- Error handling: custom exception classes, consistent error response schema

### TypeScript / React (Next.js)
- Use **const** for non-reassigned variables
- **TypeScript strict mode**
- React Server Components where possible, client components only when interactive
- shadcn/ui component library, never custom unstyled components
- Tailwind for all styling, no CSS modules
- API client with typed fetch wrapper (no axios)

### General
- Monorepo with workspace configuration
- Conventional commit messages
- Tests for services, not for trivial CRUD
- Docker Compose for local dev environment
- `.env.example` for all required environment variables

---

## Key Principles

1. **Never regenerate existing assets** — check cache first
2. **Short clips** — 4–8 seconds per shot
3. **FFmpeg motion over AI animation** when quality is comparable
4. **Image-to-video over text-to-video** for consistency
5. **Local render first**, cloud only for batch throughput
6. **Cache everything** — prompts, seeds, workflows, outputs
7. **Route shots by type** to cheapest capable engine
8. **Compile prompts through structured template**, never raw user input to model

---

## Shot Routing Policy

```python
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

## MVP Implementation Order

```text
1. Define Pydantic schemas (shared package)
2. FastAPI CRUD (projects, characters, scenes, shots)
3. Storage manager (local filesystem)
4. Job queue (Redis + RQ)
5. Prompt compiler
6. FFmpeg composer
7. edge-tts integration
8. ComfyUI client
9. Animation worker
10. Next.js frontend studio
```

---

## Definition of Done (First Release)

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
