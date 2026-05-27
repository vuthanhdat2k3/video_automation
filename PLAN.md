# Kế Hoạch Triển Khai — Hệ Thống Sinh Video Hoạt Hình AI Cao Cấp (Cinematic Donghua Pipeline)

Kế hoạch này giải quyết triệt để các vấn đề của hệ thống cũ (ảnh bị mờ nhòe, không rõ nội dung, các khung hình không liên quan nhau và thiếu tính nhất quán) bằng cách nâng cấp lên pipeline **Keyframe-to-Video (I2V)** chất lượng điện ảnh, sử dụng các mô hình AI mã nguồn mở tiên tiến nhất của Trung Quốc.

---

## 1. Phân Tích & Giải Pháp Đột Phá

| Vấn đề cũ | Nguyên nhân | Giải pháp kỹ thuật nâng cấp |
| :--- | :--- | :--- |
| **Ảnh mờ nhòe, không rõ nét** | Tạo video độ phân giải thấp, không qua bước siêu phân giải (Upscale). | **Hi-Res Latent Upscale** (local) + **Video Super-Resolution** (GPU thuê): Phóng to ảnh khóa bằng `4x-UltraSharp` / `RealESRGAN` để đạt độ phân giải cực nét trước khi tạo chuyển động. |
| **Các ảnh chắp vá, không liên quan nhau** | Sinh trực tiếp từ Text-to-Video (T2V) khiến AI tự vẽ lại từ đầu mỗi cảnh. | **Image-to-Video (I2V) Pipeline**: Sinh 1 ảnh tĩnh (Keyframe) hoàn hảo trước. Sau đó dùng ảnh đó làm đầu vào cho mô hình I2V. AI chỉ làm chuyển động các chi tiết (tóc bay, mây trôi, camera) giữ nguyên bối cảnh. |
| **Nhân vật bị đổi mặt/trang phục** | Không có cơ chế khóa chặt đặc điểm nhân vật. | **IP-Adapter FaceID Plus v2 + ReferenceNet**: Khóa chặt cấu trúc khuôn mặt, màu tóc, trang phục của nhân vật xuyên suốt mọi shot quay. |
| **Khẩu hình không khớp audio** | Dùng các mô hình cũ như Wav2Lip làm mờ miệng và lệch tiếng. | **MuseTalk / Wav2Lip-HD**: Mô hình Lip-Sync chất lượng cao của Trung Quốc, giữ nguyên chất lượng mặt nhân vật và khớp khẩu hình chính xác theo âm thanh. |

---

## 2. Bảng So Sánh & Yêu Cầu Tài Nguyên Hệ Thống (Thuê GPU)

Để tối ưu chi phí (Trade-off), chúng tôi đề xuất quy trình kết hợp: **Sinh ảnh khóa & khóa nhân vật tại máy Local (RTX 3060 12GB)**, sau đó **gửi qua server GPU thuê (RTX 4090 24GB) để chạy mô hình Video & Lip-sync đỉnh cao**.

### A. Các Mô Hình Sinh Video (Video Generation)

> [!IMPORTANT]
> Để có chất lượng hoạt hình gánh được rạp phim/mạng xã hội, bạn bắt buộc phải sử dụng dòng mô hình **13B-14B tham số** trên GPU 24GB VRAM.

