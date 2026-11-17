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
import shutil

import modal

APP_NAME = "tai-sinh-di-san-so-api"
GPU_TYPE = os.environ.get("MODAL_GPU", "T4")
SCALEDOWN_SECONDS = 900  # 15 phút (nằm trong khung 10–15 phút theo thiết kế)

HF_VOLUME_MOUNT = "/data/hf-cache"
OUTPUT_VOLUME_MOUNT = "/data/outputs"
BAKED_HF_CACHE = "/cache/huggingface"

app = modal.App(APP_NAME)

image = modal.Image.from_dockerfile(
    path="Dockerfile",
    context_mount=None,
)

hf_volume = modal.Volume.from_name("tai-sinh-di-san-hf-cache", create_if_missing=True)
output_volume = modal.Volume.from_name("tai-sinh-di-san-outputs", create_if_missing=True)
api_secret = modal.Secret.from_name("tai-sinh-di-san-secret")


@app.function(
    image=image,
    gpu=GPU_TYPE,
    max_containers=1,
    scaledown_window=SCALEDOWN_SECONDS,
    timeout=900,
    volumes={
        HF_VOLUME_MOUNT: hf_volume,
        OUTPUT_VOLUME_MOUNT: output_volume,
    },
    secrets=[api_secret],
)
@modal.asgi_app()
def fastapi_app():
    # Đồng bộ cache model đã nạp sẵn trong Dockerfile sang Volume nếu Volume mới tạo lần đầu
    baked_dir = Path(BAKED_HF_CACHE)
    vol_hf_dir = Path(HF_VOLUME_MOUNT)
    vol_hf_dir.mkdir(parents=True, exist_ok=True)
    if baked_dir.is_dir() and not any(vol_hf_dir.iterdir()):
        shutil.copytree(baked_dir, vol_hf_dir, dirs_exist_ok=True)
        hf_volume.commit()

    Path(OUTPUT_VOLUME_MOUNT, "variants").mkdir(parents=True, exist_ok=True)
    Path(OUTPUT_VOLUME_MOUNT, "audit").mkdir(parents=True, exist_ok=True)

    os.environ["HF_HOME"] = HF_VOLUME_MOUNT
    os.environ["DH_OUTPUT_DIR"] = OUTPUT_VOLUME_MOUNT

    from api.main import app as web_app

    return web_app
