from __future__ import annotations

import base64
import binascii
import csv
import io
import logging
import os
import threading
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field, field_validator

from api import store
from api.audit import AUDIT_EVENTS, append_audit_event
from provenance import passport as P
from provenance.registry import (all_items, assess_selection, completeness, get_item,
                                 load_selection_config, rights_gate)
from streamlit_ui.heritage_data import load_heritage_metadata

PROJECT_ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger("tsds.api")


def _enforce_api_key_config() -> None:
    """Fail-closed khi deploy: DH_REQUIRE_API_KEY=1 mà DH_API_KEY trống thì không khởi động.

    Chạy local không đặt DH_REQUIRE_API_KEY thì giữ hành vi cũ (bỏ qua kiểm tra khoá).
    """
    required = os.getenv("DH_REQUIRE_API_KEY", "").strip().lower() in {"1", "true", "yes"}
    if required and not os.getenv("DH_API_KEY", "").strip():
        raise RuntimeError(
            "DH_REQUIRE_API_KEY=1 nhưng DH_API_KEY đang trống: từ chối khởi động để không mở "
            "GPU cho truy cập tự do. Hãy đặt secret DH_API_KEY (Modal: secret "
            "'tai-sinh-di-san-secret')."
        )


_enforce_api_key_config()

app = FastAPI(title="Tái sinh Di sản Số API", version="1.1.0")
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
    allow_headers=["Content-Type", "X-API-Key"],
)
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()
_active_job_id: str | None = None
_rate: dict[str, deque] = defaultdict(deque)
GENERATE_LIMIT_PER_HOUR = int(os.getenv("TSDS_GENERATE_PER_HOUR", "6"))
WRITE_KEY = os.getenv("TSDS_WRITE_KEY", "")
MAX_EDIT_BYTES = 8 * 1024 * 1024


# ------------------------------------------------------------------ helpers --

def require_write_key(x_api_key: str | None = Header(default=None)) -> None:
    """Khi đặt TSDS_WRITE_KEY, mọi thao tác GHI (thẩm định, chỉnh sửa, phê duyệt,
    xuất bản) phải gửi header X-API-Key. Không đặt = chế độ phát triển cục bộ."""
    if WRITE_KEY and x_api_key != WRITE_KEY:
        raise HTTPException(status_code=401, detail="Thiếu hoặc sai khoá ghi (X-API-Key).")


def verify_gpu_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """Bảo vệ các route chạm GPU (/generate, /generate/{job_id}) khi deploy.

    Đặt DH_API_KEY (Modal secret) thì phải gửi đúng X-API-Key — cổng Vercel giữ khoá ở phía
    server. Không đặt (chạy local) thì không kiểm tra, giữ hành vi của bản chung kết.
    """
    expected = os.getenv("DH_API_KEY", "").strip()
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="API key không hợp lệ hoặc bị thiếu.")


def rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    q = _rate[ip]
    now = time.time()
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= GENERATE_LIMIT_PER_HOUR:
        raise HTTPException(status_code=429, detail="Đã vượt giới hạn lượt sinh trong một giờ. Vui lòng thử lại sau.")
    q.append(now)


def heritage_items(include_retired: bool = False) -> list[dict]:
    return load_heritage_metadata(PROJECT_ROOT, include_retired=include_retired)


