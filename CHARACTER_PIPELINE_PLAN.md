# CHARACTER REFERENCE PIPELINE — Implementation Plan

## Strategy: Hybrid "Master + Reference-Driven" Pipeline

```
[STEP 1] txt2img → master_front.png (1024×1536, full quality)
              ↓
[STEP 2] IPAdapter(master_front) → side.png   (denoise 0.45, ipa_weight 0.85)
         IPAdapter(master_front) → back.png   (denoise 0.50, ipa_weight 0.75)
         IPAdapter(master_front) → 3q4.png    (denoise 0.45, ipa_weight 0.85)
              ↓
[STEP 3] HiRes Fix (latent upscale ×1.5, denoise 0.35) → each view
              ↓
[STEP 4] GFPGAN face restore → front / side / 3q4
              ↓
[STEP 5] PIL stitch 4 views → character_sheet_preview.png
              ↓
[STEP 6] IPAdapter(master_front) → neutral / angry / smile / battle (×4 requests)
              ↓
[STEP 7] txt2img per outfit item + txt2img per asset
```

---

## Core Design Decisions

| Vấn đề | Quyết định |
|---|---|
| 1 canvas vs nhiều ảnh | **Hybrid**: master front = txt2img; side/back/3-4 = IPAdapter-driven img2img |
| Giữ identity | IPAdapter weight 0.75–0.85, denoise thấp (0.35–0.50), same prompt seed |
| Độ nét mặt | HiRes Fix (latent upscale → low-denoise pass) + GFPGAN v1.4 sau crop |
| Outfit | Từng item riêng (robe_front, boots, belt...) + 1 preview sheet ghép |
| Expression | IPAdapter từ front view, 1 request / expression, denoise thấp 0.35–0.45 |
| Back view | Không enforce mặt, tập trung hair/outfit/silhouette consistency |

---

## Phase 1 — Core Infrastructure (Priority: CRITICAL)

### 1.1 Workflows ComfyUI Mới / Sửa

#### `workflows/character_view_ipadapter.json` [NEW]
Workflow sinh 1 view đơn dùng IPAdapter:
- Node: CheckpointLoaderSimple
- Node: IPAdapterModelLoader (ip-adapter-plus_sdxl_vit-h.safetensors)
- Node: CLIPVisionLoader (clip_vision_h.safetensors)
- Node: LoadImage (reference image — front view)
- Node: IPAdapterAdvanced (weight=0.85, weight_type="linear", start=0, end=1)
- Node: EmptyLatentImage (1024×1536)
- Node: KSampler (steps=30, cfg=5.0, denoise=1.0)
- **Node: LatentUpscaleBy (×1.5) → KSampler hires (steps=15, denoise=0.35)**
- Node: VAEDecode
- Node: SaveImage

#### `workflows/character_portrait_hires.json` [NEW]
Workflow sinh master front view (txt2img thuần + hires fix):
- Giống character_portrait.json nhưng thêm HiRes Fix pass
- Resolution: 1024×1536 → latent ×1.5 → HiRes KSampler (denoise=0.35)
- Steps: 30 cho base, 15 cho hires
- Output: ~1536×2304 trước khi VAEDecode (crop/resize nếu cần)

#### `workflows/face_restore.json` [NEW]
Workflow restore khuôn mặt dùng GFPGAN:
- Node: LoadImage
- Node: GFPGANModelLoader (GFPGANv1.4.pth)
- Node: FaceRestoreWithModel
- Node: SaveImage

#### `workflows/outfit_item.json` [NEW]
Workflow sinh 1 outfit item (áo/boots/belt/...) trên white background:
- Resolution: 768×768 (square, clean)
- Prompt: "{item}, isolated clothing item, product design, white background, concept art,
           orthographic view, clean lines, detailed fabric texture, masterpiece, absurdres"
- Steps: 25, cfg: 5.0

#### `workflows/asset_item.json` [NEW]
Workflow sinh 1 prop/weapon trên white background:
- Resolution: 768×768
- Prompt: "{asset}, isolated item, white background, fantasy concept art,
           orthographic projection, front view, detailed, sharp, masterpiece"

### 1.2 Service: `image_gen.py` [MODIFY]

Thêm các methods:

```python
async def generate_master_front_view(
    self, dna: CharacterDNA, style: str, seed: int | None = None
) -> bytes:
    """Sinh master front view chất lượng cao (txt2img + HiRes Fix).
    Đây là ảnh gốc, được dùng làm reference cho tất cả views còn lại."""

async def generate_view_with_reference(
    self,
    dna: CharacterDNA,
    style: str,
    view: str,                    # "side" | "back" | "three_quarter"
    reference_image_bytes: bytes, # master front view
    ipa_weight: float = 0.85,
    denoise: float = 0.45,
    seed: int | None = None,
) -> bytes:
    """Sinh 1 view nhân vật dùng IPAdapter từ master front view.
    Mỗi view có ipa_weight và denoise riêng tối ưu."""

async def generate_expression(
    self,
    dna: CharacterDNA,
    style: str,
    expression: str,              # "neutral" | "angry" | "smile" | "battle"
    front_view_bytes: bytes,      # master front view
    denoise: float = 0.40,
) -> bytes:
    """Sinh 1 biểu cảm khuôn mặt dùng IPAdapter từ front view."""

async def generate_outfit_item(
    self, item_name: str, item_desc: str, style: str
) -> bytes:
    """Sinh ảnh 1 outfit item riêng lẻ trên white background."""

async def generate_asset_item(
    self, asset_name: str, asset_desc: str, style: str
) -> bytes:
    """Sinh ảnh 1 prop/weapon riêng lẻ trên white background."""

async def apply_face_restore(self, image_bytes: bytes) -> bytes:
    """Chạy GFPGAN face restoration qua ComfyUI."""

def stitch_character_sheet(
    self, views: dict[str, bytes]
) -> bytes:
    """Ghép 4 views thành 1 ảnh preview ngang bằng PIL."""
```

