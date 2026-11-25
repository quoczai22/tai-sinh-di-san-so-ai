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

import datetime
import hmac
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
billing_image = modal.Image.debian_slim(python_version="3.11").pip_install("fastapi[standard]")

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


@app.function(
    image=billing_image,
    max_containers=1,
    scaledown_window=60,
    timeout=30,
    secrets=[api_secret],
)
@modal.asgi_app()
def billing_summary():
    """Đọc số liệu chi phí thật của Modal Workspace trên CPU (không bật GPU)."""
    from fastapi import FastAPI, HTTPException, Request

    billing_app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    def get_summary(request):
        expected = (os.environ.get("DH_API_KEY") or "").strip()
        provided = (request.headers.get("x-api-key") or "").strip()
        if not expected or not hmac.compare_digest(provided, expected):
            raise HTTPException(status_code=401, detail="Unauthorized")

        ws = modal.Workspace.from_context()
        summary = ws.billing.summary("this month")
        metered_cost = float(summary.metered_cost)
        billed_cost = float(summary.billed_cost)
        credits_applied = abs(float(summary.adjustments.get("Credits", 0)))

        today_cost: float | None = None
        week_cost: float | None = None
        recent_days: list[dict[str, object]] = []
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            today_start = datetime.datetime(now.year, now.month, now.day, tzinfo=datetime.timezone.utc)
            week_ago = today_start - datetime.timedelta(days=7)
            items = ws.billing.report(start=week_ago, end=now, resolution="d")
            daily_map: dict[str, float] = {}
            for item in items:
                day_key = item.interval_start.strftime("%Y-%m-%d")
                daily_map[day_key] = daily_map.get(day_key, 0.0) + float(item.cost)
            today_key = today_start.strftime("%Y-%m-%d")
            today_cost = daily_map.get(today_key, 0.0)
            week_cost = sum(daily_map.values())
            recent_days = [
                {"date": day, "cost": round(cost, 4)}
                for day, cost in sorted(daily_map.items(), reverse=True)[:3]
            ]
        except Exception:
            pass

        return {
            "metered_cost": round(metered_cost, 4),
            "billed_cost": round(billed_cost, 4),
            "credits_applied": round(credits_applied, 4),
            "today_cost": round(today_cost, 4) if today_cost is not None else None,
            "week_cost": round(week_cost, 4) if week_cost is not None else None,
            "daily": recent_days,
            "currency": "USD",
        }

    get_summary.__annotations__ = {"request": Request}
    billing_app.add_api_route("/", get_summary, methods=["GET"])
    billing_app.add_api_route("/summary", get_summary, methods=["GET"])

    return billing_app
