"""Error classification and retry configuration."""
from __future__ import annotations

from enum import Enum


class ErrorClass(str, Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"


PERMANENT_PATTERNS = [
    "not found", "invalid", "unsupported", "permission denied",
    "does not exist", "no such", "unknown",
]


def classify_error(error_msg: str) -> ErrorClass:
    """Classify an error message as transient or permanent."""
    msg = error_msg.lower()
    for pat in PERMANENT_PATTERNS:
        if pat in msg:
            return ErrorClass.PERMANENT
    return ErrorClass.TRANSIENT


TASK_RETRY_CONFIG: dict[str, dict] = {
    "run_generate_background": {"max_retries": 3, "base_delay": 30, "backoff": 2.0},
    "run_generate_keyframe":   {"max_retries": 3, "base_delay": 30, "backoff": 2.0},
    "run_generate_audio":      {"max_retries": 3, "base_delay": 15, "backoff": 2.0},
    "run_export_scene":        {"max_retries": 2, "base_delay": 30, "backoff": 2.0},
    "run_lipsync_shot":        {"max_retries": 2, "base_delay": 60, "backoff": 2.0},
    "run_concat_project":      {"max_retries": 1, "base_delay": 30, "backoff": 2.0},
    "cleanup_cron_task":       {"max_retries": 1, "base_delay": 60, "backoff": 2.0},
}


def get_retry_delay(task_name: str, retry_count: int) -> int:
    """Calculate exponential backoff delay."""
    config = TASK_RETRY_CONFIG.get(task_name, {"base_delay": 30, "backoff": 2.0})
    return int(config["base_delay"] * (config["backoff"] ** retry_count))
