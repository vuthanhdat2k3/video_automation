from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import NotFoundException
from app.models.shot import ShotModel


class TTSService:
    """Text-to-speech service for shot narration."""

    def __init__(self, db: AsyncSession | None = None, provider: str = "edge_tts"):
        self.db = db
        self.provider = provider

    async def generate_speech(self, text: str, voice: str = "vi-VN-NamMinhNeural") -> bytes:
        """Generate speech audio from text. Returns MP3 bytes."""
        if self.provider == "openai":
            return await self._generate_openai(text, voice)
        return await self._generate_edge_tts(text, voice)

    async def _generate_edge_tts(self, text: str, voice: str) -> bytes:
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, voice)
            result = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    result += chunk["data"]
            if not result:
                raise RuntimeError("No audio data from edge_tts")
            return result
        except ImportError:
            raise RuntimeError("edge_tts not installed. Run: uv add edge-tts")
        except Exception as e:
            raise RuntimeError(f"edge_tts failed: {e}")

    async def _generate_openai(self, text: str, voice: str) -> bytes:
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url=settings.llm_base_url.replace("/chat", ""),
                api_key=settings.llm_api_key or "sk-default",
            )
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text,
            )
            return response.content
        except ImportError:
            raise RuntimeError("openai not installed. Run: uv add openai")
        except Exception as e:
            raise RuntimeError(f"OpenAI TTS failed: {e}")

    async def generate_for_shot(self, shot_id: UUID) -> tuple[bytes, str]:
        """Generate narration audio for a shot. Returns (audio_bytes, text_used)."""
        result = await self.db.execute(select(ShotModel).where(ShotModel.id == shot_id))
        shot = result.scalar_one_or_none()
        if not shot:
            raise NotFoundException(f"Shot {shot_id} not found")

        text = shot.description or shot.generation_prompt or ""
        if not text:
            raise RuntimeError(f"Shot {shot_id} has no description or prompt for TTS")

        audio_cfg = shot.audio
        voice = audio_cfg.voice_profile or "vi-VN-NamMinhNeural"

        audio_bytes = await self.generate_speech(text, voice)
        return audio_bytes, text
