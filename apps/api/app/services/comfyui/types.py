from typing import Any

from typing_extensions import TypedDict


class ComfyUIQueueResponse(TypedDict):
    prompt_id: str
    number: int
    node_errors: dict[str, Any]


class ComfyUIHistoryNode(TypedDict, total=False):
    images: list[dict[str, Any]]
    texts: list[str]


class ComfyUIHistory(TypedDict, total=False):
    prompt: list[Any]
    outputs: dict[str, ComfyUIHistoryNode]
    status: dict[str, Any]


class ComfyUIClientConfig(TypedDict, total=False):
    base_url: str
    timeout: int