| Mô hình | VRAM tối thiểu | GPU khuyến nghị | Chất lượng | Chi phí thuê GPU | Đánh giá & Khuyến nghị |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Wan2.1-14B-I2V (GGUF Q6)** | **20 GB** | **RTX 4090 / A5000 (24GB)** | 🏆 **Xuất sắc nhất** (Premium) | ~$0.40 - $0.80 / giờ | **KHUYÊN DÙNG**: Mô hình mã nguồn mở mạnh nhất hiện nay của Alibaba. Chuyển động vật lý mượt mà, giữ chi tiết ảnh gốc cực tốt, thời gian render nhanh (2-5 phút/clip). |
| **HunyuanVideo (FP8)** | **22 GB** | **RTX 4090 (24GB)** | 💎 **Rất cao** (Cinematic) | ~$0.40 - $0.80 / giờ | Chất lượng điện ảnh thực tế, nhưng render lâu hơn Wan2.1 và bám sát ảnh gốc ở mức khá. |
| **Wan2.1-1.3B-I2V** | **8-12 GB** | **RTX 3060 (12GB) - Chạy Local** | ⚡ **Khá** (Draft) | **MIỄN PHÍ** (Chạy máy nhà) | Tốt để test workflow local trước khi mang lên server thuê. Độ phân giải thấp hơn bản 14B. |
| **FramePack** | **6 GB** | **RTX 3060 (12GB) - Chạy Local** | 🎬 **Khá** | **MIỄN PHÍ** (Chạy máy nhà) | Rất nhẹ, hỗ trợ làm clip dài, phù hợp cấu hình thấp nhưng chuyển động không mượt bằng Wan2.1. |

### B. Mô Hình Sinh Ảnh Khóa & Khóa Nhân Vật (Keyframe & Consistency)

*Tất cả mô hình này đều chạy mượt mà trên máy Local RTX 3060 12GB của bạn:*
- **NoobAI-XL (hoặc IllustriousXL merge)**: Checkpoint Anime/Donghua tốt nhất thế giới hiện nay. Có V-Prediction giúp màu sắc cực sâu, nét vẽ mịn và chuẩn phong cách phim Trung Quốc.
- **IP-Adapter FaceID Plus v2 (SDXL)**: Khóa nhân vật cực tốt, tiêu tốn chỉ thêm ~1.5GB VRAM.
- **RealESRGAN x4plus-anime**: Bộ upscale chuyên dụng cho hoạt hình 2D, siêu nhẹ (~0.5GB VRAM).

---

## 3. Kiến Trúc Pipeline 4 Bước Hoàn Chỉnh

```text
+-------------------------------------------------------+
| Bước 1: Sinh Keyframe Siêu Nét (Chạy Local RTX 3060)  |
| - Model: NoobAI-XL + IP-Adapter FaceID v2            |
| - Upscale: RealESRGAN x4plus-anime (Độ phân giải HD)  |
+---------------------------+---------------------------+
                            | (Gửi ảnh HD)
                            v
+-------------------------------------------------------+
| Bước 2: Tạo Chuyển Động Video (Chạy trên GPU Thuê)    |
| - Model: Wan2.1-14B-I2V (GGUF Q6)                     |
| - Output: Video clip 5-8 giây, camera mượt, nhất quán |
+---------------------------+---------------------------+
                            | (Gửi video gốc)
                            v
+-------------------------------------------------------+
| Bước 3: Khớp Khẩu Hình Lip-Sync (Chạy trên GPU Thuê)  |
| - Model: MuseTalk (Giữ nét mặt HD)                     |
| - Input: Video từ B2 + File voice nhân vật (TTS)      |
+---------------------------+---------------------------+
                            | (Gửi video lip-sync)
                            v
+-------------------------------------------------------+
| Bước 4: Hậu Kỳ & Xuất Bản (Chạy Local/Server)         |
| - FaceDetailer sửa lỗi méo mặt khi chuyển động        |
| - FFmpeg ghép nhạc nền, hiệu ứng camera, vietsub      |
+-------------------------------------------------------+
```

---

## 4. Các Thay Đổi Trong Codebase

Chúng ta sẽ tích hợp API của ComfyUI chạy trên cả Local và Remote GPU thông qua hệ thống Router thông minh.

### A. ComfyUI Workflows