### 1.3 Service: `character_dna.py` [MODIFY]

Thêm VIEW_TAGS chi tiết cho từng view riêng lẻ:

```python
VIEW_TAGS = {
    "front": (
        "full body front view, facing viewer, neutral pose, "
        "feet visible, hands relaxed at sides, white background, flat lighting"
    ),
    "side": (
        "full body side profile view, facing right, full body visible, "
        "white background, flat lighting, same outfit"
    ),
    "back": (
        "full body back view, facing away from viewer, "
        "white background, same hair back detail, same outfit back design"
    ),
    "three_quarter": (
        "full body three-quarter view, slight angle left, "
        "face partially visible, white background, same outfit"
    ),
    # Expression views — bust shot only
    "face_neutral": "bust portrait, calm expression, looking at viewer, white background",
    "face_angry":   "bust portrait, angry expression, furrowed brows, fierce eyes, white background",
    "face_smile":   "bust portrait, warm smile, happy expression, white background",
    "face_battle":  "bust portrait, battle-ready face, determined gaze, intense eyes, white background",
}
```

Thêm method để extract outfit items và assets từ DNA:

```python
def extract_outfit_items(self, dna: CharacterDNA) -> list[dict]:
    """Trả về [{name: str, desc: str}] các outfit items cần gen riêng."""

def extract_asset_items(self, dna: CharacterDNA) -> list[dict]:
    """Trả về [{name: str, desc: str}] các props/weapons cần gen riêng."""
```

### 1.4 Service: `character.py` [MODIFY]

```python
async def generate_character_sheet(self, character_id: UUID) -> dict[str, str]:
    """
    Pipeline chính:
    1. Gen master front view (txt2img + HiRes)
    2. Upload front → lấy path để dùng làm IPAdapter reference
    3. Gen side (ipa 0.85, denoise 0.45)
    4. Gen back (ipa 0.75, denoise 0.50)
    5. Gen three_quarter (ipa 0.85, denoise 0.45)
    6. GFPGAN restore front/side/3q4
    7. Stitch preview sheet
    8. Xóa old assets, save tất cả vào DB
    Returns: {"front": asset_id, "side": ..., "back": ..., "three_quarter": ..., "preview": ...}
    """

async def generate_outfit_sheet(self, character_id: UUID) -> dict[str, str]:
    """
    1. Extract outfit items từ DNA
    2. Gen từng item riêng (parallel nếu có thể)
    3. Stitch preview ngang
    4. Save all to DB
    Returns: {"robe_front": asset_id, "boots": ..., "preview": ...}
    """

async def generate_asset_sheet(self, character_id: UUID) -> dict[str, str]:
    """
    1. Extract assets (weapons, accessories) từ DNA
    2. Gen từng asset riêng
    3. Stitch preview ngang
    4. Save all to DB
    Returns: {"sword": asset_id, "pendant": ..., "preview": ...}
    """

async def generate_expression_sheet(self, character_id: UUID) -> dict[str, str]:
    """
    1. Lấy front view từ character_json["view_assets"]["front"]
    2. Download front view bytes từ S3/local
    3. Gen 4 expressions tuần tự với IPAdapter
    4. GFPGAN restore từng expression
    5. Stitch preview ngang
    6. Save all to DB
    Returns: {"neutral": asset_id, "angry": ..., "smile": ..., "battle": ..., "preview": ...}
    """

async def generate_full_reference(self, character_id: UUID) -> dict:
    """
    Orchestrator gọi theo thứ tự:
    1. generate_character_sheet   ← PHẢI xong trước
    2. generate_outfit_sheet      ← có thể parallel với 3
    3. generate_asset_sheet       ← có thể parallel với 2
    4. generate_expression_sheet  ← PHẢI sau 1 vì cần front view
    Returns: {character_sheet: {...}, outfit: {...}, assets: {...}, expressions: {...}}
    """
```

---

## Phase 2 — API Endpoints [MODIFY `routers/characters.py`]

