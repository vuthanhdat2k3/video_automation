"""Tests for post-production services: color grade, VFX, shadow, transitions."""
import pytest

from app.services.color_grade import ColorGradeService
from app.services.vfx_overlay import VFXOverlayService
from app.services.shadow import ShadowService
from app.services.transition import TransitionService


class TestColorGrade:
    def test_no_grading(self):
        assert ColorGradeService.get_filter_string() == ""

    def test_lut3d(self):
        result = ColorGradeService.get_filter_string(lut_path="/tmp/test.cube")
        assert "lut3d=file=" in result
        assert "test.cube" in result

    def test_eq_brightness(self):
        result = ColorGradeService.get_filter_string(eq_params={"brightness": "0.1"})
        assert "eq=" in result
        assert "brightness=0.1" in result

    def test_colorbalance(self):
        result = ColorGradeService.get_filter_string(colorbalance={"rs": "0.2", "bs": "-0.1"})
        assert "colorbalance=" in result
        assert "rs=0.2" in result
        assert "bs=-0.1" in result

    def test_combined_order(self):
        """Filter order: eq → colorbalance → lut3d."""
        result = ColorGradeService.get_filter_string(
            eq_params={"brightness": "0.1"},
            colorbalance={"rs": "0.2"},
            lut_path="test.cube",
        )
        parts = result.split(",")
        assert parts[0].startswith("eq=")
        assert parts[1].startswith("colorbalance=")
        assert parts[2].startswith("lut3d=")


class TestVFX:
    def test_rain_filter(self):
        result = VFXOverlayService.get_rain_filter(1080, 1920, 0.5)
        assert "rain_overlay" in result
        assert "overlay=" in result
        assert "colorchannelmixer=aa=0.5" in result

    def test_aura_filter(self):
        result = VFXOverlayService.get_aura_filter(0.5, "gold")
        assert "gblur=" in result
        assert "blend=screen" in result

    def test_aura_default_color(self):
        """Unknown color falls back to gold."""
        result = VFXOverlayService.get_aura_filter(0.3, "neon_pink")
        assert "gblur=sigma=3" in result

    def test_overlay_default(self):
        result = VFXOverlayService.get_overlay_filter("ov", x=10, y=20, opacity=1.0)
        assert "[v][ov]overlay=x=10:y=20[v]" in result

    def test_overlay_with_opacity(self):
        result = VFXOverlayService.get_overlay_filter("ov", opacity=0.5)
        assert "colorchannelmixer=aa=0.5" in result


class TestShadow:
    def test_shadow_filter(self):
        result = ShadowService.get_shadow_filter()
        assert "split[orig]" in result
        assert "gblur=sigma=3" in result
        assert "overlay=x=5:y=5" in result

    def test_shadow_custom(self):
        result = ShadowService.get_shadow_filter(offset_x=10, offset_y=15, blur_sigma=5)
        assert "gblur=sigma=5" in result
        assert "overlay=x=10:y=15" in result


class TestTransition:
    def test_xfade_map_all_styles(self):
        """All 14 transition styles map to valid xfade values."""
        styles = [
            "fade", "dissolve", "fadeblack", "fadewhite",
            "wipeleft", "wiperight", "wipeup", "wipedown",
            "slideleft", "slideright", "slideup", "slidedown",
            "circlecrop", "radial",
        ]
        for s in styles:
            assert s in TransitionService.XFADE_MAP

    def test_xfade_two_segments(self):
        """2 segments = 1 xfade."""
        chain, last = TransitionService.build_xfade_chain(
            ["s0", "s1"],
            ["fade"],
            [4.0, 3.0],
        )
        assert "xfade" in chain
        assert "s0" in chain
        assert "s1" in chain
        assert last == "x1"

    def test_xfade_three_segments(self):
        """3 segments = 2 xfades."""
        chain, last = TransitionService.build_xfade_chain(
            ["s0", "s1", "s2"],
            ["fade", "wipeleft"],
            [4.0, 3.0, 5.0],
        )
        assert chain.count("xfade") == 2
        assert "wipeleft" in chain
        assert last == "x2"

    def test_xfade_single_segment(self):
        chain, last = TransitionService.build_xfade_chain(["s0"], [], [4.0])
        assert chain == ""
        assert last == "s0"

    def test_xfade_empty_segments(self):
        chain, last = TransitionService.build_xfade_chain([], [], [])
        assert chain == ""
        assert last == ""

    def test_get_filter_string(self):
        result = TransitionService.get_filter_string(["s0", "s1"], ["fade"], [4.0, 3.0])
        assert "xfade" in result