def ui_items(include_retired: bool = False) -> list[dict]:
    result = []
    for item in heritage_items(include_retired):
        prov = item.get("provenance") or {}
        demo_gate = rights_gate(item, "demo_display", PROJECT_ROOT)
        result.append({
            "id": item["heritage_id"],
            "code": item.get("code"),
            "name": item["name"],
            "status": item.get("status", "active"),
            "retiredReason": item.get("retired_reason"),
            "dynasty": prov.get("dating") or "Gốm Bát Tràng",
            "dating": prov.get("dating"),
            "datingSource": prov.get("dating_source"),
            "visualSummary": item.get("visual_summary"),
            "visualSummaryOrigin": item.get("visual_summary_origin"),
            "description": item.get("team_description", ""),
            "descriptionOrigin": prov.get("description_origin"),
            "descriptionNote": prov.get("description_note"),
            "conditioningMode": item["conditioning_mode"],
            "image": f"/media/heritage/{item['heritage_id']}",
            # Giữ các trường của API bản 09/2026 để giao diện bản 09/2026 (lưu ở archive/web_ui_2026-09) không vỡ.
            "colors": [],
            "colorNames": [],
            "variantImageBase": f"./assets/images/variants/{item['heritage_id']}_V",
            "licenseNote": item["license_note"],
            "provenance": {
                "sourceTitle": prov.get("source_title"), "sourceUrl": prov.get("source_url"),
                "holder": prov.get("holder"), "holderType": prov.get("holder_type"),
                "author": prov.get("author"), "rightsStatus": prov.get("rights_status"),
                "license": prov.get("license"), "attribution": prov.get("attribution"),
                "collectedOn": prov.get("collected_on"), "collectedBefore": prov.get("collected_before"),
                "dataVersion": prov.get("data_version"), "imageSize": prov.get("image_size"),
                "reviewFlags": prov.get("review_flags", []),
            },
            "completeness": completeness(item),
            "rightsGate": demo_gate.as_dict(),
        })
    return result


def _public_passport(p: dict) -> dict:
    return {**p, "timeline": P.timeline(p), "integrity": P.verify(p, PROJECT_ROOT)}


# ------------------------------------------------------------------- models --

class GenerateRequest(BaseModel):
    heritage_id: str = Field(min_length=1, max_length=120)
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)


class AuditRequest(BaseModel):
    step: int
    event: str = Field(max_length=40)
    heritage_id: str | None = Field(default=None, max_length=120)
    variant_name: str | None = Field(default=None, max_length=60)
    passport_id: str | None = Field(default=None, max_length=40)


class ReviewRequest(BaseModel):
    reviewer_id: str = Field(min_length=2, max_length=24, pattern=r"^[A-Za-z0-9_-]+$")
    reviewer_role: Literal["heritage_expert", "design_expert", "qc_officer"]
    consent_to_store_name: bool = False
    reviewer_name: str | None = Field(default=None, max_length=80)
    blind: bool = True
    scores: dict[str, int]
    decision: Literal["approve", "revise", "reject"]
    comment: str = Field(default="", max_length=2000)
    reviewed_version: int | None = None

    @field_validator("scores")
    @classmethod
    def _scores(cls, v: dict[str, int]) -> dict[str, int]:
        if not v or any(not (1 <= s <= 5) for s in v.values()):
            raise ValueError("Điểm phải từ 1 đến 5.")
        return v


class QcRequest(BaseModel):
    officer_id: str = Field(min_length=2, max_length=24, pattern=r"^[A-Za-z0-9_-]+$")
    decision: Literal["forward_to_expert", "return_for_repair"]
    note: str = Field(default="", max_length=1000)


class EditRequest(BaseModel):
    editor_id: str = Field(min_length=2, max_length=24, pattern=r"^[A-Za-z0-9_-]+$")
    editor_role: Literal["designer", "qc_officer"]
    description: str = Field(min_length=5, max_length=500)
    tool: str = Field(min_length=2, max_length=80)
    image_png_base64: str = Field(min_length=100)


# ------------------------------------------------------------------- routes --

@app.get("/health")
def health() -> dict:
    """Không chạm GPU khi torch chưa cài — /health dùng được cho giám sát (UptimeRobot)."""
    try:
        import torch                                             # noqa: PLC0415
        cuda = torch.cuda.is_available()
        device = torch.cuda.get_device_name(0) if cuda else "cpu"
    except ImportError:
        cuda, device = False, "torch-not-installed"
    return {"status": "ok", "cuda": cuda, "device": device, "version": app.version,
            "write_protection": bool(WRITE_KEY), "generation_available": cuda}


