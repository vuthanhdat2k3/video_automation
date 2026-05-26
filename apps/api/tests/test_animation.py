"""Tests for camera motion, subtitle, and audio mixing services."""
import json

import pytest

from app.services.camera import CameraMotionService
from app.services.subtitle import SubtitleService
from app.services.audio_mixer import AudioMixer
from app.models.shot import ShotModel
from ai_2d_shared.shot import CameraConfig, MotionConfig, AudioConfig


@pytest.mark.asyncio
async def test_camera_static():
    """Static movement → scale filter only."""
    shot = ShotModel(
        scene_id="00000000-0000-0000-0000-000000000001",
        order_index=0, duration_seconds=4.0,
        camera_json={"movement": "static"},
    )
    filters = CameraMotionService.get_filters(shot, 1080, 1920)
    assert filters == ["scale=1080:1920"]
    vf = CameraMotionService.get_filter_string(shot, 1080, 1920)
    assert vf == "scale=1080:1920"


@pytest.mark.asyncio
async def test_camera_zoom_in():
    """Zoom_in adds scale + crop + resize."""
    shot = ShotModel(
        scene_id="00000000-0000-0000-0000-000000000001",
        order_index=0, duration_seconds=4.0,
        camera_json={"movement": "zoom_in"},
    )
    filters = CameraMotionService.get_filters(shot, 1080, 1920)
    assert "scale=iw*1.1:ih*1.1:flags=bilinear" in filters
    assert "scale=1080:1920:force_original_aspect_ratio=decrease" in filters


@pytest.mark.asyncio
async def test_camera_handheld():
    """Handheld adds crop + setpts + scale + pad."""
    shot = ShotModel(
        scene_id="00000000-0000-0000-0000-000000000001",
        order_index=0, duration_seconds=4.0,
        camera_json={"movement": "handheld"},
    )
    filters = CameraMotionService.get_filters(shot, 1080, 1920)
    assert any("crop" in f for f in filters)


@pytest.mark.asyncio
async def test_camera_unknown_movement_fallback():
    """Unknown movement falls back to static."""
    shot = ShotModel(
        scene_id="00000000-0000-0000-0000-000000000001",
        order_index=0, duration_seconds=4.0,
        camera_json={"movement": "unknown_xyz"},
    )
    filters = CameraMotionService.get_filters(shot, 1080, 1920)
    assert any("scale=1080:1920" in f for f in filters)


@pytest.mark.asyncio
async def test_subtitle_generation():
    """Generate ASS content from shot descriptions."""
    shot1 = ShotModel(
        scene_id="00000000-0000-0000-0000-000000000001",
        order_index=0, duration_seconds=4.0, description="Hello world",
    )
    shot2 = ShotModel(
        scene_id="00000000-0000-0000-0000-000000000001",
        order_index=1, duration_seconds=3.0, description="Second line",
    )

    ass = SubtitleService.generate_subs([shot1, shot2], width=1080, height=1920)
    assert "[Script Info]" in ass
    assert "PlayResX: 1080" in ass
    assert "PlayResY: 1920" in ass
    assert "Hello world" in ass
    assert "Second line" in ass
    assert "Noto Sans SC" in ass
    # Timestamps: shot1 starts at 0, ends at 4. shot2 starts at 4, ends at 7
    assert "0:00:00.00" in ass  # shot1 start
    assert "0:00:04.00" in ass  # shot1 end / shot2 start
    assert "0:00:07.00" in ass  # shot2 end


@pytest.mark.asyncio
async def test_subtitle_skips_empty():
    """Shots without description are skipped."""
    shot = ShotModel(
        scene_id="00000000-0000-0000-0000-000000000001",
        order_index=0, duration_seconds=4.0, description=None,
    )
    ass = SubtitleService.generate_subs([shot])
    # Header present, no dialogue
    assert "[Events]" in ass
    assert "Dialogue:" not in ass


@pytest.mark.asyncio
async def test_subtitle_time_format():
    """Time format is H:MM:SS.cc."""
    assert SubtitleService._format_time(0) == "0:00:00.00"
    assert SubtitleService._format_time(65.5) == "0:01:05.50"
    assert SubtitleService._format_time(3661) == "1:01:01.00"


@pytest.mark.asyncio
async def test_audio_mixer_empty():
    """Mixer with no inputs returns empty bytes."""
    mixer = AudioMixer()
    result = await mixer.mix_for_scene(
        scene_id="00000000-0000-0000-0000-000000000001",
        narration_paths=[],
    )
    assert result == b""


@pytest.mark.asyncio
async def test_subtitle_overlay_filter():
    """Overlay filter contains subtitles command."""
    from pathlib import Path
    filt = SubtitleService.get_overlay_filter(Path("/tmp/subs.ass"))
    assert "subtitles=" in filt
    assert "subs.ass" in filt
    assert "Noto Sans SC" in filt
    assert "Force_style" in filt or "force_style" in filt
