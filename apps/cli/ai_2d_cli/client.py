"""HTTP client for the pipeline API."""
import os
from uuid import UUID

import httpx

API_BASE = os.getenv("PIPELINE_API_URL", "http://localhost:8000/api/v1")


def _client() -> httpx.Client:
    return httpx.Client(base_url=API_BASE, timeout=120)


def _resp(resp: httpx.Response) -> dict:
    resp.raise_for_status()
    body = resp.json()
    if body.get("error"):
        raise RuntimeError(body["error"])
    return body["data"]


# ── Projects ──

def list_projects() -> list[dict]:
    r = _client().get("/projects")
    return _resp(r)


def create_project(name: str, style: str = "2d_anime", aspect_ratio: str = "9:16") -> dict:
    r = _client().post("/projects", json={
        "name": name, "style": style, "aspect_ratio": aspect_ratio,
    })
    return _resp(r)


def get_project(project_id: str) -> dict:
    r = _client().get(f"/projects/{project_id}")
    return _resp(r)


def delete_project(project_id: str) -> None:
    _client().delete(f"/projects/{project_id}")


# ── Story ──


def generate_story(project_id: str, concept: str | None = None) -> dict:
    body = {"concept": concept} if concept else {}
    r = _client().post(f"/projects/{project_id}/story/generate", json=body)
    return _resp(r)


def materialize_story(project_id: str) -> dict:
    r = _client().post(f"/projects/{project_id}/story/materialize")
    return _resp(r)


# ── Export ──


def export_project(project_id: str) -> dict:
    r = _client().post(f"/projects/{project_id}/export")
    return _resp(r)


def export_scene(scene_id: str) -> dict:
    r = _client().post(f"/scenes/{scene_id}/export")
    return _resp(r)


# ── Jobs ──


def list_jobs(project_id: str) -> list[dict]:
    r = _client().get(f"/projects/{project_id}/jobs")
    return _resp(r)


def get_job(job_id: str) -> dict:
    r = _client().get(f"/jobs/{job_id}")
    return _resp(r)


def cancel_jobs(project_id: str) -> dict:
    r = _client().delete(f"/projects/{project_id}/jobs")
    return _resp(r)


# ── Batch Generation ──


def generate_all_keyframes(scene_id: str) -> dict:
    r = _client().post(f"/scenes/{scene_id}/generate-all-keyframes")
    return _resp(r)


def generate_all_audio(scene_id: str) -> dict:
    r = _client().post(f"/scenes/{scene_id}/generate-all-audio")
    return _resp(r)