@app.get("/heritage")
def list_heritage(include_retired: bool = False) -> list[dict]:
    return ui_items(include_retired)


@app.get("/heritage/{heritage_id}")
def get_heritage(heritage_id: str) -> dict:
    item = next((item for item in ui_items(True) if item["id"] == heritage_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hiện vật.")
    return item


@app.get("/heritage/{heritage_id}/provenance")
def heritage_provenance(heritage_id: str) -> dict:
    item = get_item(heritage_id, PROJECT_ROOT)
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hiện vật.")
    return {"heritage_id": heritage_id, "provenance": item.get("provenance"),
            "completeness": completeness(item),
            "selection": assess_selection(item, PROJECT_ROOT),
            "selection_criteria": load_selection_config(PROJECT_ROOT)["criteria"],
            "rights": {a: rights_gate(item, a, PROJECT_ROOT).as_dict()
                       for a in ("experiment", "demo_display", "publish_public", "commercial_use")}}


@app.get("/media/heritage/{heritage_id}")
def heritage_image(heritage_id: str) -> FileResponse:
    item = next((item for item in heritage_items(True) if item["heritage_id"] == heritage_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh hiện vật.")
    # Ảnh hiển thị: ưu tiên ảnh đã tách nền (nền trong suốt) nếu có
    cut = PROJECT_ROOT / "data" / "heritage" / "cutouts" / f"{heritage_id}.png"
    return FileResponse(cut if cut.exists() else PROJECT_ROOT / item["image_path"])


@app.post("/generate", status_code=202, dependencies=[Depends(verify_gpu_api_key), Depends(rate_limit)])
def generate_designs(request: GenerateRequest) -> dict:
    global _active_job_id

    item = get_item(request.heritage_id, PROJECT_ROOT)
    if item is None or item.get("status", "active") != "active":
        raise HTTPException(status_code=404, detail="Không tìm thấy hiện vật đang hoạt động.")
    try:
        from generation.streamlit_runner import SEED, generate_design_set   # noqa: PLC0415
    except ImportError:
        raise HTTPException(status_code=503, detail="Máy chủ này chưa có môi trường sinh ảnh (PyTorch + GPU). "
                                                    "Giao diện đang hiển thị kết quả đã sinh sẵn.") from None
    seed = SEED if request.seed is None else request.seed
    with _jobs_lock:
        if _active_job_id is not None and _jobs.get(_active_job_id, {}).get("status") in {"queued", "running"}:
            raise HTTPException(status_code=409, detail="Đang có một job GPU khác chạy. Vui lòng chờ job hiện tại hoàn tất.")
        job_id = uuid.uuid4().hex
        _jobs[job_id] = {"status": "queued", "progress": 0, "label": "Đang xếp hàng...", "seed": seed}
        _active_job_id = job_id
    append_audit_event(PROJECT_ROOT, {"step": 3, "event": "generation_started",
                                      "heritage_id": request.heritage_id, "job_id": job_id, "seed": seed})

    def run() -> None:
        global _active_job_id

        def progress(value: int, label: str) -> None:
            with _jobs_lock:
                _jobs[job_id].update(status="running", progress=value, label=label)

        try:
            variants = generate_design_set(request.heritage_id, progress, seed=seed)
            for v in variants:
                if v.get("status") == "completed":
                    v["image_url"] = f"/media/run/{v['run_id']}/{Path(v['design_path']).name}"
            done = sum(1 for v in variants if v.get("status") == "completed")
            with _jobs_lock:
                _jobs[job_id].update(status="completed", progress=100, variants=variants,
                                     run_id=variants[0]["run_id"] if variants else None,
                                     label=f"Đã tạo xong {done}/{len(variants)} thiết kế.")
            append_audit_event(PROJECT_ROOT, {"step": 3, "event": "generation_completed",
                                              "heritage_id": request.heritage_id, "job_id": job_id})
        except Exception:                                          # noqa: BLE001
            log.exception("Job %s lỗi", job_id)
            with _jobs_lock:
                # Không trả chi tiết lỗi nội bộ cho client (đã ghi log máy chủ)
                _jobs[job_id].update(status="failed", label="Pipeline gặp lỗi. Đã ghi nhật ký máy chủ; vui lòng thử lại.")
            append_audit_event(PROJECT_ROOT, {"step": 3, "event": "generation_failed",
                                              "heritage_id": request.heritage_id, "job_id": job_id})
        finally:
            with _jobs_lock:
                _active_job_id = None

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id, "status_url": f"/generate/{job_id}", "seed": seed}


@app.post("/audit", status_code=202)
def record_audit_event(request: AuditRequest) -> dict:
    if request.step not in {1, 2, 3, 4, 5}:
        raise HTTPException(status_code=422, detail="Bước audit phải từ 1 đến 5.")
    if request.event not in AUDIT_EVENTS:
        raise HTTPException(status_code=422, detail="Sự kiện audit không thuộc danh mục cho phép.")
    is_recorded = append_audit_event(PROJECT_ROOT, request.model_dump(exclude_none=True))
    return {"status": "recorded" if is_recorded else "unavailable"}


@app.get("/generate/{job_id}", dependencies=[Depends(verify_gpu_api_key)])
def generate_status(job_id: str) -> dict:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy job.")
        return dict(job)


@app.get("/media/run/{run_id}/{filename}")
def run_image(run_id: str, filename: str) -> FileResponse:
    path = store.safe_run_file(run_id, filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp của lần chạy.")
    return FileResponse(path)


@app.get("/media/artifact")
def artifact_image(path: str = Query(max_length=200)) -> FileResponse:
    """Phục vụ tệp ảnh đã đăng ký trong một Passport (chống duyệt thư mục tuỳ ý)."""
    rel = Path(path)
    if rel.is_absolute() or ".." in rel.parts or rel.suffix.lower() not in (".png", ".jpg", ".jpeg"):
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp.")
    allowed_roots = ("outputs/", "data/heritage/", "web_ui/assets/images/")
    if not any(rel.as_posix().startswith(r) for r in allowed_roots):
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp.")
    full = (PROJECT_ROOT / rel).resolve()
    if PROJECT_ROOT.resolve() not in full.parents or not full.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp.")
    return FileResponse(full)


# ------------------------------------------------------ runs & passports --

@app.get("/runs")
def runs() -> list[dict]:
    return store.list_runs()


@app.get("/runs/{run_id}")
def run_detail(run_id: str) -> dict:
    m = store.get_run(run_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lần chạy.")
    return m


@app.get("/passports")
def passports(heritage_id: str | None = None) -> list[dict]:
    items = store.list_passports()
    return [p for p in items if heritage_id is None or p["heritage_id"] == heritage_id]


@app.get("/passports/{passport_id}")
def passport_detail(passport_id: str) -> dict:
    p = store.get_passport(passport_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Design Passport.")
    return _public_passport(p)


@app.post("/passports/{passport_id}/qc", dependencies=[Depends(require_write_key)])
def qc_decision(passport_id: str, request: QcRequest) -> dict:
    def apply(p: dict):
        if p["approval"]["status"] not in ("qa_warning", "qa_failed"):
            raise HTTPException(status_code=409, detail="Thiết kế không ở trạng thái chờ QC.")
        if request.decision == "forward_to_expert":
            if p["approval"]["status"] == "qa_failed":
                raise HTTPException(status_code=409, detail="Thiết kế FAIL không được chuyển chuyên gia; phải sửa hoặc sinh lại.")
            P.set_approval(p, "pending_expert_review", by=request.officer_id,
                           reason=request.note or "QC chấp nhận cảnh báo, chuyển chuyên gia.")
        else:
            P.set_approval(p, "qa_failed", by=request.officer_id, reason=request.note or "QC trả về để sửa.")
        return p["approval"]
    result = store.mutate_passport(passport_id, apply)
    if result is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Design Passport.")
    append_audit_event(PROJECT_ROOT, {"step": 5, "event": "qc_decision", "passport_id": passport_id})
    return result


@app.post("/passports/{passport_id}/reviews", dependencies=[Depends(require_write_key)])
def submit_review(passport_id: str, request: ReviewRequest) -> dict:
    import json                                                  # noqa: PLC0415
    rubric = json.loads((PROJECT_ROOT / "config" / "expert_rubric.json").read_text(encoding="utf-8"))
    known = {c["key"] for c in rubric["criteria"]}
    unknown = set(request.scores) - known
    if unknown:
        raise HTTPException(status_code=422, detail=f"Tiêu chí không có trong bộ tiêu chí: {sorted(unknown)}")

    def apply(p: dict):
        if p["approval"]["status"] not in ("pending_expert_review", "revision_requested"):
            raise HTTPException(status_code=409, detail="Thiết kế chưa qua cổng chất lượng/QC nên chưa được thẩm định.")
        review = {"review_id": f"RV{len(p['reviews']) + 1}", "at": P.now_iso(),
                  "reviewer_id": request.reviewer_id, "reviewer_role": request.reviewer_role,
                  "reviewer_name": request.reviewer_name if request.consent_to_store_name else None,
                  "blind": request.blind, "scores": request.scores, "decision": request.decision,
                  "comment": request.comment,
                  "reviewed_version": request.reviewed_version or (p["versions"][-1]["version"] if p["versions"] else None),
                  "rubric_version": rubric["version"]}
        low = [k for k, v in request.scores.items() if v < 3]
        culture = request.scores.get("cultural_appropriateness")
        review["rule_conflict"] = (request.decision == "approve" and (bool(low) or (culture is not None and culture < 4)))
        P.record_review(p, review)
        status = {"approve": "approved", "revise": "revision_requested", "reject": "rejected"}[request.decision]
        P.set_approval(p, status, by=request.reviewer_id, reason=request.comment or None)
        return review
    result = store.mutate_passport(passport_id, apply)
    if result is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Design Passport.")
    append_audit_event(PROJECT_ROOT, {"step": 5, "event": "expert_review_submitted", "passport_id": passport_id})
    return result


@app.post("/passports/{passport_id}/edits", dependencies=[Depends(require_write_key)])
def submit_edit(passport_id: str, request: EditRequest) -> dict:
    from PIL import Image                                         # noqa: PLC0415
    try:
        raw = base64.b64decode(request.image_png_base64.split(",")[-1], validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=422, detail="Ảnh không phải base64 hợp lệ.") from None
    if len(raw) > MAX_EDIT_BYTES:
        raise HTTPException(status_code=413, detail="Ảnh vượt 8 MB.")
    try:
        with Image.open(io.BytesIO(raw)) as im:
            im.verify()
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:                                             # noqa: BLE001
        raise HTTPException(status_code=422, detail="Tệp không phải ảnh hợp lệ.") from None

    def apply(p: dict):
        n = len(p["versions"]) + 1
        out = store.EDITS / passport_id / f"v{n}_human_edit.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out)
        art = P.file_record(out, "human_edit", PROJECT_ROOT)
        edit = P.record_edit(p, editor_id=request.editor_id, editor_role=request.editor_role,
                             description=request.description, tool=request.tool, artifact=art)
        # Bản sửa quay lại cổng G3 trước khi chuyên gia thẩm định lại (BPMN TO-BE).
        from quality.assess import approval_from_assessment, assess_edit   # noqa: PLC0415
        assessment = assess_edit(p, out, PROJECT_ROOT)
        if assessment is None:
            P.set_approval(p, "qa_warning", by="quality_gate", actor_type="system",
                           reason="Không đủ dữ liệu để chạy G3 cho bản sửa — QC Officer xem thủ công.")
            edit["quality_decision"] = None
        else:
            P.add_step(p, step="quality_gate", label=f"Cổng G3 cho bản sửa: {assessment['G3_final']['decision']}",
                       actor_type="system", actor="quality/gate.py", tool=assessment["config_version"])
            P.record_quality(p, {k: assessment[k] for k in ("G2_pattern", "G3_final", "overall")},
                             assessment["config_version"])
            p["quality"]["evaluated_version"] = p["versions"][-1]["version"]
            status, reason = approval_from_assessment(assessment)
            P.set_approval(p, status, by="quality_gate", actor_type="system", reason=reason)
            edit["quality_decision"] = assessment["overall"]["decision"]
        edit["approval_status"] = p["approval"]["status"]
        return edit
    result = store.mutate_passport(passport_id, apply)
    if result is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Design Passport.")
    append_audit_event(PROJECT_ROOT, {"step": 5, "event": "manual_edit_recorded", "passport_id": passport_id})
    return result


@app.post("/passports/{passport_id}/publish", dependencies=[Depends(require_write_key)])
def publish(passport_id: str) -> dict:
    p = store.get_passport(passport_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Design Passport.")
    if p["approval"]["status"] != "approved":
        raise HTTPException(status_code=409, detail="Chỉ xuất bản thiết kế đã được chuyên gia phê duyệt.")
    item = get_item(p["heritage"]["heritage_id"], PROJECT_ROOT)
    gate = rights_gate(item, "publish_public", PROJECT_ROOT)
    if not gate.allowed:
        raise HTTPException(status_code=403, detail=gate.reason)

    def apply(pp: dict):
        P.append_event(pp, "published", "system", "system", {"rights": gate.as_dict()})
        pp["published_at"] = P.now_iso()
        return {"published_at": pp["published_at"], "rights": gate.as_dict()}
    return store.mutate_passport(passport_id, apply)


@app.get("/passports/{passport_id}/export")
def export_design(passport_id: str, version: int | None = None) -> Response:
    """Xuất ảnh thiết kế KÈM nhãn AI nhìn thấy được + siêu dữ liệu PNG."""
    from PIL import Image                                         # noqa: PLC0415
    from provenance.labeling import label_image                   # noqa: PLC0415
    p = store.get_passport(passport_id)
    if p is None or not p["versions"]:
        raise HTTPException(status_code=404, detail="Không tìm thấy Design Passport.")
    v = p["versions"][-1] if version is None else next((x for x in p["versions"] if x["version"] == version), None)
    if v is None:
        raise HTTPException(status_code=404, detail="Không có phiên bản này.")
    item = get_item(p["heritage"]["heritage_id"], PROJECT_ROOT)
    gate = rights_gate(item, "demo_display", PROJECT_ROOT)
    with Image.open(PROJECT_ROOT / v["path"]) as im:
        data, _ = label_image(im, passport_id=passport_id, design_sha256=v["sha256"],
                              heritage_name=p["heritage"]["name"], attribution=p["heritage"].get("attribution"),
                              rights_warning=gate.level != "ok")
    append_audit_event(PROJECT_ROOT, {"step": 5, "event": "design_exported", "passport_id": passport_id})
    return Response(content=data, media_type="image/png",
                    headers={"Content-Disposition": f'attachment; filename="{passport_id}_v{v["version"]}.png"'})


# --------------------------------------------------- quality & experiments --

@app.get("/quality/designs")
def quality_designs() -> list[dict]:
    return store.quality_rows()


@app.get("/experiments")
def experiments() -> list[dict]:
    return store.list_experiments()


@app.get("/provenance/catalog")
def provenance_catalog() -> list[dict]:
    out = []
    for item in all_items(PROJECT_ROOT):
        prov = item.get("provenance") or {}
        out.append({"heritage_id": item["heritage_id"], "code": item.get("code"), "name": item["name"],
                    "status": item.get("status", "active"), "source_url": prov.get("source_url"),
                    "holder": prov.get("holder"), "rights_status": prov.get("rights_status"),
                    "license": prov.get("license"), "attribution": prov.get("attribution"),
                    "completeness": completeness(item),
                    "publish_gate": rights_gate(item, "publish_public", PROJECT_ROOT).as_dict()})
    return out
