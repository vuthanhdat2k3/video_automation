#!/bin/bash
# ==============================================================================
# Script: setup_remote_gpu.sh
# Description: Automated script to configure a remote ComfyUI server for
#              Wan2.1-14B-I2V (GGUF Q6) and video generation pipeline.
# Author: Antigravity AI Assistant
# ==============================================================================

set -e

# Harmonious colors for logs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_info "Bắt đầu thiết lập hệ thống sinh Video Wan2.1-14B trên GPU Server..."

# 1. Kiểm tra và cài đặt aria2 để tải nhanh đa luồng
if ! command -v aria2c &> /dev/null; then
    log_info "Không tìm thấy aria2c. Tiến hành cài đặt aria2..."
    apt-get update && apt-get install -y aria2
    log_success "Đã cài đặt aria2 thành công!"
else
    log_info "aria2c đã được cài đặt sẵn."
fi

# 2. Tự động phát hiện thư mục cài đặt ComfyUI
log_info "Đang tìm kiếm thư mục cài đặt ComfyUI..."
COMFYUI_DIR=""

POSSIBLE_PATHS=(
    "/workspace/ComfyUI"
    "/root/ComfyUI"
    "/app/ComfyUI"
    "/ComfyUI"
    "/app"
    "$(pwd)/ComfyUI"
)

for path in "${POSSIBLE_PATHS[@]}"; do
    if [ -d "$path" ] && [ -f "$path/main.py" ]; then
        COMFYUI_DIR="$path"
        break
    fi
done

if [ -z "$COMFYUI_DIR" ]; then
    # Thử tìm bằng lệnh find nếu các đường dẫn mặc định không khớp
    log_warn "Không tìm thấy ở các đường dẫn mặc định. Đang quét hệ thống..."
    FOUND_PATH=$(find / -name "main.py" | grep "ComfyUI/main.py" | head -n 1 || true)
    if [ -n "$FOUND_PATH" ]; then
        COMFYUI_DIR=$(dirname "$FOUND_PATH")
    fi
fi

if [ -z "$COMFYUI_DIR" ]; then
    log_error "Không thể tìm thấy thư mục cài đặt ComfyUI. Vui lòng chạy script từ thư mục cha của ComfyUI hoặc kiểm tra lại container!"
    exit 1
fi

log_success "Đã tìm thấy ComfyUI tại: ${COMFYUI_DIR}"

# 3. Cài đặt các Custom Nodes
log_info "Tiến hành cài đặt các Custom Nodes cần thiết..."
cd "${COMFYUI_DIR}/custom_nodes"

install_node() {
    local repo_url=$1
    local dir_name=$2
    if [ -d "$dir_name" ]; then
        log_info "Custom node ${dir_name} đã tồn tại. Đang cập nhật..."
        cd "$dir_name" && git pull && cd ..
    else
        log_info "Đang clone repo: ${repo_url}..."
        git clone "$repo_url"
    fi
}

# Clone các node
install_node "https://github.com/city96/ComfyUI-GGUF.git" "ComfyUI-GGUF"
install_node "https://github.com/kijai/ComfyUI-WanVideoWrapper.git" "ComfyUI-WanVideoWrapper"
install_node "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git" "ComfyUI-VideoHelperSuite"

# Cài đặt pip dependencies cho các custom nodes
log_info "Đang cài đặt thư viện python phụ trợ cho các Custom Nodes..."
# Kích hoạt venv nếu có trong ComfyUI
if [ -d "${COMFYUI_DIR}/venv" ]; then
    source "${COMFYUI_DIR}/venv/bin/activate"
fi

pip install -r ComfyUI-WanVideoWrapper/requirements.txt || log_warn "Cảnh báo lỗi cài đặt requirements WanVideoWrapper"
pip install -r ComfyUI-VideoHelperSuite/requirements.txt || log_warn "Cảnh báo lỗi cài đặt requirements VideoHelperSuite"

