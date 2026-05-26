# Module 3: Character System — Implementation Plan

## Overview

Module 3 là hệ thống quản lý nhân vật. Từ character data do Story Bible sinh ra, người dùng có thể xem, chỉnh sửa DNA nhân vật (visual descriptors), generate ảnh portrait qua ComfyUI, quản lý expression packs và pose variants, liên kết assets images vào character.

MVP: CRUD characters + ComfyUI T2I generate ảnh portrait + lưu vào assets + link về character.

---

## Step 3.1 — Character CRUD Router

**Goal:** REST endpoints cho character — list, create, get, update, delete.

**Files:**

```text
apps/api/app/routers/characters.py   # NEW
apps/api/app/main.py                 # MODIFY — register router
```

**Endpoints:**

```text
GET    /api/v1/projects/{id}/characters           # List characters in project
POST   /api/v1/projects/{id}/characters           # Create character manually
GET    /api/v1/characters/{id}                    # Get character detail
PATCH  /api/v1/characters/{id}                    # Update character DNA / metadata
DELETE /api/v1/characters/{id}                    # Delete character + cascade assets
```

**Business logic:**
- List: filter by project_id, optional role filter, sort by name
- Create: validate CharacterCreate schema, store character_json from CharacterDNA
- Get: return full CharacterRead with relationship to reference_asset
- Update: partial update CharacterDNA fields, merge into character_json
- Delete: cascade delete linked assets

**Tests:**
```text
apps/api/tests/test_characters.py   # CRUD endpoint tests
```

---

## Step 3.2 — Character DNA ↔ Visual Descriptor Normalization

**Goal:** Bridge the gap between LLM story `character_json` (free-form) và `CharacterDNA` (structured visual fields).

**Files:**

```text
apps/api/app/services/character_dna.py   # NEW
```

**Functions:**

```python
class CharacterDNAService:
    def extract_dna_from_story_json(self, character_json: dict) -> CharacterDNA
        """Extract structured DNA from LLM-generated character data"""
    
    def merge_dna_into_json(self, existing_json: dict, dna: CharacterDNA) -> dict
        """Merge structured DNA fields back into character_json blob"""
    
    def generate_image_prompt(self, dna: CharacterDNA, style: str) -> str
        """Generate ComfyUI-ready text prompt from CharacterDNA fields"""
```

**Mapping logic:**
- `appearance`, `personality`, `visual_cues` từ story Json → extract màu tóc, mắt, trang phục etc.
- Nếu LLM cung cấp `age`, `gender`, `hair_color` etc. → map trực tiếp
- Còn thiếu → default reasonable values theo style

---

## Step 3.3 — ComfyUI Client

**Goal:** Python client để gọi ComfyUI API (queue prompt, poll status, download output).

**Files:**

```text
apps/api/app/services/comfyui/
├── __init__.py
├── client.py          # Low-level HTTP client to ComfyUI
├── workflows/
│   └── character_portrait.json   # Default T2I workflow
└── types.py           # TypedDicts for ComfyUI API responses
```

**Client interface:**

```python
class ComfyUIClient:
    def __init__(self, base_url: str, timeout: int = 120)
    async def queue_prompt(self, workflow: dict) -> str        # returns prompt_id
    async def get_history(self, prompt_id: str) -> dict        # poll result
    async def wait_for_result(self, prompt_id: str, poll_interval: float = 2.0) -> dict
    async def generate_image(self, prompt: str, negative_prompt: str = "",
                              width: int = 512, height: int = 768,
                              seed: int | None = None, steps: int = 20,
                              cfg: float = 7.0) -> bytes      # returns PNG bytes
```

**Config mở rộng:**

```python
# apps/api/app/config.py — thêm
comfyui_base_url: str = "http://localhost:8188"
comfyui_timeout: int = 300
comfyui_default_checkpoint: str = "meinamix_meinaV11.safetensors"
```

**Workflow file** — `character_portrait.json`:
- Load checkpoint → CLIP Text Encode (positive + negative) → Empty Latent → KSampler → VAE Decode → Save Image
- Placeholder tokens: `{{positive_prompt}}`, `{{negative_prompt}}`, `{{width}}`, `{{height}}`, `{{seed}}`, `{{steps}}`, `{{cfg}}`, `{{checkpoint}}`

---

## Step 3.4 — Character Image Generation Endpoint

**Goal:** `POST /characters/{id}/generate-image` — tạo ảnh portrait từ CharacterDNA.

**Files:**

```text
apps/api/app/routers/characters.py   # MODIFY — add endpoint
apps/api/app/services/image_gen.py   # NEW
```

**Endpoint:**

```text
POST /api/v1/characters/{id}/generate-image
  Body: {
    "expression": "neutral",       # neutral | happy | angry | sad | surprised
    "pose": "standing",            # standing | action | sitting
    "variant_name": "default",     # label for this generation
    "seed": null,                  # optional fixed seed
    "width": 512,
    "height": 768,
    "steps": 20,
    "cfg": 7.0
  }
  Response: {
    "data": {
      "asset_id": "uuid",
      "image_url": "/storage/...",
      "expression": "neutral",
      "pose": "standing",
      "variant_name": "default"
    }
  }
```

