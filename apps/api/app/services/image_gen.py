import io
import json
from pathlib import Path
from typing import Any

from ai_2d_shared.character import CharacterDNA

from app.config import settings
from app.services.character_dna import CharacterDNAService
from app.services.comfyui.client import ComfyUIClient, WORKFLOW_DIR


class ImageGenError(Exception):
    pass


class ImageGenService:
    def __init__(self):
        self.dna_service = CharacterDNAService()
        self.comfyui = ComfyUIClient(
            base_url=settings.comfyui_base_url,
            timeout=settings.comfyui_timeout,
        )

    # ──────────── Prompt builders ────────────

    def _build_positive_prompt(self, dna: CharacterDNA, style: str, view: str = "front") -> str:
        """Build full positive prompt for image generation."""
        base = self.dna_service.generate_image_prompt(dna, style, view=view)
        quality = "illustration, digital artwork, masterpiece, high score, great score, absurdres"
        return f"{base}, {quality}"

    def _build_negative_prompt(self, dna: CharacterDNA) -> str:
        parts = [
            "lowres, bad anatomy, bad hands, text, error, missing finger",
            "extra digits, fewer digits, cropped, worst quality, low quality",
            "low score, bad score, average score, signature, watermark, username, blurry",
            "mutation, deformed, distorted, disfigured, poorly drawn, bad proportions",
            "extra limbs, missing limbs, floating limbs, disconnected limbs",
            "malformed hands, malformed feet, poorly drawn hands, poorly drawn feet",
            "bad perspective, bad composition, off-center, out of frame",
        ]
        if dna.gender in ("male", "nam"):
            parts.append("1girl, female, woman, breasts, feminine, cute girl")
        elif dna.gender in ("female", "nữ"):
            parts.append("1boy, male, man, handsome, masculine, beard, mustache")
        return ", ".join(parts)

    # ──────────── Core generation methods ────────────

    async def generate_master_front_view(
        self,
        dna: CharacterDNA,
        style: str = "2d_chinese_donghua",
        seed: int | None = None,
    ) -> bytes:
        """Generate master front view (txt2img + HiRes Fix). Returns PNG bytes."""
        prompt = self._build_positive_prompt(dna, style, view="front")
        neg = self._build_negative_prompt(dna)

        workflow_path = WORKFLOW_DIR / "character_portrait_hires.json"
        with open(workflow_path) as f:
            workflow = json.load(f)

        overrides: dict[str, Any] = {
            "3": {"inputs": {"text": prompt}},
            "4": {"inputs": {"text": neg}},
        }
        return await self.comfyui.generate_with_workflow_dict(
            workflow=workflow, overrides=overrides, seed=seed,
        )

    async def generate_view_with_reference(
        self,
        dna: CharacterDNA,
        style: str,
        view: str,
        reference_image_bytes: bytes,
        ipa_weight: float = 0.85,
        denoise: float = 0.45,
        seed: int | None = None,
    ) -> bytes:
        """Generate a character view using IPAdapter reference.

        view: "side" | "back" | "three_quarter"
        """
        prompt = self._build_positive_prompt(dna, style, view=view)
        neg = self._build_negative_prompt(dna)

        ref_filename = await self.comfyui.upload_image(
            reference_image_bytes, f"view_ref_{view}.png"
        )

        workflow_path = WORKFLOW_DIR / "character_view_ipadapter.json"
        with open(workflow_path) as f:
            workflow = json.load(f)

        overrides: dict[str, Any] = {
            "3": {"inputs": {"text": prompt}},
            "4": {"inputs": {"text": neg}},
            "7": {"inputs": {"image": ref_filename}},
            "8": {"inputs": {"weight": ipa_weight}},
            "9": {"inputs": {"denoise": denoise}},
        }
        return await self.comfyui.generate_with_workflow_dict(
            workflow=workflow, overrides=overrides, seed=seed,
        )

    async def generate_expression(
        self,
        dna: CharacterDNA,
        style: str,
        expression: str,
        front_view_bytes: bytes,
        denoise: float = 0.40,
    ) -> bytes:
        """Generate a face expression using IPAdapter from front view.

        expression: "neutral" | "angry" | "smile" | "battle"
        """
        view_key = f"face_{expression}"
        prompt = self._build_positive_prompt(dna, style, view=view_key)
        neg = self._build_negative_prompt(dna)

        ref_filename = await self.comfyui.upload_image(
            front_view_bytes, f"expr_ref_{expression}.png"
        )

        workflow_path = WORKFLOW_DIR / "character_view_ipadapter.json"
        with open(workflow_path) as f:
            workflow = json.load(f)

        # Expressions: higher IPA weight to lock identity, lower denoise
        ipa_weight = {"neutral": 0.90, "angry": 0.88, "smile": 0.88, "battle": 0.85}.get(expression, 0.85)

        overrides: dict[str, Any] = {
            "3": {"inputs": {"text": prompt}},
            "4": {"inputs": {"text": neg}},
            "7": {"inputs": {"image": ref_filename}},
            "8": {"inputs": {"weight": ipa_weight}},
            "9": {"inputs": {"denoise": denoise}},
        }
        return await self.comfyui.generate_with_workflow_dict(
            workflow=workflow, overrides=overrides,
        )

    async def generate_item(
        self,
        item_name: str,
        item_desc: str,
        style: str = "2d_chinese_donghua",
        seed: int | None = None,
    ) -> bytes:
        """Generate an isolated item (outfit piece / prop / weapon) on white bg.

        Returns PNG bytes.
        """
        style_prompt = self.dna_service.STYLE_PROMPTS.get(
            style, self.dna_service.STYLE_PROMPTS["2d_chinese_donghua"]
        )
        prompt = (
            f"{item_desc}, isolated clothing item, product design, "
            f"white background, concept art, orthographic view, "
            f"clean lines, detailed fabric texture, {style_prompt}, "
            f"masterpiece, high score, absurdres"
        )
        neg = "lowres, bad anatomy, text, error, cropped, worst quality, low quality, signature, watermark, blurry, person, mannequin, human"

        workflow_path = WORKFLOW_DIR / "item_gen.json"
        with open(workflow_path) as f:
            workflow = json.load(f)

        overrides: dict[str, Any] = {
            "3": {"inputs": {"text": prompt}},
            "4": {"inputs": {"text": neg}},
        }
        return await self.comfyui.generate_with_workflow_dict(
            workflow=workflow, overrides=overrides, seed=seed,
        )

    async def apply_face_restore(self, image_bytes: bytes) -> bytes:
        """Run GFPGAN face restoration on an image. Returns PNG bytes."""
        filename = await self.comfyui.upload_image(image_bytes, "face_restore_input.png")

        workflow_path = WORKFLOW_DIR / "face_restore.json"
        with open(workflow_path) as f:
            workflow = json.load(f)

        overrides: dict[str, Any] = {
            "1": {"inputs": {"image": filename}},
        }
        return await self.comfyui.generate_with_workflow_dict(workflow, overrides=overrides)

    def stitch_character_sheet(self, views: dict[str, bytes]) -> bytes:
        """Stitch multiple view images into a single horizontal preview sheet.

        views: {"front": bytes, "back": bytes, ...}
        Returns PNG bytes of stitched image (resized to uniform height, side-by-side).
        """
        try:
            from PIL import Image
        except ImportError:
            raise ImageGenError("Pillow is required for sheet stitching")

        images: list = []
        has_standard_views = any(k in views for k in ("front", "side", "back", "three_quarter"))
        if has_standard_views:
            for key in ("front", "side", "back", "three_quarter"):
                data = views.get(key)
                if data:
                    img = Image.open(io.BytesIO(data))
                    images.append(img)
        else:
            for key, data in views.items():
                if data:
                    img = Image.open(io.BytesIO(data))
                    images.append(img)

        if not images:
            raise ImageGenError("No images to stitch")

        # Resize all to same height
        target_h = min(img.height for img in images)
        resized = []
        for img in images:
            ratio = target_h / img.height
            new_w = int(img.width * ratio)
            resized.append(img.resize((new_w, target_h), Image.LANCZOS))

        # Concatenate horizontally with white gap
        gap = 16
        total_w = sum(r.width for r in resized) + gap * (len(resized) - 1)
        canvas = Image.new("RGB", (total_w, target_h), (255, 255, 255))
        x = 0
        for r in resized:
            canvas.paste(r, (x, 0))
            x += r.width + gap

        buf = io.BytesIO()
        canvas.save(buf, format="PNG")
        return buf.getvalue()

    # ──────────── Backward-compatible alias ────────────

    async def generate_character_portrait(
        self,
        dna: CharacterDNA,
        style: str = "2d_chinese_donghua",
        expression: str = "neutral",
        pose: str = "standing",
        view: str = "front",
        reference_image_path: str | None = None,
        seed: int | None = None,
        width: int = 832,
        height: int = 1216,
        steps: int = 25,
        cfg: float = 5.0,
    ) -> bytes:
        """Legacy method — delegates to new HiRes workflow for front,
        or IPAdapter workflow for side/back/3/4."""
        if reference_image_path:
            # Reference workflow already handles everything via ComfyUI filesystem
            prompt = self._build_positive_prompt(dna, style, view=view)
            neg = self._build_negative_prompt(dna)

            workflow_path = WORKFLOW_DIR / "character_view_ipadapter.json"
            with open(workflow_path) as f:
                workflow = json.load(f)

            overrides: dict[str, Any] = {
                "3": {"inputs": {"text": prompt}},
                "4": {"inputs": {"text": neg}},
                "7": {"inputs": {"image": reference_image_path}},
                "9": {"inputs": {"denoise": 0.45}},
            }
            return await self.comfyui.generate_with_workflow_dict(
                workflow=workflow, overrides=overrides, seed=seed,
                steps=steps, cfg=cfg,
            )

        return await self.generate_master_front_view(dna, style, seed=seed)

    async def generate_character_sheet(
        self,
        dna: CharacterDNA,
        style: str = "2d_chinese_donghua",
        views: list[str] | None = None,
        expression: str = "neutral",
    ) -> dict[str, bytes]:
        """Legacy alias — calls new generate_character_sheet pipeline
        but returns raw bytes without face restore / stitch."""
        return await self._generate_sheet_raw(dna, style, views)

    async def _generate_sheet_raw(
        self,
        dna: CharacterDNA,
        style: str,
        views: list[str] | None = None,
    ) -> dict[str, bytes]:
        """Generate multi-view sheet returning raw bytes (no face restore / stitch).

        Returns: {"front": bytes, "side": bytes, "back": bytes, "three_quarter": bytes}
        """
        if views is None:
            views = ["front", "side", "back", "three_quarter"]

        results: dict[str, bytes] = {}

        front_bytes = await self.generate_master_front_view(dna, style)
        results["front"] = front_bytes

        view_params = {
            "side": (0.85, 0.45),
            "back": (0.75, 0.50),
            "three_quarter": (0.85, 0.45),
        }
        for view in views:
            if view == "front":
                continue
            ipa_w, den = view_params.get(view, (0.85, 0.45))
            view_bytes = await self.generate_view_with_reference(
                dna, style, view=view,
                reference_image_bytes=front_bytes,
                ipa_weight=ipa_w, denoise=den,
            )
            results[view] = view_bytes

        return results
