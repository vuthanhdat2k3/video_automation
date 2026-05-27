# Tóm Tắt Quá Trình Thiết Lập & Giải Quyết Lỗi Trên GPU Server (ckey)

Tài liệu này tóm tắt toàn bộ quá trình cấu hình môi trường chạy **ComfyUI sinh video Wan2.1-14B** từ xa trên máy chủ GPU thuê (RTX 4090), các lỗi phát sinh trong hệ thống gốc của container, và cách khắc phục chi tiết để bạn có thể áp dụng cho các lần thuê GPU tiếp theo.

---

## 1. Các Việc Đã Làm (What Was Done)

1. **Khởi tạo và cập nhật ComfyUI Core:**
   - Phát hiện ComfyUI cài sẵn trong container `chieustudio/comfyui-latest-nvidia` quá cũ (từ tháng 10/2023).
   - Khởi tạo Git trong `/app` trên remote server, thêm cấu hình `safe.directory` và đồng bộ mã nguồn lên phiên bản `master` mới nhất từ GitHub.
2. **Cài đặt và thiết lập các Mô hình (Models):**
   - Đã tải đầy đủ 4 models cần thiết cho Wan2.1-14B-I2V:
     - `wan2.1-i2v-14b-480p-Q6_K.gguf` (14 GB - UNET model)
     - `umt5_xxl_fp8_e4m3fn_scaled.safetensors` (6.3 GB - Text Encoder)
     - `clip_vision_h.safetensors` (1.2 GB - Image Encoder)
     - `wan_2.1_vae.safetensors` (243 MB - VAE model)
   - Tạo liên kết tượng trưng (symlinks) để map tên mô hình khớp hoàn toàn với workflow chuẩn của dự án (ví dụ: tạo file ảo `wan2.1-i2v-14b-gguf-q6.safetensors` trỏ đến file Q6_K thực tế).
3. **Nâng cấp môi trường Python tương thích:**
   - Cài đặt bản `opencv-python-headless` để loại bỏ lỗi thiếu thư viện đồ họa hệ thống (`libxcb.so.1`) của `ComfyUI-VideoHelperSuite`.
   - Nâng cấp **PyTorch** trong virtual environment của container từ `2.1.0` lên `2.4.0+cu121` để hỗ trợ cơ chế đăng ký Custom Ops của thư viện `comfy_kitchen`.
   - Sắp xếp và ép cài đặt phiên bản ổn định của `transformers==4.48.2` và `tokenizers==0.21.0` để hỗ trợ cấu trúc của Wan2.1 mà không làm crash hệ thống import của PyTorch.
4. **Xóa lock file SQLite:**
   - Phát hiện và xóa file lock rác `/app/user/comfyui.db.lock` sinh ra do crash tiến trình cũ, giúp khôi phục khả năng ghi nhận hàng đợi (queue) và lịch sử (history) của ComfyUI.
5. **Cập nhật mã nguồn hệ thống (Local codebase):**
   - **Đồng bộ hóa Workflow JSON:** Viết lại file cấu hình workflow `wan2_1_i2v_14b.json` để ánh xạ chính xác với các lớp node mới của `ComfyUI-WanVideoWrapper` phiên bản mới (`WanVideoModelLoader`, `WanVideoTextEncode`, `WanVideoSampler`, `WanVideoDecode`).
   - **Tối ưu hóa kích thước động:** Cập nhật file `wan2_video_gen.py` để tự động tính toán kích thước chiều rộng/cao cho video dựa trên `aspect_ratio` của project (`9:16` -> 480x832, `16:9` -> 832x480).

---

## 2. Bảng Tóm Tắt Lỗi & Cách Khắc Phục (Errors & Solutions)

> [!IMPORTANT]
> Đây là cẩm nang quan trọng để bạn tự xử lý hoặc cài đặt lại môi trường trong những lần thuê GPU tiếp theo trên các hệ thống container sạch của ckey.

