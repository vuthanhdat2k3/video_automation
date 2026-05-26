"""Transition FFmpeg xfade filter chain builder."""
from __future__ import annotations


class TransitionService:
    """Build xfade filter_complex chains for scene transitions.

    Supports 14 transition types via FFmpeg xfade filter.
    """

    XFADE_MAP: dict[str, str] = {
        "fade": "fade",
        "dissolve": "fade",
        "fadeblack": "fadeblack",
        "fadewhite": "fadewhite",
        "wipeleft": "wipeleft",
        "wiperight": "wiperight",
        "wipeup": "wipeup",
        "wipedown": "wipedown",
        "slideleft": "slideleft",
        "slideright": "slideright",
        "slideup": "slideup",
        "slidedown": "slidedown",
        "circlecrop": "circlecrop",
        "radial": "radial",
    }

    @classmethod
    def build_xfade_chain(
        cls,
        segment_labels: list[str],
        transition_styles: list[str],
        segment_durations: list[float],
        transition_duration: float = 0.5,
    ) -> tuple[str, str]:
        """Build xfade filter_complex chain.

        For N segments with N-1 transitions:
          [s0][s1]xfade=transition=fade:duration=0.5:offset=3.5[x1]
          [x1][s2]xfade=transition=wipeleft:duration=0.5:offset=6.5[x2]

        Returns (filter_string, last_output_label).
        """
        n = len(segment_labels)
        if n < 2:
            return "", segment_labels[0] if n == 1 else ""

        filter_parts = []
        last_label = segment_labels[0]
        cumulative_offset = segment_durations[0]

        for i in range(1, n):
            style = transition_styles[i - 1] if i - 1 < len(transition_styles) else "fade"
            xfade_name = cls.XFADE_MAP.get(style, "fade")
            offset = cumulative_offset - transition_duration
            next_out = f"x{i}"
            filter_parts.append(
                f"[{last_label}][{segment_labels[i]}]"
                f"xfade=transition={xfade_name}:duration={transition_duration}:offset={max(offset, 0)}"
                f"[{next_out}]"
            )
            last_label = next_out
            cumulative_offset += segment_durations[i]

        return "\n".join(filter_parts), last_label

    @classmethod
    def get_filter_string(
        cls,
        segment_labels: list[str],
        transition_styles: list[str],
        segment_durations: list[float],
        transition_duration: float = 0.5,
    ) -> str:
        """Same as build_xfade_chain but returns just the filter string."""
        chain, _ = cls.build_xfade_chain(
            segment_labels, transition_styles, segment_durations, transition_duration
        )
        return chain
