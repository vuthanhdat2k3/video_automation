# AI 2D Animation Studio

A production pipeline for AI-generated 2D animation, combining LLM-driven story development with ComfyUI-based image generation and FFmpeg video assembly.

## Architecture

- **API** — FastAPI backend (Python 3.11+) with async SQLAlchemy + PostgreSQL
- **Shared** — Pydantic v2 schemas shared between API and frontend
- **Pipeline** — ComfyUI for image gen, edge-tts for voice, FFmpeg for video assembly
- **Queue** — Redis + RQ for async job processing

## Quickstart

```bash
# Start infrastructure
docker compose -f infra/docker-compose.yml up -d

# Install API dependencies
cd apps/api && pip install -e ".[dev]"

# Run migrations
cd apps/api && alembic upgrade head

# Start dev server
uvicorn app.main:app --reload --port 8000
```

## Project Structure

```
ai-2d-flow/
├── apps/api/          # FastAPI backend
├── packages/shared/   # Shared Pydantic schemas
├── infra/             # Docker, nginx configs
├── scripts/           # Dev and seed scripts
└── storage/           # Asset storage (gitignored)
```