#### [NEW] [wan2_1_i2v_14b.json](file:///home/dat/pipeline/video_automation/apps/api/app/services/comfyui/workflows/wan2_1_i2v_14b.json)
- Workflow ComfyUI nâng cấp chứa:
  - `Wan2ImageToVideo` node (nạp Wan2.1-14B-I2V GGUF).
  - `LoadImage` (nhận Keyframe HD đã được sinh từ máy local).
  - `KSampler` cấu hình CFG thấp (3.0) để triệt tiêu hiện tượng nhấp nháy (flickering).
  - `VHS_VideoCombine` để xuất MP4 chất lượng cao.

#### [NEW] [keyframe_generation.json](file:///home/dat/pipeline/video_automation/apps/api/app/services/comfyui/workflows/keyframe_generation.json)
- Workflow sinh ảnh khóa nhất quán chạy local:
  - `CheckpointLoaderSimple` nạp NoobAI-XL.
  - `IPAdapterApply` kết hợp FaceID v2 để áp ảnh mẫu nhân vật Lâm Hàn.
  - `UltimateSDUpscale` kết hợp `4x-UltraSharp` nâng cấp ảnh lên 1080p sắc nét.

---

### B. Backend Services

#### [MODIFY] [character.py](file:///home/dat/pipeline/video_automation/apps/api/app/services/character.py)
- Thay đổi prompt sinh ảnh nhân vật mặc định sang tag Danbooru phù hợp với NoobAI-XL (ví dụ: `masterpiece, best quality, 2d chinese donghua style, sharp lines`).
- Tích hợp nạp ảnh Reference của nhân vật từ database và truyền sang IP-Adapter.

#### [NEW] [wan2_video_gen.py](file:///home/dat/pipeline/video_automation/apps/api/app/services/wan2_video_gen.py)
- Triển khai `Wan2VideoGenService` quản lý giao tiếp với ComfyUI remote (GPU thuê).
- Tự động hóa việc đóng gói ảnh Keyframe local gửi lên server thuê, kích hoạt render video 14B, và tải clip `.mp4` thành phẩm về local storage.

#### [MODIFY] [lipsync.py](file:///home/dat/pipeline/video_automation/apps/api/app/services/lipsync.py)
- Chuyển đổi công nghệ Lip-sync từ Wav2Lip cũ sang **MuseTalk API** để giữ nguyên độ phân giải HD của khuôn mặt Lâm Hàn, tránh bị mờ vỡ vùng miệng.

#### [MODIFY] [worker.py](file:///home/dat/pipeline/video_automation/apps/api/app/services/worker.py)
- Cập nhật quy trình chạy job:
  1. Sinh ảnh keyframe trước (`run_generate_keyframe`).
  2. Gửi keyframe đi sinh video qua Wan2.1-14B (`run_generate_wan2_video`).
  3. Chạy MuseTalk ghép giọng nói (`run_lipsync`).
  4. Chạy FFmpeg tổng hợp xuất bản video phim hoàn chỉnh.

---

## 5. Kế Hoạch Xác Minh (Verification Plan)

### Kiểm thử Tự Động
- Viết file `apps/api/tests/test_wan2_pipeline.py` để mock kết nối tới ComfyUI GPU thuê, đảm bảo luồng truyền gửi ảnh và tải video hoạt động trơn tru.

### Kiểm thử Thủ Công
1. **Kiểm tra Chất lượng Ảnh Khóa**: Chạy sinh ảnh Lâm Hàn qua NoobAI-XL + IP-Adapter trên máy local, mở ảnh kiểm tra xem có sắc nét (HD 1080p), chuẩn style Donghua và đúng mặt nhân vật không.
2. **Kiểm tra Video Chuyển Động**: Render thử shot quay 5 giây qua Wan2.1-14B trên GPU thuê. Đánh giá độ nhất quán của nhân vật, camera chuyển động có mượt không, có bị méo mó (morphing) không.
3. **Kiểm tra Lip-Sync & Ghép Nhạc**: Tạo một shot có nhân vật nói chuyện, kiểm tra xem khẩu hình MuseTalk có khớp từng chữ và nét mặt có giữ nguyên HD không.