| STT | Triệu chứng / Log báo lỗi | Nguyên nhân | Giải pháp khắc phục |
| :--- | :--- | :--- | :--- |
| **1** | `ModuleNotFoundError: No module named 'comfy.float'`<br>hoặc `cannot import name 'copy_to_param' from 'comfy.utils'` | Phiên bản ComfyUI core trong container gốc quá cũ (từ năm 2023), thiếu các hàm hỗ trợ mô hình mới. | **Cập nhật ComfyUI Core:**<br>1. SSH vào server.<br>2. Chạy: `cd /app && git init`<br>3. `git config --global --add safe.directory /app`<br>4. `git remote add origin https://github.com/comfyanonymous/ComfyUI.git`<br>5. `git fetch origin && git reset --hard origin/master` |
| **2** | `AttributeError: module 'torch.library' has no attribute 'custom_op'` | Thư viện `comfy_kitchen` (yêu cầu bởi ComfyUI mới) cần PyTorch >= 2.4.0, nhưng container chỉ có PyTorch 2.1.0. | **Nâng cấp PyTorch:**<br>Chạy lệnh nâng cấp trong venv:<br>`/app/venv/bin/pip install torch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0 --index-url https://download.pytorch.org/whl/cu121` |
| **3** | `ImportError: libxcb.so.1: cannot open shared object file: No such file or directory` | Thư viện OpenCV thường của node `VideoHelperSuite` yêu cầu GUI X11 hệ thống vốn không có trong container headless. | **Thay thế bằng OpenCV Headless:**<br>`/app/venv/bin/pip uninstall -y opencv-python opencv-python-headless`<br>`/app/venv/bin/pip install --no-deps opencv-python-headless` |
| **4** | `ImportError: huggingface-hub>=0.24.0,<1.0 is required ... but found huggingface-hub==1.16.4` | Cài đặt tự động nâng `huggingface-hub` lên bản `1.x`, vượt quá giới hạn chặn `<1.0` của thư viện `transformers`. | **Hạ cấp huggingface-hub:**<br>`/app/venv/bin/pip install --force-reinstall --no-deps "huggingface-hub==0.28.1"` |
| **5** | `ModuleNotFoundError: No module named 'torch.distributed.tensor.device_mesh'` | Bản prerelease `transformers 5.9.0` bị lỗi cấu trúc Mesh khi import trên PyTorch 2.4.0. | **Cài đặt transformers bản ổn định:**<br>`/app/venv/bin/pip install --force-reinstall --no-deps "transformers==4.48.2" "tokenizers==0.21.0"` |
| **6** | `[ERROR] Failed to initialize database ... Could not acquire lock on database '/app/user/comfyui.db'` | File `.lock` ảo còn sót lại từ lần crash trước làm ComfyUI tưởng database đang bị tiến trình khác chiếm dụng, gây treo hàng đợi. | **Xóa file lock và khởi động lại:**<br>1. Chạy: `rm -f /app/user/comfyui.db.lock`<br>2. Kill các tiến trình python cũ: `pkill -9 -f main.py`<br>3. Restart s6 service: `s6-svc -u /etc/services.d/comfyui` |
| **7** | `Client error '400 Bad Request' for url '.../prompt'` | (A) Custom Node phiên bản mới đổi tên class từ tiền tố `Wan2` sang `WanVideo`. (B) Node `WanVideoDecode` bắt buộc phải truyền đủ 4 tham số tiling từ workflow JSON. | **Cấu hình lại Workflow JSON:**<br>1. Thay các node cũ thành node mới (vd: `WanVideoModelLoader`, `WanVideoTextEncode`, v.v.).<br>2. Thêm rõ các tham số vào Node 9 (Decode) trong file JSON:<br>`"tile_x": 272, "tile_y": 272, "tile_stride_x": 144, "tile_stride_y": 128`. |

---

## 3. Trạng Thái Hiện Tại Khi Hết Hạn Thuê

- **Remote ComfyUI:** Đã cấu hình hoàn tất, online hoàn hảo và load sạch sẽ 100% các custom nodes cần thiết (GGUF, WanVideo, VHS).
- **Database Local:** Đã được khởi tạo đầy đủ các bảng dữ liệu qua Alembic migrations.
- **Workflow & Code:** Đã được sửa đổi để sẵn sàng kích hoạt render Wan2.1-14B thông qua remote server bất kỳ lúc nào bạn thuê GPU mới (chỉ cần cập nhật địa chỉ IP và SSH Port trong file `.env`).
