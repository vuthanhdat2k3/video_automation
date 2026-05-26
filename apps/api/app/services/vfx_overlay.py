"""VFX overlay FFmpeg filter generation."""
from __future__ import annotations


class VFXOverlayService:
    """Generate FFmpeg filter_complex snippets for VFX overlays."""

    @staticmethod
    def get_rain_filter(width: int, height: int, opacity: float = 0.3) -> str:
        """Rain overlay filter_complex for a single input stream.

        Assumes input label [v], outputs [v_rain].
        Rain overlay MP4 is expected at storage/vfx/rain_overlay.mp4.
        """
        alpha = min(max(opacity, 0), 1)
        return (
            f"movie=storage/vfx/rain_overlay.mp4:loop=0,setpts=N/FRAME_RATE/TB[rain];"
            f"[v][rain]overlay=shortest=1:format=auto,"
            f"colorchannelmixer=aa={alpha}[v_rain]"
        )

    @staticmethod
    def get_aura_filter(intensity: float = 0.5, color: str = "gold") -> str:
        """Spiritual aura glow effect for a single input stream.

        Assumes input label [v], outputs [v_aura].
        Uses split → gblur → colorize → blend=screen.
        """
        sig = max(intensity * 10, 1)
        r, g, b = VFXOverlayService._color_to_rgb(color)
        return (
            f"[v]split[orig][blur_src];"
            f"[blur_src]gblur=sigma={sig}[blurred];"
            f"[blurred]colorize=hue=0:lightness=50:saturation=50,"
            f"colorchannelmixer=rr={r/255}:gg={g/255}:bb={b/255}[colored];"
            f"[orig][colored]blend=screen:c0=1:c1=1[v_aura]"
        )

    @staticmethod
    def get_overlay_filter(
        overlay_input_label: str,
        x: int = 0,
        y: int = 0,
        opacity: float = 1.0,
    ) -> str:
        """Generic overlay for compositing one stream over another."""
        if opacity < 1.0:
            return (
                f"[{overlay_input_label}]colorchannelmixer=aa={min(max(opacity,0),1)}[ov];"
                f"[v][ov]overlay=x={x}:y={y}[v]"
            )
        return f"[v][{overlay_input_label}]overlay=x={x}:y={y}[v]"

    @staticmethod
    def _color_to_rgb(color: str) -> tuple[int, int, int]:
        mapping = {
            "gold": (255, 215, 0),
            "red": (255, 0, 0),
            "blue": (0, 100, 255),
            "green": (0, 255, 0),
            "white": (255, 255, 255),
            "purple": (128, 0, 255),
        }
        return mapping.get(color.lower(), (255, 215, 0))
