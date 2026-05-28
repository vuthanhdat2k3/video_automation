# Technical Issue Report: Outfit & Asset Consistency

## 1. Flow Hiện Tại (Current Generation Flow)
Toàn bộ quy trình sinh ảnh nhân vật được chia thành một **4-Phase Full Pipeline** chạy tự động:
1. **Phase 1: Character Turnaround Views**:
   - Sinh ảnh **Master Front View** (View chính diện) từ text prompt + DNA của nhân vật, áp dụng HiRes Fix để tăng độ nét.
   - Sinh Side View và Back View dùng IP-Adapter lấy style từ Master Front View.
   - Chạy GFPGAN để phục hồi và làm nét khuôn mặt (Face Restoration) cho các góc nhìn này.
2. **Phase 2: Outfit Items (Trang phục/Giáp)**: Sinh các vật phẩm cô lập (Bodysuit, Kính Visor, v.v.) độc lập trên nền trắng.
3. **Phase 3: Asset Items (Vũ khí/Đạo cụ)**: Sinh các món đồ vật/vũ khí cô lập (VD: Cyber Sword) trên nền trắng.
4. **Phase 4: Expression Views (Biểu cảm)**: Sinh các khuôn mặt biểu cảm (Smile, Angry, Battle) bằng IP-Adapter lock identity từ Master Front View.

**Cơ chế sinh vật phẩm cô lập (Phase 2 & Phase 3)** đang diễn ra theo nguyên lý sau:
- **Reference Image**: Sử dụng **nguyên bản** ảnh Master Front View (bức ảnh chứa toàn bộ nhân vật, tóc, khuôn mặt, chân tay, và các hiệu ứng năng lượng xung quanh) từ Phase 1.
- **IP-Adapter**: Đưa ảnh này vào IP-Adapter Advanced với `weight = 0.52` để trích xuất phong cách (style) và màu sắc (color palette).
- **Prompt Isolation**: Sử dụng text prompt ép buộc cô lập như `isolated white background, no human, no face, no mannequin`.

## 2. Vấn Đề Gặp Phải (The Issues)
Dù đã sử dụng prompt triệt tiêu hình thể con người, pipeline hiện tại vẫn thất bại trong việc đồng bộ hóa thiết kế đồ vật với 2 lỗi đặc biệt nghiêm trọng:

### A. Lỗi Ám Ảnh Hình Thể (Body Bleeding / Full Character Generation)
Thay vì sinh ra một đồ vật tĩnh (như kính visor, hoặc bộ bodysuit) nằm riêng lẻ trên nền trắng, mô hình lại **vẽ ra nguyên một cô gái** đang đeo chiếc kính đó hoặc mặc bộ bodysuit đó. 
- **Lý do**: Ảnh reference chiếm 90% là nhân vật và tóc. IP-Adapter đã hiểu lầm rằng "đặc điểm cốt lõi" cần giữ lại là hình dáng cơ thể và mái tóc, nên nó bỏ qua lệnh `no human` trong negative prompt.

### B. Lệch Tông Màu / Sai Chất Liệu (Color & Texture Drifting)
Các đồ vật sinh ra hoàn toàn không khớp với thiết kế trên Master Front View.
- Ví dụ thực tế: Kính visor màu xanh cyan trong suốt bị biến thành mũ bảo hiểm robot màu hầm hố xanh tím. Kiếm năng lượng cyan bị biến thành kiếm thép lưỡi hồng.
- **Lý do**: IP-Adapter lấy trung bình cộng tất cả các màu có trong ảnh reference (màu tóc trắng bạc, màu da, màu áo đen trắng, màu hiệu ứng năng lượng). Việc trộn lẫn này phá hủy hoàn toàn màu sắc đặc trưng của vật phẩm mục tiêu.

## 3. Chẩn Đoán Nguyên Nhân Cốt Lõi (Root Cause)
**"Rác đầu vào" (Input Noise)**.
Công nghệ IP-Adapter rất nhạy cảm với composition của ảnh tham chiếu. Khi ta muốn AI sao chép "chất liệu áo giáp" hoặc "lưỡi kiếm cyan", ta không thể đưa cho nó một bức ảnh có cả mặt, tóc và đùi. Đầu vào quá nhiễu sẽ làm loãng sự chú ý của AI khỏi vật phẩm chính.

## 4. Hướng Giải Quyết Tối Ưu Đề Xuất (The Solution)
Phương pháp "cắt ảnh theo tọa độ cứng" (Hard Cropping) có rủi ro cao nếu vũ khí bị lệch hoặc item nhỏ bị tóc che. Theo kinh nghiệm và workflow từ cộng đồng ComfyUI, giải pháp tối ưu cho production là **Dynamic Segmented Reference Extraction** kết hợp **IPAdapter Attention Mask**:

1. **Segmented Reference Extraction (Dùng SAM/Segmentation)**: 
   - Thay vì crop tọa độ cứng, sử dụng SAM (Segment Anything Model) với text prompt (VD: "visor", "chest armor", "sword") để tự động tìm và tách chính xác vùng item trên ảnh Master Front high-res.
   - Trích xuất bounding box của mask (cộng thêm 15-30% padding) và đặt vào canvas vuông trắng để tạo ảnh reference chuẩn (High-res Prep).

2. **Validation Fallback**:
   - Tự động kiểm tra chất lượng patch vừa crop (item phải chiếm 35-60% canvas, không dính quá nhiều da/tóc). Nếu patch lỗi/nhỏ, kích hoạt fallback sang text prompt thuần.

3. **IPAdapter Attention Mask & Weight Tuning**:
   - Đưa mask của item vào cổng `attn_mask` của IPAdapter Advanced để ép IP-Adapter chỉ trích xuất phong cách từ đúng vùng item đó (quan trọng hơn cả negative prompt).
   - **Không tăng weight mù quáng**: Sau khi reference sạch, weight có thể tăng có kiểm soát theo từng item, nhưng mặc định nên bắt đầu từ mức an toàn **0.45 - 0.65** (VD: Visor 0.45-0.55, Bodysuit 0.50-0.65) để tránh làm biến dạng composition.

4. **Giải Pháp Production Dài Hạn (Phase 1.5 - Canonical Item Reference)**:
   - Thêm một bước trung gian: Sau khi có Master Front View, tự động sinh các "Canonical Item Refs" (ảnh các item độc lập, nền trắng, high-res) và validate 1 lần duy nhất.
   - Ở Phase 2/3, dùng chính các Canonical Item này làm reference thay vì phải crop lại từ nhân vật, biến đồ vật thành các asset độc lập thực thụ.
