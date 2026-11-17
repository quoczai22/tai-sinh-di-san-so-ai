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

# Tải sẵn các model (SD1.5 fp16, ControlNet Canny fp16, CLIP ViT-B/32) vào image
# để rút ngắn tối đa thời gian cold start trên cả Modal và HF Space.
RUN mkdir -p "${HF_HOME}" "${DH_OUTPUT_DIR}/variants" "${DH_OUTPUT_DIR}/audit" && \
    python -c "\
from huggingface_hub import snapshot_download; \
snapshot_download('stable-diffusion-v1-5/stable-diffusion-v1-5', allow_patterns=['*.json', '*.txt', '*.fp16.safetensors']); \
snapshot_download('lllyasviel/control_v11p_sd15_canny', allow_patterns=['*.json', '*.fp16.safetensors']); \
snapshot_download('openai/clip-vit-base-patch32', allow_patterns=['*.json', '*.txt', '*.safetensors', 'pytorch_model.bin']); \
" && chmod -R 777 "${HF_HOME}" "${DH_OUTPUT_DIR}"

COPY api/ /app/api/
COPY generation/ /app/generation/
COPY evaluation/ /app/evaluation/
COPY streamlit_ui/__init__.py streamlit_ui/heritage_data.py /app/streamlit_ui/
COPY data/ /app/data/

EXPOSE 7860

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
