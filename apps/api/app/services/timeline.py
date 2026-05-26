from typing import Any

from ai_2d_shared.shot import ShotRead


def compute_scene_timeline(shots: list[ShotRead]) -> dict[str, Any]:
    """Compute cumulative timing for shots in a scene."""
    total_duration = 0.0
    shot_timelines = []
    for s in shots:
        sd = s.model_dump()
        shot_timelines.append({
            "shot": sd,
            "start_at": round(total_duration, 2),
            "end_at": round(total_duration + s.duration_seconds, 2),
        })
        total_duration += s.duration_seconds
    return {
        "start_at": 0.0,
        "total_duration": round(total_duration, 2),
        "shot_count": len(shots),
        "shots": shot_timelines,
    }
