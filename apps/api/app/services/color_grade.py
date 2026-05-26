"""Color grading FFmpeg filter generation."""
from __future__ import annotations


class ColorGradeService:
    """Generate FFmpeg filter strings for color grading.

    Filter order: eq → colorbalance → lut3d.
    This matches standard post-production workflow.
    """

    @staticmethod
    def get_filter_string(
        lut_path: str | None = None,
        colorbalance: dict | None = None,
        eq_params: dict | None = None,
    ) -> str:
        """Return comma-joined filter chain, or empty string if none set.

        eq_params keys: brightness, contrast, saturation, gamma, gamma_r, gamma_g, gamma_b
        colorbalance keys: rs, gs, bs, rh, gh, bh (shadow/highlight)
        lut_path: path to .cube file
        """
        filters = []

        if eq_params:
            parts = []
            for k in ("brightness", "contrast", "saturation", "gamma", "gamma_r", "gamma_g", "gamma_b"):
                if k in eq_params:
                    parts.append(f"{k}={eq_params[k]}")
            if parts:
                filters.append(f"eq={':'.join(parts)}")

        if colorbalance:
            parts = []
            for k in ("rs", "gs", "bs", "rh", "gh", "bh"):
                if k in colorbalance:
                    parts.append(f"{k}={colorbalance[k]}")
            if parts:
                filters.append(f"colorbalance={':'.join(parts)}")

        if lut_path:
            filters.append(f"lut3d=file={lut_path}")

        return ",".join(filters)