cd "${COMFYUI_DIR}"

# 4. Tạo các thư mục mô hình nếu chưa tồn tại
log_info "Đảm bảo cấu trúc thư mục mô hình chính xác..."
mkdir -p models/unet
mkdir -p models/diffusion_models
mkdir -p models/clip
mkdir -p models/text_encoders
mkdir -p models/vae
mkdir -p models/clip_vision

# 5. Tải các mô hình AI với tốc độ đa luồng của aria2c
log_info "Bắt đầu tải các mô hình AI trực tiếp từ HuggingFace..."

download_model() {
    local url=$1
    local dest_dir=$2
    local filename=$3
    
    log_info "Đang tải ${filename} vào thư mục ${dest_dir}..."
    aria2c -x 16 -s 16 -k 1M -c --dir="${COMFYUI_DIR}/${dest_dir}" -o "${filename}" "${url}"
}

# A. Wan2.1-14B-I2V GGUF Q6 Model
# Đặt vào cả unet và diffusion_models dưới dạng symlink để cả ComfyUI-GGUF và node gốc đều tìm thấy
download_model \
    "https://huggingface.co/city96/Wan2.1-I2V-14B-480P-gguf/resolve/main/wan2.1-i2v-14b-480p-Q6_K.gguf" \
    "models/unet" \
    "wan2.1-i2v-14b-480p-Q6_K.gguf"

# Tạo liên kết tượng trưng (symlink) sang diffusion_models
ln -sf "${COMFYUI_DIR}/models/unet/wan2.1-i2v-14b-480p-Q6_K.gguf" "${COMFYUI_DIR}/models/diffusion_models/wan2.1-i2v-14b-480p-Q6_K.gguf"

# B. Text Encoder (umt5_xxl_fp8)
download_model \
    "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" \
    "models/clip" \
    "umt5_xxl_fp8_e4m3fn_scaled.safetensors"

# Tạo liên kết tượng trưng sang tên file gốc để tương thích tối đa với workflow
ln -sf "${COMFYUI_DIR}/models/clip/umt5_xxl_fp8_e4m3fn_scaled.safetensors" "${COMFYUI_DIR}/models/clip/umt5_xxl_fp8_e4m3fn.safetensors"
ln -sf "${COMFYUI_DIR}/models/clip/umt5_xxl_fp8_e4m3fn_scaled.safetensors" "${COMFYUI_DIR}/models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"
ln -sf "${COMFYUI_DIR}/models/clip/umt5_xxl_fp8_e4m3fn_scaled.safetensors" "${COMFYUI_DIR}/models/text_encoders/umt5_xxl_fp8_e4m3fn.safetensors"

# C. VAE
download_model \
    "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors" \
    "models/vae" \
    "wan_2.1_vae.safetensors"

# Tạo liên kết tượng trưng sang tên file thay thế để tương thích tối đa
ln -sf "${COMFYUI_DIR}/models/vae/wan_2.1_vae.safetensors" "${COMFYUI_DIR}/models/vae/wan2.1_vae.safetensors"

# D. CLIP Vision (Yêu cầu bắt buộc đối với Image-to-Video)
download_model \
    "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors" \
    "models/clip_vision" \
    "clip_vision_h.safetensors"

log_success "Đã tải xong toàn bộ mô hình AI cần thiết!"

# 6. Hướng dẫn khởi động lại
echo -e "\n======================================================================"
log_success "THIẾT LẬP HOÀN TẤT THÀNH CÔNG!"
echo -e "======================================================================"
log_info "Bây giờ bạn chỉ cần khởi động lại dịch vụ ComfyUI trên Server thuê."
log_info "Bạn có thể khởi động lại container trên ckey Panel,"
log_info "hoặc chạy lệnh khởi động lại tiến trình python trong terminal."
log_info "Đường dẫn ComfyUI của bạn đã sẵn sàng chạy Wan2.1-14B!"
echo -e "======================================================================\n"
