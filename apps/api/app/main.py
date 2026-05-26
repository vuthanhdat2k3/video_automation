from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import engine
from .exceptions import AppException, app_exception_handler
from .routers import assets, characters, health, jobs, projects, story, scenes, shots, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="AI 2D Animation Studio API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/storage", StaticFiles(directory=settings.storage_root), name="storage")

app.add_exception_handler(AppException, app_exception_handler)


@app.middleware("http")
async def catch_all_errors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"data": None, "error": {"code": 500, "message": str(exc)}},
        )


app.include_router(assets.router, prefix="/api/v1", tags=["assets"])
app.include_router(characters.router, prefix="/api/v1", tags=["characters"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
app.include_router(story.router, prefix="/api/v1", tags=["story"])
app.include_router(scenes.router, prefix="/api/v1", tags=["scenes"])
app.include_router(shots.router, prefix="/api/v1", tags=["shots"])
app.include_router(ws.router, prefix="/api/v1", tags=["ws"])
