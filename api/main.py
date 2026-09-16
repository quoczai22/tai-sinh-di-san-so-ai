from __future__ import annotations

from pathlib import Path
import os
import threading
import uuid

import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from streamlit_ui.heritage_data import load_heritage_metadata


PROJECT_ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="Tái sinh Di sản Số API", version="0.1.0")
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "WEB_UI_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()
_active_job_id: str | None = None


class GenerateRequest(BaseModel):
    heritage_id: str


def heritage_items() -> list[dict]:
    return load_heritage_metadata(PROJECT_ROOT)


def ui_items() -> list[dict]:
    result = []
    for item in heritage_items():
        result.append({
            "id": item["heritage_id"],
            "name": item["name"],
            "dynasty": "Di sản Bát Tràng",
            "conditioningMode": item["conditioning_mode"],
            "image": f"/media/heritage/{item['heritage_id']}",
            "colors": [],
            "colorNames": [],
            "licenseNote": item["license_note"],
            "variantImageBase": f"./assets/images/variants/{item['heritage_id']}_V",
        })
    return result


@app.get("/health")
def health() -> dict:
    device = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
    return {"status": "ok", "cuda": torch.cuda.is_available(), "device": device}


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
    return FileResponse(path)


@app.post("/generate", status_code=202)
def generate_designs(request: GenerateRequest) -> dict:
    from generation.streamlit_runner import generate_design_set
    global _active_job_id

    if not any(item["heritage_id"] == request.heritage_id for item in heritage_items()):
        raise HTTPException(status_code=404, detail="Không tìm thấy hiện vật.")
    with _jobs_lock:
        if _active_job_id is not None and _jobs.get(_active_job_id, {}).get("status") in {"queued", "running"}:
            raise HTTPException(status_code=409, detail="Đang có một job GPU khác chạy. Vui lòng chờ job hiện tại hoàn tất.")
        job_id = uuid.uuid4().hex
        _jobs[job_id] = {"status": "queued", "progress": 0, "label": "Đang xếp hàng..."}
        _active_job_id = job_id

    def run() -> None:
        global _active_job_id
        def progress(value: int, label: str) -> None:
            with _jobs_lock:
                _jobs[job_id].update(status="running", progress=value, label=label)

        try:
            variants = generate_design_set(request.heritage_id, progress)
            with _jobs_lock:
                _jobs[job_id].update(
                    status="completed",
                    progress=100,
                    label="Đã tạo xong bốn thiết kế.",
                    variants=[
                        {
                            **variant,
                            "image_url": f"/media/variant/{Path(variant['design_path']).name}",
                        }
                        for variant in variants
                    ],
                )
        except Exception as exc:
            with _jobs_lock:
                _jobs[job_id].update(status="failed", label=str(exc))
        finally:
            with _jobs_lock:
                _active_job_id = None

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id, "status_url": f"/generate/{job_id}"}


@app.get("/generate/{job_id}")
def generate_status(job_id: str) -> dict:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy job.")
        return dict(job)


@app.get("/media/variant/{filename}")
def variant_image(filename: str) -> FileResponse:
    path = PROJECT_ROOT / "outputs" / "variants" / filename
    if not path.is_file() or path.parent != (PROJECT_ROOT / "outputs" / "variants"):
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh thiết kế.")
    return FileResponse(path)