**Pipeline:**

```text
character_id
  → load CharacterDNA
    → ImageGenService.generate_portrait(dna, params)
      → CharacterDNAService.generate_image_prompt(dna, style)
        → ComfyUIClient.generate_image(prompt)
          → StorageService.save(character_id, image_bytes, variant_name)
            → AssetModel.create(type=CHARACTER)
              → CharacterModel.reference_asset_id = asset.id
```

**Tests:**

```text
apps/api/tests/test_image_gen.py   # mock ComfyUI, test prompt generation + storage
```

---

## Step 3.5 — Asset Router

**Goal:** CRUD + serve static image files linked to characters.

**Files:**

```text
apps/api/app/routers/assets.py   # NEW
apps/api/app/main.py             # MODIFY — register router + static mount
```

**Endpoints:**

```text
GET    /api/v1/assets/{id}                          # Asset metadata
DELETE /api/v1/assets/{id}                          # Delete asset + file
GET    /api/v1/assets/{id}/download                 # Serve raw file
GET    /api/v1/characters/{id}/assets               # List all assets for character
```

**Static serving:**
- Mount `storage/` directory at `/storage/`
- Asset metadata JSONB tracks generation params (prompt, seed, steps, checkpoint)

---

## Step 3.6 — Expression & Variant Management

**Goal:** Quản lý expression packs + pose variants cho mỗi character.

**No new DB table needed** — dùng `AssetModel.metadata_json` để tag expression/pose/variant info.

**Asset metadata structure:**

```python
class CharacterAssetMetadata(AssetMetadata):
    character_id: UUID
    expression: str          # neutral, happy, angry, sad, surprised, custom
    pose: str                # standing, action, sitting, portrait, full_body
    variant_name: str        # default, alt_outfit, powered_up, etc.
    generation_params: dict  # prompt, negative_prompt, seed, steps, cfg, checkpoint
    is_primary: bool         # default portrait for character
```

**Endpoints:**

```text
POST /api/v1/characters/{id}/generate-expression
  Body: { "expression": "happy", "intensity": 0.8 }
  → generates portrait with modified expression prompt

POST /api/v1/characters/{id}/set-primary-asset
  Body: { "asset_id": "uuid" }
  → sets this asset as character.primary portrait
```

---

## Step 3.7 — Tests

**Files:**

```text
apps/api/tests/test_characters.py     # CRUD + DNA validation
apps/api/tests/test_assets.py         # Asset CRUD + download
apps/api/tests/test_image_gen.py      # Image generation pipeline (mocked ComfyUI)
apps/api/tests/test_comfyui.py        # ComfyUI client unit tests
```

**Test cases:**
- Character CRUD: create, list by project, get detail, update DNA, delete
- Character DNA: extract/merge, prompt generation quality
- Asset CRUD: upload/download, metadata, character-asset linking
- Image Gen: full pipeline mock (DNA → prompt → ComfyUI → save → link)
- ComfyUI client: queue, poll, download (with httpx mock)
- Edge cases: character not found, ComfyUI timeout, invalid workflow

---

## Execution Order

```text
3.1 → 3.2 → 3.3 → 3.4 → 3.5 → 3.6 → 3.7
(Character CRUD → DNA normalization → ComfyUI client → Image gen → Assets → Expressions → Tests)
```

---

## New Files Summary

```text
apps/api/app/routers/characters.py                  # NEW
apps/api/app/routers/assets.py                      # NEW
apps/api/app/services/character_dna.py              # NEW
apps/api/app/services/image_gen.py                  # NEW
apps/api/app/services/comfyui/
├── __init__.py                                     # NEW
├── client.py                                       # NEW
├── types.py                                        # NEW
└── workflows/
    └── character_portrait.json                     # NEW
apps/api/app/main.py                                # MODIFY — register routers + static mount
apps/api/app/config.py                              # MODIFY — ComfyUI settings
apps/api/tests/
├── test_characters.py                              # NEW
├── test_assets.py                                  # NEW
├── test_image_gen.py                               # NEW
└── test_comfyui.py                                 # NEW
```

---

## Deliverables Checkpoint

```text
☑ Character CRUD API (list, create, get, update, delete) — 9 tests
☑ CharacterDNA normalization service (extract, merge, prompt gen)
☑ ComfyUI client (queue, poll, download) — 5 tests
☑ Character portrait generation endpoint
☑ Asset CRUD + static file serving — 6 tests
☑ Expression packs & variant management (generate-expression, set-primary-asset)
☑ Full test coverage — 26 tests passing (9 char CRUD + 6 asset + 5 comfyui + 6 image_gen)
```

---

## Next: Module 4 — Scene & Shot Builder

Timeline-based scene/shots editor, keyframe workflow, continuity tracking, camera/motion/animation timing.
