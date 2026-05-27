# Bug Report — AI 2D Animation Studio

## 🔴 Nghiêm trọng

### 1. Lỗi 500 khi gen ảnh khóa — Hardcoded ComfyUI Input path

**File:** `apps/api/app/services/keyframe_gen.py:124-128`

```python
comfy_input_dir = Path("/home/dat/pipeline/ComfyUI/input")
```

Đường dẫn cứng này sẽ **gây 500** nếu thư mục không tồn tại trên máy chạy. Cần đưa vào config.

---

### 2. Lỗi 500 khi gen ảnh khóa — IP-Adapter bypass dễ vỡ

**File:** `apps/api/app/services/keyframe_gen.py:161`

```python
workflow["9"]["inputs"]["model"] = ["1", 0]
```

Mutate trực tiếp workflow dict. Nếu workflow JSON thay đổi node numbering (node 9 không phải KSampler), dòng này gây `KeyError` → 500. Cần validate workflow structure trước khi mutate.

---

### 3. `_download_image` không handle `video` output từ Wan2.1

**File:** `apps/api/app/services/comfyui/client.py:147-163`

```python
images = node_output.get("images", [])
if not images:
    images = node_output.get("gifs", [])
```

Wan2.1 workflow dùng `VHS_VideoCombine` output. Nếu ComfyUI trả `video` entries thay vì `gifs`, sẽ raise `ComfyUIClientError("No image/video found in output")` → 500. Cần thêm fallback:
```python
if not images:
    images = node_output.get("gifs", [])
if not images:
    images = node_output.get("video", [])
```

---

### 4. Silent fail trong `_translate` — nuốt lỗi LLM

**Files:**
- `apps/api/app/services/keyframe_gen.py:48`
- `apps/api/app/services/animation_gen.py:57`

```python
except Exception as e:
    pass
```

Nếu LLM provider (Ollama) không chạy hoặc lỗi, exception bị nuốt → text không được translate → prompt tiếng Việt gửi sang ComfyUI → ảnh sai chất lượng → người dùng thấy lỗi.

---

### 5. LLM config thiếu fields — gây `AttributeError`

**File:** `apps/api/app/services/tts.py:44-46`

```python
client = OpenAI(
    base_url=settings.llm_base_url.replace("/chat", ""),  # KHÔNG TỒN TẠI
    api_key=settings.llm_api_key or "sk-default",          # KHÔNG TỒN TẠI
)
```

`config.py` không có `llm_base_url` hay `llm_api_key`. Chỉ có `openai_base_url` và `openai_api_key`. Gây `AttributeError` khi dùng OpenAI TTS.

---

## 🟠 Trung bình

### 6. Trùng lặp code — `STYLE_MAP` định nghĩa 3 lần

**Files:**
- `apps/api/app/services/background_gen.py:12`
- `apps/api/app/services/keyframe_gen.py:14`
- `apps/api/app/services/animation_gen.py:14`

```python
STYLE_MAP = {
    "2d_chinese_donghua": "Chinese donghua animation style",
    "2d_anime": "anime style, Japanese animation",
    ...
}
```

Cần đưa vào shared module hoặc config.

---

### 7. Trùng lặp code — `_translate()` method

**Files:**
- `apps/api/app/services/keyframe_gen.py:44`
- `apps/api/app/services/animation_gen.py:44`

Cùng implementation. Cần extract thành utility function.

---

### 8. Trùng lặp code — Character description building

**Files:**
- `apps/api/app/services/keyframe_gen.py:86-130`
- `apps/api/app/services/animation_gen.py:86-110`

Logic xây dựng mô tả nhân vật giống hệt nhau ở 3 service. Cần shared helper.

---

### 9. `keyframe_gen.json` vs `keyframe_generation.json` — nhầm lẫn

**Directory:** `apps/api/app/services/comfyui/workflows/`

- `keyframe_gen.json` — không rõ ai dùng
- `keyframe_generation.json` — được `keyframe_gen.py` dùng
- `animation_gen.json` — được `animation_gen.py` dùng

Tên file không nhất quán.

---

### 10. `AnimationGenService` có khả năng là dead code

**File:** `apps/api/app/services/animation_gen.py`

`worker.py` chỉ gọi `Wan2VideoGenService`, không gọi `AnimationGenService`. Nếu không dùng, cần xóa hoặc deprecate.

---

### 11. Busy-wait polling parent job

**File:** `apps/api/app/services/worker.py:335-346`

```python
for _ in range(60):
    ...
    await asyncio.sleep(5)  # poll 5 giây
```

Chờ job cha hoàn thành bằng polling. Lãng phí tài nguyên, không scale. Cần dùng event-driven (Redis pub/sub hoặc ARQ dependency).

---

### 12. N+1 Queries

**Files:**
- `apps/api/app/services/keyframe_gen.py:63-94`
- `apps/api/app/services/animation_gen.py:63-94`
- `apps/api/app/services/worker.py:119-120`

Mỗi shot/scene trigger nhiều SELECT riêng lẻ:
1. `select(ShotModel)` → `select(SceneModel)` → `select(ProjectModel)` → `select(CharacterModel)` → `select(AssetModel)`

Cần dùng SQLAlchemy `selectinload()` hoặc `joinedload()`.

---

### 13. Inline imports

**Files:** `keyframe_gen.py:48,114,119,146`, `worker.py:199,128`, `lipsync.py:50`

Import bên trong function làm giảm readability và performance.

---

### 14. Exporter quá phức tạp

**File:** `apps/api/app/services/exporter.py:377 dòng`

Quá nhiều responsibility:
- Filter chain (scale, camera motion, color grade, shadow, VFX)
- Audio mixing
- Subtitles
- Transitions (xfade)

Cần tách thành pipeline steps riêng.

---

## 🟡 Thấp

### 15. `config.py` hardcoded env_file path

**File:** `apps/api/app/config.py:11`

```python
env_file="/home/dat/pipeline/video_automation/.env",
```

Đường dẫn tuyệt đối, không portable. Nên dùng:
```python
env_file=PROJECT_ROOT / ".env",
```

### 16. Test database URL hardcoded

**File:** `apps/api/tests/conftest.py:12`

```python
os.environ["DATABASE_URL"] = "postgresql+asyncpg://ai2d:ai2d_pass@localhost:15432/ai2d_flow"
```

Nên đọc từ env var với fallback.

### 17. Không có authentication/authorization

**Files:** `apps/api/app/routers/*.py`

Tất cả API endpoints đều public, không có xác thực.

### 18. No input validation cho prompts

**Files:** `apps/api/app/services/keyframe_gen.py`, `wan2_video_gen.py`

Prompt từ user/LLM được gửi trực tiếp sang ComfyUI không qua sanitize.

---

## Priority Fix Recommendations

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| P0 | #1, #3 — Fix 500 keygen + video download | 2h | Critical |
| P0 | #5 — Fix LLM config fields | 30m | Critical |
| P1 | #2 — Validate workflow nodes before mutate | 1h | High |
| P1 | #4 — Remove silent `except: pass` | 30m | High |
| P1 | #6, #7, #8 — DRY shared code | 3h | High |
| P2 | #11 — Replace polling with event-driven | 4h | Medium |
| P2 | #12 — Eager loading N+1 | 2h | Medium |
| P3 | #9, #10, #13, #14, #15, #16, #17, #18 | Varies | Low |
