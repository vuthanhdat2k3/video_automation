from ai_2d_shared.character import CharacterDNA

from app.config import settings
from app.services.character_dna import CharacterDNAService
from app.services.comfyui.client import ComfyUIClient


class ImageGenError(Exception):
    pass


class ImageGenService:
    def __init__(self):
        self.dna_service = CharacterDNAService()
        self.comfyui = ComfyUIClient(
            base_url=settings.comfyui_base_url,
            timeout=settings.comfyui_timeout,
        )

    async def generate_character_portrait(
        self,
        dna: CharacterDNA,
        style: str = "2d_chinese_donghua",
        expression: str = "neutral",
        pose: str = "standing",
        seed: int | None = None,
        width: int = 1024,
        height: int = 1536,
        steps: int = 25,
        cfg: float = 5.0,
    ) -> bytes:
        """Generate a character portrait from DNA. Returns PNG bytes."""
        prompt = self.dna_service.generate_image_prompt(dna, style)

        expression_modifiers = {
            "neutral": "",
            "happy": ", smiling, happy expression, bright eyes",
            "angry": ", angry expression, furrowed brows, fierce look",
            "sad": ", sad expression, teary eyes, downturned mouth",
            "surprised": ", surprised expression, wide eyes, open mouth",
        }
        pose_modifiers = {
            "standing": "full body standing pose",
            "portrait": "close-up portrait",
            "action": "dynamic action pose, mid-motion",
            "sitting": "sitting pose",
        }

        parts = [prompt]
        if expression in expression_modifiers:
            parts.append(expression_modifiers[expression])
        if pose in pose_modifiers:
            parts.append(pose_modifiers[pose])
        full_prompt = ", ".join(p for p in parts if p)

        negative_prompt = (
            "low quality, blurry, distorted, bad anatomy, extra limbs, "
            "watermark, signature, ugly, deformed, disfigured, nsfw"
        )

        try:
            png_bytes = await self.comfyui.generate_image(
                positive_prompt=full_prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                seed=seed,
                steps=steps,
                cfg=cfg,
            )
            return png_bytes
        except Exception as e:
            raise ImageGenError(f"Image generation failed: {e}") from e
