# -*- coding: utf-8 -*-
"""Mock GPU Backend dùng để kiểm thử failover (Modal -> HF Space -> Demo) không tốn GPU.

Biến môi trường hỗ trợ:
  - PORT=<cổng>          (mặc định: 8001)
  - DELAY=<giây>         (mặc định: 2.0; nếu DELAY >= 15 sẽ giả lập treo kết nối khi gọi API để test timeout failover)
  - FAIL=1               (luôn trả 503 Service Unavailable)
  - WARMUP_CALLS=<số>    (tuỳ chọn: số lần gọi /health đầu tiên trả 503 "warming" để giả lập HF Space đang ngủ)
  - DH_API_KEY=<key>     (tuỳ chọn: kiểm tra header X-API-Key)
  - HF_TOKEN=<token>     (tuỳ chọn: kiểm tra header Authorization: Bearer <token>)
  - BACKEND_NAME=<tên>   (tuỳ chọn: nhãn tên GPU trả về, mặc định "NVIDIA T4 (Mock)")
"""
from __future__ import annotations

from collections import deque
import csv
import hashlib
from pathlib import Path
import os
import shutil
import threading
import time
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.audit import append_audit_event, get_output_dir
from api import store
from provenance.heritage import load_heritage_metadata


PROJECT_ROOT = Path(__file__).resolve().parent
CSV_PATH = PROJECT_ROOT / "evaluation" / "variants.csv"
WEB_VARIANTS_DIR = PROJECT_ROOT / "web_ui" / "assets" / "images" / "variants"

