# -*- coding: utf-8 -*-
"""Design Passport — hồ sơ truy xuất nguồn gốc của MỘT thiết kế.

Một mã định danh đi suốt chuỗi (mượn nguyên tắc của quy trình mua hàng):
    heritage_id → run_id → design_id → passport_id → version
Mọi tệp trong chuỗi được băm SHA-256 đầy đủ. Mọi sự kiện (sinh ảnh, đo chất
lượng, sửa thủ công, thẩm định, phê duyệt, xuất bản) được ghi vào `ledger` theo
chuỗi băm: mỗi bản ghi chứa băm của bản ghi trước, nên sửa lén một sự kiện cũ
sẽ làm `verify()` báo sai ở đúng vị trí đó.

Phân định AI / hệ thống / con người là trường bắt buộc của mỗi bước:
    actor_type ∈ {"ai", "system", "human"}
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .hashing import sha256_file, sha256_json

SCHEMA = "design-passport/1.0"
from core.paths import ROOT
ACTOR_TYPES = {"ai": "AI hỗ trợ", "system": "Hệ thống (tất định)", "human": "Con người"}
APPROVAL_STATES = {
    "draft": "Đang tạo",
    "qa_failed": "Không đạt cổng chất lượng — chờ sửa/sinh lại",
    "qa_warning": "Có cảnh báo — chờ QC xem xét",
    "pending_expert_review": "Chờ chuyên gia thẩm định",
    "revision_requested": "Chuyên gia yêu cầu chỉnh sửa",
    "approved": "Đã phê duyệt",
    "rejected": "Bị loại",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def passport_id_for(code: str, run_stamp: str, variant_index: int) -> str:
    return f"DP-{code}-{run_stamp}-V{variant_index}"


def file_record(path: Path, role: str, root: Path = ROOT, **extra) -> dict:
    path = Path(path)
    rel = path.relative_to(root).as_posix() if path.is_absolute() and root in path.parents else str(path)
    real = path if path.is_absolute() else root / path
    rec = {"role": role, "path": rel, "sha256": sha256_file(real), "bytes": real.stat().st_size}
    try:
        from PIL import Image                                   # noqa: PLC0415
        with Image.open(real) as im:
            rec["size"] = list(im.size)
    except Exception:                                           # noqa: BLE001
        pass
    rec.update(extra)
    return rec


def new_passport(*, passport_id: str, design_id: str, run_id: str, heritage: dict,
                 created_at: str | None = None) -> dict:
    prov = heritage.get("provenance") or {}
    return {
        "schema": SCHEMA,
        "passport_id": passport_id,
        "design_id": design_id,
        "run_id": run_id,
        "created_at": created_at or now_iso(),
        "heritage": {
            "heritage_id": heritage["heritage_id"], "code": heritage.get("code"),
            "name": heritage["name"], "status": heritage.get("status", "active"),
            "source_title": prov.get("source_title"), "source_url": prov.get("source_url"),
            "holder": prov.get("holder"), "author": prov.get("author"),
            "rights_status": prov.get("rights_status"), "license": prov.get("license"),
            "attribution": prov.get("attribution"), "dating": prov.get("dating"),
            "registry_data_version": prov.get("data_version"),
            "source_image_sha256": prov.get("image_sha256"),
        },
        "artifacts": [],
        "generation": {},
        "process_steps": [],
        "quality": {},
        "versions": [],
        "edits": [],
        "reviews": [],
        "approval": {"status": "draft", "label": APPROVAL_STATES["draft"], "decided_by": None,
                     "decided_at": None, "reason": None},
        "ai_disclosure": {"label": "Thiết kế được tạo với sự hỗ trợ của AI", "ai_steps": [], "human_steps": [],
                          "system_steps": []},
        "ledger": [],
    }


def append_event(passport: dict, event: str, actor: str, actor_type: str,
                  payload: dict | None = None, at: str | None = None) -> dict:
    if actor_type not in ACTOR_TYPES:
        raise ValueError(f"actor_type không hợp lệ: {actor_type}")
    ledger = passport["ledger"]
    prev = ledger[-1]["entry_hash"] if ledger else "0" * 64
    body = {"seq": len(ledger) + 1, "at": at or now_iso(), "event": event, "actor": actor,
            "actor_type": actor_type, "payload_hash": sha256_json(payload or {}), "prev_hash": prev}
    entry = {**body, "payload": payload or {}, "entry_hash": sha256_json(body)}
    ledger.append(entry)
    return entry


def add_step(passport: dict, *, step: str, label: str, actor_type: str, actor: str,
             tool: str | None = None, at: str | None = None, inputs: list[str] | None = None,
             outputs: list[str] | None = None, note: str | None = None) -> None:
    rec = {"step": step, "label": label, "actor_type": actor_type, "actor": actor, "tool": tool,
           "at": at, "inputs": inputs or [], "outputs": outputs or [], "note": note}
    passport["process_steps"].append(rec)
    key = {"ai": "ai_steps", "human": "human_steps", "system": "system_steps"}[actor_type]
    passport["ai_disclosure"][key].append(label)
    append_event(passport, f"step:{step}", actor, actor_type,
                 {"label": label, "tool": tool, "inputs": inputs or [], "outputs": outputs or []}, at=at)


def add_version(passport: dict, *, kind: str, artifact: dict, created_by: str, actor_type: str,
                note: str = "", at: str | None = None, ai_assisted: bool = True) -> dict:
    parent = passport["versions"][-1]["version"] if passport["versions"] else None
    version = {"version": len(passport["versions"]) + 1, "kind": kind, "path": artifact["path"],
               "sha256": artifact["sha256"], "parent_version": parent,
               "parent_sha256": passport["versions"][-1]["sha256"] if passport["versions"] else None,
               "created_at": at or now_iso(), "created_by": created_by, "actor_type": actor_type,
               "ai_assisted": ai_assisted, "note": note}
    passport["versions"].append(version)
    append_event(passport, f"version:{kind}", created_by, actor_type,
                 {"version": version["version"], "sha256": artifact["sha256"], "parent": parent}, at=at)
    return version


def record_edit(passport: dict, *, editor_id: str, editor_role: str, description: str, tool: str,
                artifact: dict, at: str | None = None) -> dict:
    """Ghi một lần CHỈNH SỬA THỦ CÔNG: ai, lúc nào, sửa gì, bằng công cụ gì, tệp
    trước/sau (băm). Bản sửa thành một phiên bản mới; phiên bản cũ giữ nguyên."""
    at = at or now_iso()
    base = passport["versions"][-1] if passport["versions"] else None
    edit = {"edit_id": f"E{len(passport['edits']) + 1}", "at": at, "editor_id": editor_id,
            "editor_role": editor_role, "description": description, "tool": tool,
            "before_sha256": base["sha256"] if base else None, "after_sha256": artifact["sha256"],
            "after_path": artifact["path"]}
    passport["edits"].append(edit)
    passport["artifacts"].append(artifact)
    add_version(passport, kind="human_edit", artifact=artifact, created_by=editor_id, actor_type="human",
                note=description, at=at, ai_assisted=True)
    add_step(passport, step="manual_edit", label=f"Chỉnh sửa thủ công: {description}", actor_type="human",
             actor=f"{editor_id} ({editor_role})", tool=tool, at=at,
             inputs=[edit["before_sha256"]] if edit["before_sha256"] else [], outputs=[artifact["sha256"]])
    set_approval(passport, "pending_expert_review", by="system",
                 reason="Có phiên bản mới sau chỉnh sửa thủ công — phải qua cổng chất lượng và thẩm định lại.",
                 actor_type="system", at=at)
    return edit


def record_quality(passport: dict, gate_result: dict, config_version: str, at: str | None = None) -> None:
    passport["quality"] = {**gate_result, "config_version": config_version, "evaluated_at": at or now_iso()}
    append_event(passport, "quality_gate", "quality_gate", "system",
                 {"decision": gate_result.get("overall", {}).get("decision"), "config_version": config_version}, at=at)


def record_review(passport: dict, review: dict) -> None:
    passport["reviews"].append(review)
    append_event(passport, "expert_review", review["reviewer_id"], "human",
                 {"decision": review["decision"], "scores": review.get("scores", {})}, at=review.get("at"))


def set_approval(passport: dict, status: str, *, by: str, reason: str | None = None,
                 actor_type: str = "human", at: str | None = None) -> None:
    if status not in APPROVAL_STATES:
        raise ValueError(f"Trạng thái phê duyệt không hợp lệ: {status}")
    at = at or now_iso()
    passport["approval"] = {"status": status, "label": APPROVAL_STATES[status], "decided_by": by,
                            "decided_at": at, "reason": reason}
    append_event(passport, f"approval:{status}", by, actor_type, {"reason": reason}, at=at)


def verify(passport: dict, root: Path = ROOT, check_files: bool = True) -> dict:
    """Kiểm tra toàn vẹn: chuỗi băm của ledger + băm tệp trên đĩa."""
    problems = []
    prev = "0" * 64
    for entry in passport["ledger"]:
        body = {k: entry[k] for k in ("seq", "at", "event", "actor", "actor_type", "payload_hash", "prev_hash")}
        if entry["prev_hash"] != prev:
            problems.append(f"ledger #{entry['seq']}: prev_hash không khớp")
        if sha256_json(entry["payload"]) != entry["payload_hash"]:
            problems.append(f"ledger #{entry['seq']}: payload đã bị sửa")
        if sha256_json(body) != entry["entry_hash"]:
            problems.append(f"ledger #{entry['seq']}: entry_hash không khớp")
        prev = entry["entry_hash"]
    # Các trường tóm tắt (trạng thái, phiên bản, phiếu) phải khớp với sổ cái; sửa
    # thẳng vào trường tóm tắt mà không qua sổ cái sẽ bị phát hiện ở đây.
    ledger = passport["ledger"]
    approvals = [e["event"].split(":", 1)[1] for e in ledger if e["event"].startswith("approval:")]
    current = (passport.get("approval") or {}).get("status")
    if approvals and current != approvals[-1]:
        problems.append(f"trạng thái phê duyệt '{current}' không khớp sự kiện cuối trong sổ cái '{approvals[-1]}'")
    v_events = [e["payload"] for e in ledger if e["event"].startswith("version:")]
    if len(v_events) != len(passport.get("versions", [])):
        problems.append("số phiên bản không khớp sổ cái")
    else:
        for v, ev in zip(passport["versions"], v_events):
            if v["sha256"] != ev.get("sha256") or v["version"] != ev.get("version"):
                problems.append(f"phiên bản v{v['version']} không khớp sổ cái")
    if sum(1 for e in ledger if e["event"] == "expert_review") != len(passport.get("reviews", [])):
        problems.append("số phiếu thẩm định không khớp sổ cái")
    files_checked = 0
    if check_files:
        for art in passport["artifacts"]:
            path = root / art["path"]
            if not path.exists():
                problems.append(f"thiếu tệp {art['path']}")
                continue
            files_checked += 1
            if sha256_file(path) != art["sha256"]:
                problems.append(f"băm không khớp: {art['path']}")
    return {"ok": not problems, "problems": problems, "ledger_entries": len(passport["ledger"]),
            "files_checked": files_checked}


def timeline(passport: dict) -> list[dict]:
    """Dòng thời gian cho UI: sắp theo thời điểm, giữ thứ tự ledger khi trùng."""
    items = []
    for entry in passport["ledger"]:
        items.append({"seq": entry["seq"], "at": entry["at"], "event": entry["event"],
                      "actor": entry["actor"], "actor_type": entry["actor_type"],
                      "label": entry["payload"].get("label") or entry["event"],
                      "entry_hash": entry["entry_hash"][:12]})
    return sorted(items, key=lambda x: (x["at"] or "", x["seq"]))


def save(passport: dict, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{passport['passport_id']}.json"
    path.write_text(json.dumps(passport, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
