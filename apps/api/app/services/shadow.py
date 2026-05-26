"""Drop shadow FFmpeg filter generation."""
from __future__ import annotations


class ShadowService:
    """Generate FFmpeg filter_complex snippets for drop shadows.

    Works by splitting the input, creating a semi-transparent blurred
    copy, offseting it, and compositing it behind the original.
    """

    @staticmethod
    def get_shadow_filter(
        input_label: str = "v",
        output_label: str = "v_out",
        offset_x: int = 5,
        offset_y: int = 5,
        blur_sigma: int = 3,
    ) -> str:
        """Drop shadow filter_complex snippet.

        Example output:
        [v]split[orig][shadow];
        [shadow]format=rgba,colorchannelmixer=aa=0.4,gblur=sigma=3[blur];
        [blur]pad=iw+10:ih+10:5:5[blur_pad];
        [blur_pad][orig]overlay=x=5:y=5[v_out]
        """
        return (
            f"[{input_label}]split[orig][shadow_src];"
            f"[shadow_src]format=rgba,colorchannelmixer=aa=0.4[shadow_alpha];"
            f"[shadow_alpha]gblur=sigma={blur_sigma}[shadow_blur];"
            f"[orig][shadow_blur]overlay=x={offset_x}:y={offset_y}:format=auto[{output_label}]"
        )