```python
POST /characters/{id}/generate-character-sheet
# → Sinh master front + 3 views (IPAdapter) + preview sheet
# Response: {"data": {"front": uuid, "side": uuid, "back": uuid, "three_quarter": uuid, "preview": uuid}}

POST /characters/{id}/generate-outfit-sheet
# → Sinh từng outfit item + preview
# Response: {"data": {"robe": uuid, "boots": uuid, ..., "preview": uuid}}

POST /characters/{id}/generate-asset-sheet
# → Sinh từng weapon/prop + preview
# Response: {"data": {"sword": uuid, "pendant": uuid, ..., "preview": uuid}}

POST /characters/{id}/generate-expression-sheet
# → Sinh 4 expressions dùng IPAdapter
# Body có thể chứa: {"expressions": ["neutral", "angry", "smile", "battle"]}
# Response: {"data": {"neutral": uuid, "angry": uuid, "smile": uuid, "battle": uuid, "preview": uuid}}

POST /characters/{id}/generate-full-reference
# → Gọi tuần tự 4 endpoint trên
# Body: {"skip_phases": []}  # có thể bỏ qua phase nào đó nếu đã có
# Response: {"data": {character_sheet: {...}, outfit: {...}, assets: {...}, expressions: {...}}}
```

---

## Phase 3 — DB Structure (No Migration Needed)

### Asset Types (bảng `assets.type`)

| type value | Nội dung |
|---|---|
| `character_reference` | 4 views nhân vật (front/side/back/3-4) |
| `character_sheet_preview` | Ảnh preview ghép 4 views |
| `outfit_reference` | Từng outfit item riêng |
| `outfit_sheet_preview` | Ảnh preview ghép outfit |
| `prop_reference` | Từng weapon/accessory riêng |
| `prop_sheet_preview` | Ảnh preview ghép assets |
| `expression_reference` | Từng expression riêng |
| `expression_sheet_preview` | Ảnh preview ghép 4 expressions |

### `character_json` Schema Mới

```json
{
  "view_assets": {
    "front": "uuid",
    "side": "uuid",
    "back": "uuid",
    "three_quarter": "uuid",
    "preview": "uuid"
  },
  "outfit_assets": {
    "robe": "uuid",
    "boots": "uuid",
    "belt": "uuid",
    "preview": "uuid"
  },
  "prop_assets": {
    "sword": "uuid",
    "pendant": "uuid",
    "preview": "uuid"
  },
  "expression_assets": {
    "neutral": "uuid",
    "angry": "uuid",
    "smile": "uuid",
    "battle": "uuid",
    "preview": "uuid"
  }
}
```

---

## IPAdapter Parameters Per View

| View | ipa_weight | denoise | Lý do |
|---|---|---|---|
| front | — | — | Master, txt2img thuần |
| side | 0.85 | 0.45 | Cần giữ mặt rõ |
| three_quarter | 0.85 | 0.45 | Cần giữ mặt rõ |
| back | 0.75 | 0.50 | Không cần giữ mặt, tập trung outfit/hair |
| face_neutral | 0.90 | 0.35 | Lock identity chặt |
| face_angry | 0.88 | 0.38 | Lock identity, hơi lơi để expression thay đổi |
| face_smile | 0.88 | 0.38 | Như trên |
| face_battle | 0.85 | 0.40 | Cho phép đổi cường độ ánh mắt |

---

## File Structure Sau Khi Implement

```
apps/api/app/services/
├── character.py           [MODIFY] — thêm 4 generate methods + orchestrator
├── character_dna.py       [MODIFY] — VIEW_TAGS chi tiết, extract outfit/asset items
├── image_gen.py           [MODIFY] — thêm 6 methods mới
└── comfyui/
    └── workflows/
        ├── character_portrait_hires.json     [NEW] — master front + hires fix
        ├── character_view_ipadapter.json     [NEW] — view gen với IPAdapter
        ├── face_restore.json                 [NEW] — GFPGAN pipeline
        ├── outfit_item.json                  [NEW] — outfit item trên white bg
        └── asset_item.json                   [NEW] — weapon/prop trên white bg

apps/api/app/routers/
└── characters.py          [MODIFY] — 5 endpoints mới

# Không cần sửa DB schema, migration, hay models
```

---

## Implementation Order (Step-by-step)

```
Step 1: Tạo workflow character_portrait_hires.json (hires fix)
Step 2: Tạo workflow character_view_ipadapter.json (IPAdapter views)
Step 3: Cập nhật VIEW_TAGS trong character_dna.py
Step 4: Thêm generate_master_front_view() + generate_view_with_reference() vào image_gen.py
Step 5: Refactor generate_character_sheet() trong character.py → dùng hybrid strategy
Step 6: Thêm endpoint POST /generate-character-sheet → test với nhân vật thực
Step 7: Tạo workflow face_restore.json + thêm apply_face_restore() vào image_gen.py
Step 8: Tạo workflow outfit_item.json + generate_outfit_item() + generate_outfit_sheet()
Step 9: Tạo workflow asset_item.json + generate_asset_item() + generate_asset_sheet()
Step 10: generate_expression() + generate_expression_sheet() (IPAdapter từ front)
Step 11: Thêm generate_full_reference() orchestrator
Step 12: Thêm tất cả endpoints còn lại vào router
Step 13: Test full pipeline với nhân vật a377b64a
```
