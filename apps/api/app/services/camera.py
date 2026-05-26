"""Camera motion FFmpeg filter generation."""
from __future__ import annotations

from app.models.shot import ShotModel


class CameraMotionService:
    """Generate FFmpeg video filter chains from CameraConfig."""

    # Each movement returns a list of ffmpeg filter strings.
    # Filters are applied in sequence over the clip duration.
    MOTION_FILTERS = {
        "static": [],
        "pan_left": [
            "crop=iw-100:ih:0:0",
            f"setpts=PTS+0.5/TB",  # slow pan offset
        ],
        "pan_right": [
            "crop=iw-100:ih:100:0",
            "setpts=PTS+0.5/TB",
        ],
        "tilt_up": [
            "crop=iw:ih-80:0:80",
            "setpts=PTS+0.5/TB",
        ],
        "tilt_down": [
            "crop=iw:ih-80:0:0",
        ],
        "zoom_in": [
            "scale=iw*1.1:ih*1.1:flags=bilinear",
            f"crop=iw/1.1:ih/1.1",
        ],
        "zoom_out": [
            "scale=iw*0.9:ih*0.9:flags=bilinear",
        ],
        "dolly": [
            "scale=iw*1.05:ih*1.05:flags=bilinear",
            "crop=iw/1.05:ih/1.05",
        ],
        "handheld": [
            "crop=iw-20:ih-20:10:10",
            "setpts=PTS+0.2/TB",
        ],
    }

    @classmethod
    def get_filters(cls, shot: ShotModel, width: int, height: int) -> list[str]:
        """Return FFmpeg video filter list for camera motion on this shot."""
        movement = shot.camera.movement if shot.camera else "static"
        base_filters = cls.MOTION_FILTERS.get(movement, [])

        # Always ensure exact output resolution
        result = list(base_filters)
        if movement != "static":
            result.append(f"scale={width}:{height}:force_original_aspect_ratio=decrease")
            result.append(f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black")
        else:
            result.append(f"scale={width}:{height}")

        return result

    @classmethod
    def get_filter_string(cls, shot: ShotModel, width: int, height: int) -> str:
        """Return a single FFmpeg -vf filter chain string."""
        filters = cls.get_filters(shot, width, height)
        if not filters:
            return f"scale={width}:{height}"
        return ",".join(filters)
