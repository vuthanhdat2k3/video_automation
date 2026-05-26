import asyncio
import copy
import json
import time
from pathlib import Path
from typing import Any

import httpx

WORKFLOW_DIR = Path(__file__).parent / "workflows"


def _deep_merge(base: dict, overrides: dict) -> dict:
    """Recursively merge overrides into a copy of base dict."""
    result = copy.deepcopy(base)
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class ComfyUIClientError(Exception):
    pass


class ComfyUIClient:
    """Client for ComfyUI with SDXL workflow (Animagine XL 4.0)."""

    SDXL_DEFAULTS = {
        "width": 1024,
        "height": 1536,
        "steps": 25,
        "cfg": 5.0,
        "ckpt_name": "animagine-xl-4.0-opt.safetensors",
    }

    def __init__(self, base_url: str = "http://localhost:8188", timeout: int = 300):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def generate_image(
        self,
        positive_prompt: str,
        negative_prompt: str = "",
        width: int | None = None,
        height: int | None = None,
        seed: int | None = None,
        steps: int | None = None,
        cfg: float | None = None,
        ckpt_name: str | None = None,
    ) -> bytes:
        """Queue generation and wait for result. Returns PNG bytes."""
        workflow = self._build_workflow(
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            width=width or self.SDXL_DEFAULTS["width"],
            height=height or self.SDXL_DEFAULTS["height"],
            seed=seed or int(time.time() * 1000) % (2**32),
            steps=steps or self.SDXL_DEFAULTS["steps"],
            cfg=cfg or self.SDXL_DEFAULTS["cfg"],
            ckpt_name=ckpt_name or self.SDXL_DEFAULTS["ckpt_name"],
        )
        return await self._run_workflow(workflow)

    async def generate_with_workflow(
        self,
        workflow_name: str,
        overrides: dict[str, Any] | None = None,
        seed: int | None = None,
        steps: int | None = None,
        cfg: float | None = None,
    ) -> bytes:
        """Load a workflow JSON, apply overrides, queue and download."""
        workflow_path = WORKFLOW_DIR / workflow_name
        with open(workflow_path) as f:
            workflow = json.load(f)

        if overrides:
            workflow = _deep_merge(workflow, overrides)

        # Default sampler overrides
        for node_id, node in workflow.items():
            if isinstance(node, dict) and node.get("class_type") == "KSampler":
                if seed is not None:
                    node["inputs"]["seed"] = seed
                if steps is not None:
                    node["inputs"]["steps"] = steps
                if cfg is not None:
                    node["inputs"]["cfg"] = cfg
                break

        return await self._run_workflow(workflow)

    async def _run_workflow(self, workflow: dict) -> bytes:
        prompt_id = await self._queue_prompt(workflow)
        output = await self._wait_for_result(prompt_id)
        return await self._download_image(output)

    async def _queue_prompt(self, workflow: dict) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/prompt",
                json={"prompt": workflow},
            )
            resp.raise_for_status()
            data = resp.json()
            if "node_errors" in data and data["node_errors"]:
                raise ComfyUIClientError(f"Workflow errors: {data['node_errors']}")
            return data["prompt_id"]

    async def _wait_for_result(self, prompt_id: str, poll_interval: float = 3.0) -> dict[str, Any]:
        deadline = time.time() + self.timeout
        async with httpx.AsyncClient(timeout=10) as client:
            while time.time() < deadline:
                resp = await client.get(f"{self.base_url}/history/{prompt_id}")
                if resp.status_code == 200:
                    data = resp.json()
                    if prompt_id in data:
                        history = data[prompt_id]
                        if history.get("status", {}).get("completed", False):
                            return history
                elif resp.status_code != 404:
                    resp.raise_for_status()
                await asyncio.sleep(poll_interval)
        raise ComfyUIClientError(f"Timeout waiting for prompt {prompt_id}")

    async def _download_image(self, output: dict) -> bytes:
        for node_id, node_output in output.get("outputs", {}).items():
            images = node_output.get("images", [])
            if images:
                img = images[0]
                filename = img["filename"]
                subfolder = img.get("subfolder", "")
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(
                        f"{self.base_url}/view",
                        params={"filename": filename, "subfolder": subfolder, "type": "output"},
                    )
                    resp.raise_for_status()
                    return resp.content
        raise ComfyUIClientError("No image found in output")

    def _build_workflow(
        self,
        positive_prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        seed: int,
        steps: int,
        cfg: float,
        ckpt_name: str,
    ) -> dict:
        workflow_path = WORKFLOW_DIR / "character_portrait.json"
        with open(workflow_path) as f:
            workflow = json.load(f)

        workflow = copy.deepcopy(workflow)
        # Checkpoint loader
        workflow["4"]["inputs"]["ckpt_name"] = ckpt_name
        # Latent dimensions
        workflow["5"]["inputs"]["width"] = width
        workflow["5"]["inputs"]["height"] = height
        # Sampler params
        workflow["3"]["inputs"]["seed"] = seed
        workflow["3"]["inputs"]["steps"] = steps
        workflow["3"]["inputs"]["cfg"] = cfg
        # Prompts
        workflow["6"]["inputs"]["text"] = positive_prompt
        workflow["7"]["inputs"]["text"] = negative_prompt
        return workflow