app = FastAPI(title="Tái sinh Di sản Số — Mock GPU Backend", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

_jobs: dict[str, dict] = {}
_queue: deque[str] = deque()
_jobs_cond = threading.Condition()
_worker_started = False
_health_calls = 0


class GenerateRequest(BaseModel):
    heritage_id: str
    seed: int | None = None


class AuditRequest(BaseModel):
    step: int
    event: str
    heritage_id: str | None = None
    variant_name: str | None = None
    backend: str | None = None
    wait_ms: int | None = None
    failover: bool | None = None


def _is_failing() -> bool:
    return os.getenv("FAIL", "0").strip() in {"1", "true", "True", "yes"}


def _get_delay() -> float:
    try:
        return max(0.0, float(os.getenv("DELAY", "2.0")))
    except ValueError:
        return 2.0


def _check_fail_or_hang() -> None:
    if _is_failing():
        raise HTTPException(status_code=503, detail="Mock backend đang ở chế độ FAIL=1 (503 Service Unavailable).")
    delay = _get_delay()
    # Khi DELAY >= 15s (ví dụ DELAY=120 ở tiêu chí nghiệm thu #4), giả lập backend treo phản hồi
    # để cổng Vercel chạm ngưỡng MODAL_TIMEOUT_MS và tự động failover.
    if delay >= 15.0:
        time.sleep(delay)


def verify_auth(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    expected_key = os.getenv("DH_API_KEY", "").strip()
    expected_hf = os.getenv("HF_TOKEN", "").strip()
    if expected_key and x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Thiếu hoặc sai X-API-Key.")
    if expected_hf:
        bearer = f"Bearer {expected_hf}"
        if authorization != bearer and x_api_key != expected_hf:
            raise HTTPException(status_code=401, detail="Thiếu hoặc sai Authorization Bearer HF_TOKEN.")


def heritage_items() -> list[dict]:
    # Mock trả số liệu từ evaluation/variants.csv (bộ hiện vật cũ, nay đã "retired" trong
    # metadata bản chung kết), nên phải chấp nhận cả hiện vật retired.
    return load_heritage_metadata(PROJECT_ROOT, include_retired=True)


def ui_items() -> list[dict]:
    return [
        {
            "id": item["heritage_id"],
            "name": item["name"],
            "dynasty": "Di sản Bát Tràng",
            "description": item.get("team_description", ""),
            "conditioningMode": item["conditioning_mode"],
            "image": f"/media/heritage/{item['heritage_id']}",
            "colors": [],
            "colorNames": [],
            "licenseNote": item["license_note"],
            "variantImageBase": f"./assets/images/variants/{item['heritage_id']}_V",
        }
        for item in heritage_items()
    ]


def _load_csv_variants(heritage_id: str) -> list[dict]:
    rows: list[dict] = []
    if CSV_PATH.is_file():
        with CSV_PATH.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("heritage_id") == heritage_id:
                    rows.append(row)
    rows.sort(key=lambda r: int(r.get("variant_index", 1)))
    out_variants_dir = get_output_dir(PROJECT_ROOT) / "variants"
    out_variants_dir.mkdir(parents=True, exist_ok=True)
    gpu_label = os.getenv("BACKEND_NAME", "NVIDIA T4 16GB (Mock)")

    results = []
    for idx in range(1, 5):
        row = rows[idx - 1] if idx - 1 < len(rows) else {}
        filename = f"{heritage_id}_V{idx}_aodai.png"
        target_img = out_variants_dir / filename
        if not target_img.is_file():
            fallback_img = WEB_VARIANTS_DIR / filename
            if fallback_img.is_file():
                shutil.copy2(fallback_img, target_img)
        sha256_full = (
            hashlib.sha256(target_img.read_bytes()).hexdigest()
            if target_img.is_file()
            else row.get("sha256_design", "").ljust(64, "0")
        )
        results.append({
            "variant_index": idx,
            "heritage_id": heritage_id,
            "seed": int(row.get("seed", 42)),
            "intensity_level": int(row.get("intensity_level", idx)),
            "level_name": row.get("level_name", f"Mức {idx}"),
            "controlnet_weight": float(row.get("controlnet_weight", 0.85 - (idx - 1) * 0.2)),
            "palette_mode": row.get("palette_mode", "original" if idx == 1 else "free"),
            "layout": row.get("layout", "front_panel"),
            "layout_label": row.get("layout_label", "Dải thân trước"),
            "polish_strength": float(row.get("polish_strength", 0.40)),
            "positive_prompt": row.get("positive_prompt", ""),
            "negative_prompt": row.get("negative_prompt", ""),
            "sha256_design": sha256_full,
            "sd_model_id": row.get("sd_model_id", "stable-diffusion-v1-5/stable-diffusion-v1-5"),
            "controlnet_id": row.get("controlnet_id", "lllyasviel/control_v11p_sd15_canny"),
            "torch_version": row.get("torch_version", "2.13.0+cu126"),
            "diffusers_version": row.get("diffusers_version", "0.40.0"),
            "gpu": gpu_label,
            "duration_s": float(row.get("duration_s", 5.6)),
            "similarity_pattern_vs_ceramic": float(row.get("similarity_pattern_vs_ceramic", 0.8)),
            "source_palette": row.get("source_palette", ""),
            "design_path": f"outputs/variants/{filename}",
            "image_url": f"/media/variant/{filename}",
        })
    return results


def _queue_position_unlocked(job_id: str) -> int:
    job = _jobs.get(job_id)
    if not job or job.get("status") != "queued":
        return 0
    try:
        return list(_queue).index(job_id) + 1
    except ValueError:
        return 0


def _refresh_queue_labels_unlocked() -> None:
    for idx, queued_id in enumerate(_queue, start=1):
        job = _jobs.get(queued_id)
        if job and job.get("status") == "queued":
            job["queue_position"] = idx
            job["label"] = f"Đang xếp hàng chờ GPU (vị trí #{idx})..."


def _worker_loop() -> None:
    while True:
        with _jobs_cond:
            while not _queue:
                _jobs_cond.wait()
            job_id = _queue.popleft()
            job = _jobs.get(job_id)
            if job is None:
                continue
            heritage_id = job["heritage_id"]
            job.update(
                status="running",
                queue_position=0,
                progress=10,
                label="Đang chuẩn bị hoa văn từ hiện vật...",
            )
            _refresh_queue_labels_unlocked()

        delay = _get_delay()
        step_sleep = max(0.05, delay / 4.0)
        for step_idx, (pct, msg) in enumerate((
            (25, "Đang tạo thiết kế 1/4..."),
            (50, "Đang tạo thiết kế 2/4..."),
            (75, "Đang tạo thiết kế 3/4..."),
            (92, "Đang hoàn thiện thiết kế 4/4..."),
        ), start=1):
            time.sleep(step_sleep)
            if _is_failing():
                with _jobs_cond:
                    _jobs[job_id].update(status="failed", queue_position=0, label="Mock backend lỗi giữa chừng (FAIL=1).")
                break
            with _jobs_cond:
                if job_id in _jobs:
                    _jobs[job_id].update(status="running", queue_position=0, progress=pct, label=msg)
        else:
            variants = _load_csv_variants(heritage_id)
            with _jobs_cond:
                _jobs[job_id].update(
                    status="completed",
                    queue_position=0,
                    progress=100,
                    label="Đã tạo xong bốn thiết kế.",
                    gpu=os.getenv("BACKEND_NAME", "NVIDIA T4 16GB (Mock)"),
                    variants=variants,
                )


def _ensure_worker_started_unlocked() -> None:
    global _worker_started
    if not _worker_started:
        threading.Thread(target=_worker_loop, daemon=True, name="mock-gpu-fifo-worker").start()
        _worker_started = True


@app.get("/health")
def health() -> dict:
    global _health_calls
    _health_calls += 1
    warmup_Needed = int(os.getenv("WARMUP_CALLS", "0") or "0")
    if _health_calls <= warmup_Needed:
        raise HTTPException(status_code=503, detail="Space đang khởi động (warming up)...")
    _check_fail_or_hang()
    return {"status": "ok", "generation_available": True}


@app.get("/passports")
def passports() -> list[dict]:
    _check_fail_or_hang()
    return store.list_passports()


@app.get("/experiments")
def experiments() -> list[dict]:
    _check_fail_or_hang()
    return store.list_experiments()


@app.get("/media/run/{run_id}/{filename}")
def run_image(run_id: str, filename: str) -> FileResponse:
    _check_fail_or_hang()
    file = store.safe_run_file(run_id, filename)
    if file is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh.")
    return FileResponse(file)


@app.get("/media/artifact")
def artifact_image(path: str = Query(max_length=200)) -> FileResponse:
    _check_fail_or_hang()
    relative = Path(path)
    if relative.is_absolute() or ".." in relative.parts or relative.suffix.lower() != ".png":
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh.")
    if not relative.as_posix().startswith("outputs/runs/"):
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh.")
    file = (PROJECT_ROOT / relative).resolve()
    if PROJECT_ROOT.resolve() not in file.parents or not file.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh.")
    return FileResponse(file)


@app.get("/heritage")
def list_heritage() -> list[dict]:
    return ui_items()


@app.get("/heritage/{heritage_id}")
def get_heritage(heritage_id: str) -> dict:
    item = next((item for item in ui_items() if item["id"] == heritage_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hiện vật.")
    return item


@app.get("/media/heritage/{heritage_id}")
def heritage_image(heritage_id: str) -> FileResponse:
    item = next((item for item in heritage_items() if item["heritage_id"] == heritage_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh hiện vật.")
    path = PROJECT_ROOT / item["image_path"]
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy file ảnh hiện vật.")
    return FileResponse(path)


@app.post("/generate", status_code=202, dependencies=[Depends(verify_auth)])
def generate_designs(request: GenerateRequest) -> dict:
    _check_fail_or_hang()
    if not any(item["heritage_id"] == request.heritage_id for item in heritage_items()):
        raise HTTPException(status_code=404, detail="Không tìm thấy hiện vật.")

    job_id = uuid.uuid4().hex
    with _jobs_cond:
        _ensure_worker_started_unlocked()
        _queue.append(job_id)
        queue_pos = len(_queue)
        _jobs[job_id] = {
            "job_id": job_id,
            "heritage_id": request.heritage_id,
            "status": "queued",
            "queue_position": queue_pos,
            "progress": 0,
            "label": f"Đang xếp hàng chờ GPU (vị trí #{queue_pos})...",
        }
        _jobs_cond.notify()

    return {
        "job_id": job_id,
        "status_url": f"/generate/{job_id}",
        "seed": request.seed,
        "queue_position": queue_pos,
    }


@app.get("/generate/{job_id}", dependencies=[Depends(verify_auth)])
def generate_status(job_id: str) -> dict:
    _check_fail_or_hang()
    with _jobs_cond:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy job.")
        response = dict(job)
        response["queue_position"] = _queue_position_unlocked(job_id)
        return response


@app.post("/audit", status_code=202, dependencies=[Depends(verify_auth)])
def record_audit_event(request: AuditRequest) -> dict:
    is_recorded = append_audit_event(PROJECT_ROOT, request.model_dump(exclude_none=True))
    return {"status": "recorded" if is_recorded else "unavailable"}


@app.get("/media/variant/{filename}")
def variant_image(filename: str) -> FileResponse:
    if "/" in filename or "\\" in filename or Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Tên file không hợp lệ.")
    variants_dir = (get_output_dir(PROJECT_ROOT) / "variants").resolve()
    path = (variants_dir / filename).resolve()
    if path.parent != variants_dir or not path.is_file():
        fallback = (WEB_VARIANTS_DIR / filename).resolve()
        if fallback.parent == WEB_VARIANTS_DIR.resolve() and fallback.is_file():
            return FileResponse(fallback)
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh thiết kế.")
    return FileResponse(path)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="127.0.0.1", port=port)
