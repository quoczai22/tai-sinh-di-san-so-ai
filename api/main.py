from __future__ import annotations

from collections import deque
from pathlib import Path
import os
import threading
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.audit import append_audit_event, get_output_dir
from streamlit_ui.heritage_data import load_heritage_metadata


PROJECT_ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="Tái sinh Di sản Số API", version="0.2.0")
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "WEB_UI_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:3000,http://localhost:3000"
    ).split(",")
    if origin.strip()
]
origin_regex = os.getenv("WEB_UI_ORIGIN_REGEX", r"https://.*\.vercel\.app")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=origin_regex,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

_jobs: dict[str, dict] = {}
_queue: deque[str] = deque()
_jobs_cond = threading.Condition()
_worker_started = False


class GenerateRequest(BaseModel):
    heritage_id: str


class AuditRequest(BaseModel):
    step: int
    event: str
    heritage_id: str | None = None
    variant_name: str | None = None
    backend: str | None = None
    wait_ms: int | None = None
    failover: bool | None = None


def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    expected = os.getenv("DH_API_KEY", "").strip()
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="API key không hợp lệ hoặc bị thiếu.")


def heritage_items() -> list[dict]:
    return load_heritage_metadata(PROJECT_ROOT)


def ui_items() -> list[dict]:
    result = []
    for item in heritage_items():
        result.append({
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
        })
    return result


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
    from generation.streamlit_runner import generate_design_set

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
                progress=2,
                label="Đang khởi chạy pipeline trên GPU...",
            )
            _refresh_queue_labels_unlocked()

        def progress(value: int, label: str) -> None:
            with _jobs_cond:
                if job_id in _jobs:
                    _jobs[job_id].update(
                        status="running",
                        queue_position=0,
                        progress=value,
                        label=label,
                    )

        try:
            variants_out_dir = get_output_dir(PROJECT_ROOT) / "variants"
            variants = generate_design_set(heritage_id, progress, output_dir=variants_out_dir)
            gpu_name = variants[0].get("gpu") if variants else None
            with _jobs_cond:
                _jobs[job_id].update(
                    status="completed",
                    queue_position=0,
                    progress=100,
                    label="Đã tạo xong bốn thiết kế.",
                    gpu=gpu_name,
                    variants=[
                        {
                            **variant,
                            "image_url": f"/media/variant/{Path(variant['design_path']).name}",
                        }
                        for variant in variants
                    ],
                )
            append_audit_event(PROJECT_ROOT, {
                "step": 3,
                "event": "generation_completed",
                "heritage_id": heritage_id,
                "job_id": job_id,
            })
        except Exception as exc:
            with _jobs_cond:
                _jobs[job_id].update(
                    status="failed",
                    queue_position=0,
                    label=str(exc),
                )
            append_audit_event(PROJECT_ROOT, {
                "step": 3,
                "event": "generation_failed",
                "heritage_id": heritage_id,
                "job_id": job_id,
                "error": str(exc),
            })


def _ensure_worker_started_unlocked() -> None:
    global _worker_started
    if not _worker_started:
        threading.Thread(target=_worker_loop, daemon=True, name="gpu-fifo-worker").start()
        _worker_started = True


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/health/gpu")
def health_gpu() -> dict:
    try:
        import torch  # noqa: PLC0415

        cuda_available = torch.cuda.is_available()
        device = torch.cuda.get_device_name(0) if cuda_available else "cpu"
        return {"status": "ok", "cuda": cuda_available, "device": device}
    except Exception as exc:
        return {"status": "error", "cuda": False, "device": "cpu", "detail": str(exc)}


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


@app.post("/generate", status_code=202, dependencies=[Depends(verify_api_key)])
def generate_designs(request: GenerateRequest) -> dict:
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

    append_audit_event(PROJECT_ROOT, {
        "step": 3,
        "event": "generation_started",
        "heritage_id": request.heritage_id,
        "job_id": job_id,
        "queue_position": queue_pos,
    })
    return {
        "job_id": job_id,
        "status_url": f"/generate/{job_id}",
        "queue_position": queue_pos,
    }


@app.post("/audit", status_code=202, dependencies=[Depends(verify_api_key)])
def record_audit_event(request: AuditRequest) -> dict:
    if request.step not in {1, 2, 3, 4}:
        raise HTTPException(status_code=422, detail="Bước audit phải từ 1 đến 4.")
    is_recorded = append_audit_event(PROJECT_ROOT, request.model_dump(exclude_none=True))
    return {"status": "recorded" if is_recorded else "unavailable"}


@app.get("/generate/{job_id}", dependencies=[Depends(verify_api_key)])
def generate_status(job_id: str) -> dict:
    with _jobs_cond:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy job.")
        response = dict(job)
        response["queue_position"] = _queue_position_unlocked(job_id)
        return response


@app.get("/media/variant/{filename}")
def variant_image(filename: str) -> FileResponse:
    if "/" in filename or "\\" in filename or Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Tên file không hợp lệ.")
    variants_dir = (get_output_dir(PROJECT_ROOT) / "variants").resolve()
    path = (variants_dir / filename).resolve()
    if path.parent != variants_dir or not path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh thiết kế.")
    return FileResponse(path)
