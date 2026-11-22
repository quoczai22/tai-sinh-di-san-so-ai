# -*- coding: utf-8 -*-
"""Triển khai Backend GPU chính trên Modal (Tái Sinh Di Sản Số).

Cách chạy và vận hành:
  1. Tạo secret chứa khóa API trên Modal (chạy 1 lần):
       modal secret create tai-sinh-di-san-secret DH_API_KEY=<khoa_bi_mat_cua_nhom>

  2. Chạy thử nghiệm (dev, hot-reload URL tạm thời):
       modal serve modal_app.py

  3. Triển khai chính thức (production):
       modal deploy modal_app.py

  4. Giả lập Modal sập để kiểm thử tự động failover sang HF Space / Demo:
       modal app stop tai-sinh-di-san-so-api

  5. Đổi tạm sang GPU L4 cho buổi phản biện trực tiếp:
       $env:MODAL_GPU="L4"; modal deploy modal_app.py
"""
from __future__ import annotations

import os
from pathlib import Path

import modal

APP_NAME = "tai-sinh-di-san-so-api"
GPU_TYPE = os.environ.get("MODAL_GPU", "T4")
SCALEDOWN_SECONDS = 420  # Giữ T4 tối đa 7 phút sau lượt dùng cuối

OUTPUT_VOLUME_MOUNT = "/data/outputs"
# Model (SD1.5, ControlNet, CLIP) đã tải sẵn vào image ở đường dẫn này (xem Dockerfile).
# Đọc thẳng từ image — KHÔNG copy ~5GB sang Volume lúc khởi động (làm cold start rất chậm).
BAKED_HF_CACHE = "/cache/huggingface"

app = modal.App(APP_NAME)

# Chạy lệnh modal từ gốc repo để các lệnh COPY trong Dockerfile tìm thấy file.
image = modal.Image.from_dockerfile("Dockerfile")

output_volume = modal.Volume.from_name("tai-sinh-di-san-outputs", create_if_missing=True)
api_secret = modal.Secret.from_name("tai-sinh-di-san-secret")


@app.function(
    image=image,
    gpu=GPU_TYPE,
    max_containers=1,
    scaledown_window=SCALEDOWN_SECONDS,
    timeout=900,
    volumes={
        OUTPUT_VOLUME_MOUNT: output_volume,
    },
    secrets=[api_secret],
)
@modal.asgi_app()
def fastapi_app():
    Path(OUTPUT_VOLUME_MOUNT, "variants").mkdir(parents=True, exist_ok=True)
    Path(OUTPUT_VOLUME_MOUNT, "audit").mkdir(parents=True, exist_ok=True)
    output_link = Path("/app/outputs")
    if output_link.is_symlink():
        if output_link.resolve() != Path(OUTPUT_VOLUME_MOUNT):
            raise RuntimeError("/app/outputs trỏ sai Modal Volume")
    elif output_link.exists():
        raise RuntimeError("/app/outputs phải trỏ tới Modal Volume trước khi khởi động")
    else:
        output_link.symlink_to(OUTPUT_VOLUME_MOUNT, target_is_directory=True)

    os.environ["HF_HOME"] = BAKED_HF_CACHE
    os.environ["DH_OUTPUT_DIR"] = OUTPUT_VOLUME_MOUNT
    os.environ.setdefault("TSDS_GENERATE_PER_HOUR", "1000")
    # Fail-closed: thiếu DH_API_KEY trong secret thì tsds.api.main từ chối khởi động.
    os.environ["DH_REQUIRE_API_KEY"] = "1"

    from tsds.api.main import app as web_app

    return web_app
