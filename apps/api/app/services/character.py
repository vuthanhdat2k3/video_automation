from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_2d_shared.character import CharacterDNA, CharacterRead, CharacterUpdate

from app.exceptions import NotFoundException
from app.models.character import CharacterModel
from app.models.project import ProjectModel
from app.models.asset import AssetModel
from app.services.asset_utils import save_generated_asset
from app.services.image_gen import ImageGenService
from app.services.llm.base import LLMProvider
from app.services.story import create_llm_provider, create_translation_llm_provider
from app.services.prompts.compiler import PromptCompiler
from app.services.character_dna import CharacterDNAService
from app.services.storage import StorageManager
from app.config import settings


class CharacterService:
    def __init__(self, db: AsyncSession, image_gen: ImageGenService | None = None):
        self.db = db
        self.llm = create_llm_provider()
        self.translation_llm = create_translation_llm_provider()
        self.compiler = PromptCompiler()
        self.dna_service = CharacterDNAService()
        self.image_gen = image_gen or ImageGenService()

    async def list_by_project(self, project_id: UUID) -> list[CharacterRead]:
        result = await self.db.execute(
            select(CharacterModel)
            .where(CharacterModel.project_id == project_id)
            .order_by(CharacterModel.name)
        )
        return [CharacterRead.model_validate(c) for c in result.scalars().all()]

    async def create(self, project_id: UUID, data) -> CharacterRead:
        dna = data.character_dna or CharacterDNA()
        character = CharacterModel(
            project_id=project_id,
            name=data.name,
            role=data.role,
            character_json=dna.model_dump(),
        )
        self.db.add(character)
        await self.db.commit()
        await self.db.refresh(character)
        return CharacterRead.model_validate(character)

    async def get(self, character_id: UUID) -> CharacterRead:
        character = await self._get_or_404(character_id)
        return CharacterRead.model_validate(character)

    async def update(self, character_id: UUID, data: CharacterUpdate) -> CharacterRead:
        character = await self._get_or_404(character_id)
        if data.name is not None:
            character.name = data.name
        if data.role is not None:
            character.role = data.role
        if data.reference_asset_id is not None:
            character.reference_asset_id = data.reference_asset_id

        existing = dict(character.character_json or {})

        if data.description is not None:
            existing["description"] = data.description
            if data.description.strip():
                system_prompt = "You are a precise character metadata extraction assistant. Output ONLY valid JSON."
                prompt = self.compiler.compile("CHARACTER_DNA_EXTRACT_PROMPT", description=data.description)
                extracted_dna_dict = None
                try:
                    extracted_dna_dict = await self.translation_llm.generate(system_prompt, prompt, CharacterDNA)
                except Exception as e:
                    print(f"Translation LLM failed (OpenRouter 429/404), falling back to main LLM: {e}")
                    try:
                        extracted_dna_dict = await self.llm.generate(system_prompt, prompt, CharacterDNA)
                    except Exception as e2:
                        print(f"Main LLM also failed: {e2}")

                if extracted_dna_dict:
                    dna_obj = CharacterDNA(**extracted_dna_dict)
                    existing.update(dna_obj.model_dump(exclude_unset=True))

                    project_res = await self.db.execute(
                        select(ProjectModel).where(ProjectModel.id == character.project_id)
                    )
                    project = project_res.scalar_one_or_none()
                    style = project.style if project else "2d_chinese_donghua"

                    img_prompt = self.dna_service.generate_image_prompt(dna_obj, style)
                    existing["prompt"] = img_prompt

        if data.character_dna is not None:
            existing.update(data.character_dna.model_dump(exclude_unset=True))

        character.character_json = existing
        await self.db.commit()
        await self.db.refresh(character)
        return CharacterRead.model_validate(character)

    async def delete(self, character_id: UUID) -> None:
        character = await self._get_or_404(character_id)
        await self.db.delete(character)
        await self.db.commit()

    # ──────────── Helper: delete old assets ────────────

    async def _delete_old_assets(self, project_id: UUID, character_id: UUID, asset_type: str) -> None:
        storage = StorageManager(settings.storage_root)
        old = await self.db.execute(
            select(AssetModel)
            .where(AssetModel.project_id == project_id)
            .where(AssetModel.type == asset_type)
            .where(AssetModel.metadata_json.op("->>")("character_id") == str(character_id))
        )
        for old_asset in old.scalars().all():
            try:
                storage.delete_asset(old_asset.project_id, old_asset.path)
            except Exception as e:
                print(f"Failed to delete old asset {old_asset.path}: {e}")
            await self.db.delete(old_asset)
        await self.db.flush()

    # ──────────── Generate Character Sheet ────────────

    async def generate_character_sheet(self, character_id: UUID) -> dict[str, str]:
        """Generate multi-view character sheet with HiRes + IPAdapter + face restore.

        Returns: {"front": asset_id, "side": ..., "back": ...,
                   "three_quarter": ..., "preview": asset_id}
        """
        character = await self._get_or_404(character_id)
        dna = character.character_dna
        project_res = await self.db.execute(
            select(ProjectModel).where(ProjectModel.id == character.project_id)
        )
        project = project_res.scalar_one_or_none()
        style = project.style if project else "2d_chinese_donghua"

        # Step 1: Generate master front (HiRes Fix)
        front_bytes = await self.image_gen.generate_master_front_view(dna, style)

        # Step 2: Generate side/back/3/4 with IPAdapter
        view_params = {
            "side": (0.85, 0.45),
            "back": (0.75, 0.50),
            "three_quarter": (0.85, 0.45),
        }
        raw_views: dict[str, bytes] = {"front": front_bytes}
        for view, (ipa_w, den) in view_params.items():
            view_bytes = await self.image_gen.generate_view_with_reference(
                dna, style, view=view,
                reference_image_bytes=front_bytes,
                ipa_weight=ipa_w, denoise=den,
            )
            raw_views[view] = view_bytes

        # Step 3: GFPGAN face restore on front/side/3q4
        for face_view in ("front", "side", "three_quarter"):
            if face_view in raw_views:
                try:
                    raw_views[face_view] = await self.image_gen.apply_face_restore(raw_views[face_view])
                except Exception as e:
                    print(f"Face restore failed for {face_view}: {e}")

        # Step 4: Stitch preview
        try:
            preview_bytes = self.image_gen.stitch_character_sheet(raw_views)
        except Exception as e:
            print(f"Stitching failed: {e}")
            preview_bytes = None

        # Step 5: Delete old + save new assets
        await self._delete_old_assets(character.project_id, character_id, "character_reference")
        await self._delete_old_assets(character.project_id, character_id, "character_sheet_preview")

        import uuid as _uuid
        run_id = _uuid.uuid4().hex[:8]

        view_assets: dict[str, str] = {}
        for name, img_bytes in raw_views.items():
            safe_fn = f"{character_id}/char_{character_id}_{name}_{run_id}.png"
            asset = await save_generated_asset(
                db=self.db,
                project_id=character.project_id,
                asset_type="character_reference",
                filename=safe_fn,
                data=img_bytes,
                metadata={
                    "character_id": str(character_id),
                    "view": name,
                    "source": "character_sheet",
                    "run_id": run_id,
                },
            )
            view_assets[name] = str(asset.id)

        if preview_bytes:
            preview_fn = f"{character_id}/char_{character_id}_sheet_preview_{run_id}.png"
            preview_asset = await save_generated_asset(
                db=self.db,
                project_id=character.project_id,
                asset_type="character_sheet_preview",
                filename=preview_fn,
                data=preview_bytes,
                metadata={"character_id": str(character_id), "source": "character_sheet"},
            )
            view_assets["preview"] = str(preview_asset.id)

        existing = dict(character.character_json or {})
        existing["view_assets"] = view_assets
        character.character_json = existing
        if "front" in view_assets:
            character.reference_asset_id = UUID(view_assets["front"])
        await self.db.commit()

        return view_assets

    # ──────────── Generate Outfit Sheet ────────────

    async def generate_outfit_sheet(self, character_id: UUID) -> dict[str, str]:
        """Generate individual outfit item images.

        Returns: {"upper_body": asset_id, "lower_body": ..., "preview": asset_id}
        """
        character = await self._get_or_404(character_id)
        dna = character.character_dna
        project_res = await self.db.execute(
            select(ProjectModel).where(ProjectModel.id == character.project_id)
        )
        project = project_res.scalar_one_or_none()
        style = project.style if project else "2d_chinese_donghua"

        items = self.dna_service.extract_outfit_items(dna)
        if not items:
            return {}

        await self._delete_old_assets(character.project_id, character_id, "outfit_reference")
        await self._delete_old_assets(character.project_id, character_id, "outfit_sheet_preview")

        import uuid as _uuid
        run_id = _uuid.uuid4().hex[:8]

        outfit_assets: dict[str, str] = {}
        raw_items: dict[str, bytes] = {}
        for item in items:
            try:
                img_bytes = await self.image_gen.generate_item(
                    item_name=item["name"],
                    item_desc=item["desc"],
                    style=style,
                )
                raw_items[item["name"]] = img_bytes
                safe_fn = f"{character_id}/outfit_{character_id}_{item['name']}_{run_id}.png"
                asset = await save_generated_asset(
                    db=self.db,
                    project_id=character.project_id,
                    asset_type="outfit_reference",
                    filename=safe_fn,
                    data=img_bytes,
                    metadata={
                        "character_id": str(character_id),
                        "item": item["name"],
                        "source": "outfit_sheet",
                    },
                )
                outfit_assets[item["name"]] = str(asset.id)
            except Exception as e:
                print(f"Outfit item '{item['name']}' failed: {e}")

        if raw_items:
            try:
                preview_bytes = self.image_gen.stitch_character_sheet(raw_items)
                preview_fn = f"{character_id}/outfit_{character_id}_sheet_preview_{run_id}.png"
                preview_asset = await save_generated_asset(
                    db=self.db,
                    project_id=character.project_id,
                    asset_type="outfit_sheet_preview",
                    filename=preview_fn,
                    data=preview_bytes,
                    metadata={"character_id": str(character_id), "source": "outfit_sheet"},
                )
                outfit_assets["preview"] = str(preview_asset.id)
            except Exception as e:
                print(f"Outfit stitch failed: {e}")

        existing = dict(character.character_json or {})
        existing["outfit_assets"] = outfit_assets
        character.character_json = existing
        await self.db.commit()

        return outfit_assets

    # ──────────── Generate Asset/Prop Sheet ────────────

    async def generate_asset_sheet(self, character_id: UUID) -> dict[str, str]:
        """Generate individual prop/weapon images.

        Returns: {"sword": asset_id, "preview": asset_id}
        """
        character = await self._get_or_404(character_id)
        dna = character.character_dna
        project_res = await self.db.execute(
            select(ProjectModel).where(ProjectModel.id == character.project_id)
        )
        project = project_res.scalar_one_or_none()
        style = project.style if project else "2d_chinese_donghua"

        items = self.dna_service.extract_asset_items(dna)
        if not items:
            return {}

        await self._delete_old_assets(character.project_id, character_id, "prop_reference")
        await self._delete_old_assets(character.project_id, character_id, "prop_sheet_preview")

        import uuid as _uuid
        run_id = _uuid.uuid4().hex[:8]

        prop_assets: dict[str, str] = {}
        raw_items: dict[str, bytes] = {}
        for item in items:
            try:
                img_bytes = await self.image_gen.generate_item(
                    item_name=item["name"],
                    item_desc=item["desc"],
                    style=style,
                )
                raw_items[item["name"]] = img_bytes
                safe_fn = f"{character_id}/prop_{character_id}_{item['name']}_{run_id}.png"
                asset = await save_generated_asset(
                    db=self.db,
                    project_id=character.project_id,
                    asset_type="prop_reference",
                    filename=safe_fn,
                    data=img_bytes,
                    metadata={
                        "character_id": str(character_id),
                        "item": item["name"],
                        "source": "prop_sheet",
                    },
                )
                prop_assets[item["name"]] = str(asset.id)
            except Exception as e:
                print(f"Prop item '{item['name']}' failed: {e}")

        if raw_items:
            try:
                preview_bytes = self.image_gen.stitch_character_sheet(raw_items)
                preview_fn = f"{character_id}/prop_{character_id}_sheet_preview_{run_id}.png"
                preview_asset = await save_generated_asset(
                    db=self.db,
                    project_id=character.project_id,
                    asset_type="prop_sheet_preview",
                    filename=preview_fn,
                    data=preview_bytes,
                    metadata={"character_id": str(character_id), "source": "prop_sheet"},
                )
                prop_assets["preview"] = str(preview_asset.id)
            except Exception as e:
                print(f"Prop stitch failed: {e}")

        existing = dict(character.character_json or {})
        existing["prop_assets"] = prop_assets
        character.character_json = existing
        await self.db.commit()

        return prop_assets

    # ──────────── Generate Expression Sheet ────────────

    async def generate_expression_sheet(
        self,
        character_id: UUID,
        expressions: list[str] | None = None,
    ) -> dict[str, str]:
        """Generate face expression images from front view using IPAdapter.

        Returns: {"neutral": asset_id, "angry": ..., "smile": ...,
                   "battle": ..., "preview": asset_id}
        """
        if expressions is None:
            expressions = ["neutral", "angry", "smile", "battle"]

        character = await self._get_or_404(character_id)
        dna = character.character_dna
        project_res = await self.db.execute(
            select(ProjectModel).where(ProjectModel.id == character.project_id)
        )
        project = project_res.scalar_one_or_none()
        style = project.style if project else "2d_chinese_donghua"

        # Get front view bytes from view_assets
        view_assets = (character.character_json or {}).get("view_assets", {})
        front_asset_id = view_assets.get("front")
        if not front_asset_id:
            raise NotFoundException("No front view available. Generate character sheet first.")

        asset_res = await self.db.execute(
            select(AssetModel).where(AssetModel.id == UUID(front_asset_id))
        )
        front_asset = asset_res.scalar_one_or_none()
        if not front_asset:
            raise NotFoundException("Front view asset not found in storage.")

        storage = StorageManager(settings.storage_root)
        front_path = storage.get_asset_path(character.project_id, front_asset.path)
        if not front_path.exists():
            raise NotFoundException("Front view file not found on disk.")
        front_bytes = front_path.read_bytes()

        await self._delete_old_assets(character.project_id, character_id, "expression_reference")
        await self._delete_old_assets(character.project_id, character_id, "expression_sheet_preview")

        import uuid as _uuid
        run_id = _uuid.uuid4().hex[:8]

        expr_assets: dict[str, str] = {}
        raw_expr: dict[str, bytes] = {}
        for expr in expressions:
            try:
                denoise = {"neutral": 0.35, "angry": 0.38, "smile": 0.38, "battle": 0.40}.get(expr, 0.38)
                img_bytes = await self.image_gen.generate_expression(
                    dna, style, expression=expr,
                    front_view_bytes=front_bytes,
                    denoise=denoise,
                )
                # Face restore on each expression
                try:
                    img_bytes = await self.image_gen.apply_face_restore(img_bytes)
                except Exception as e:
                    print(f"Face restore failed for expr '{expr}': {e}")

                raw_expr[expr] = img_bytes
                safe_fn = f"{character_id}/expr_{character_id}_{expr}_{run_id}.png"
                asset = await save_generated_asset(
                    db=self.db,
                    project_id=character.project_id,
                    asset_type="expression_reference",
                    filename=safe_fn,
                    data=img_bytes,
                    metadata={
                        "character_id": str(character_id),
                        "expression": expr,
                        "source": "expression_sheet",
                    },
                )
                expr_assets[expr] = str(asset.id)
            except Exception as e:
                print(f"Expression '{expr}' failed: {e}")

        if raw_expr:
            try:
                preview_bytes = self.image_gen.stitch_character_sheet(raw_expr)
                preview_fn = f"{character_id}/expr_{character_id}_sheet_preview_{run_id}.png"
                preview_asset = await save_generated_asset(
                    db=self.db,
                    project_id=character.project_id,
                    asset_type="expression_sheet_preview",
                    filename=preview_fn,
                    data=preview_bytes,
                    metadata={"character_id": str(character_id), "source": "expression_sheet"},
                )
                expr_assets["preview"] = str(preview_asset.id)
            except Exception as e:
                print(f"Expression stitch failed: {e}")

        existing = dict(character.character_json or {})
        existing["expression_assets"] = expr_assets
        character.character_json = existing
        await self.db.commit()

        return expr_assets

    # ──────────── Full Reference Orchestrator ────────────

    async def generate_full_reference(
        self,
        character_id: UUID,
        skip_phases: list[str] | None = None,
    ) -> dict:
        """Orchestrate full character reference generation.

        Order:
        1. character_sheet (must complete first)
        2. outfit_sheet (parallel with 3)
        3. asset_sheet (parallel with 2)
        4. expression_sheet (needs front view from step 1)

        skip_phases: ["outfit", "asset", "expression"] to skip specific phases
        """
        if skip_phases is None:
            skip_phases = []

        result: dict = {}

        # Phase 1: Character sheet (views + preview)
        result["character_sheet"] = await self.generate_character_sheet(character_id)

        # Phase 2 + 3: Outfit + Assets (parallel)
        import asyncio
        tasks = []
        if "outfit" not in skip_phases:
            tasks.append(("outfit", self.generate_outfit_sheet(character_id)))
        if "asset" not in skip_phases:
            tasks.append(("asset", self.generate_asset_sheet(character_id)))

        if tasks:
            done = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
            for (name, _), outcome in zip(tasks, done):
                if isinstance(outcome, Exception):
                    print(f"Phase '{name}' failed: {outcome}")
                    result[name] = {"error": str(outcome)}
                else:
                    result[name] = outcome

        # Phase 4: Expression sheet (needs front view from phase 1)
        if "expression" not in skip_phases:
            try:
                result["expression"] = await self.generate_expression_sheet(character_id)
            except Exception as e:
                print(f"Expression phase failed: {e}")
                result["expression"] = {"error": str(e)}

        return result

    # ──────────── Backward compat ────────────

    async def generate_reference_sheet(self, character_id: UUID) -> dict[str, str]:
        """Legacy alias for generate_character_sheet."""
        return await self.generate_character_sheet(character_id)

    async def _get_or_404(self, character_id: UUID) -> CharacterModel:
        result = await self.db.execute(
            select(CharacterModel).where(CharacterModel.id == character_id)
        )
        character = result.scalar_one_or_none()
        if not character:
            raise NotFoundException(f"Character {character_id} not found")
        return character
