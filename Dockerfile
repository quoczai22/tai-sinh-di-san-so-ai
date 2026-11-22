# syntax=docker/dockerfile:1
# Image dùng chung cho cả Modal GPU (chính) và Hugging Face Space Docker T4 (dự phòng).
FROM nvidia/cuda:12.6.2-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/cache/huggingface \
    DH_OUTPUT_DIR=/data/outputs \
    DH_REQUIRE_API_KEY=1 \
    SD15_MODEL_ID=stable-diffusion-v1-5/stable-diffusion-v1-5 \
    CONTROLNET_CANNY_ID=lllyasviel/control_v11p_sd15_canny \
    PORT=7860

RUN apt-get update && apt-get install -y --no-install-recommends \
        software-properties-common \
        ca-certificates \
        curl \
        git \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update && apt-get install -y --no-install-recommends \
        python3.11 \
        python3.11-venv \
        python3.11-distutils \
    && curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11 \
    && ln -sf /usr/bin/python3.11 /usr/local/bin/python \
    && ln -sf /usr/bin/python3.11 /usr/local/bin/python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-api.txt /app/requirements-api.txt
RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir -r /app/requirements-api.txt

# Tải sẵn các model (SD1.5 fp16, ControlNet Canny fp16, CLIP ViT-B/32, SAM ViT-B) vào image
# để rút ngắn tối đa thời gian cold start trên cả Modal và HF Space.
# SAM dùng trong tsds/generation/garment/garment_sam.py (tách dáng áo của ảnh LoRA).
RUN mkdir -p "${HF_HOME}" && \
    python -c "\
from huggingface_hub import snapshot_download; \
snapshot_download('stable-diffusion-v1-5/stable-diffusion-v1-5', allow_patterns=['*.json', '*.txt', '*.fp16.safetensors']); \
snapshot_download('lllyasviel/control_v11p_sd15_canny', allow_patterns=['*.json', '*.fp16.safetensors']); \
snapshot_download('openai/clip-vit-base-patch32', allow_patterns=['*.json', '*.txt', '*.safetensors', 'pytorch_model.bin']); \
snapshot_download('facebook/sam-vit-base', allow_patterns=['*.json', '*.txt', '*.safetensors']); \
" && chmod -R 777 "${HF_HOME}"

# Toàn bộ mã Python nằm trong gói tsds/ (api, core, pipeline, generation, evaluation, provenance, quality)
COPY tsds/ /app/tsds/
COPY config/ /app/config/
# data/ gồm cả trọng số LoRA dáng áo dài (data/lora/**/*.safetensors, ~37 MB)
COPY data/ /app/data/

EXPOSE 7860

CMD ["uvicorn", "tsds.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
