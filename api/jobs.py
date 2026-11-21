"""Persist generation receipts so a returning browser can recover its result."""
from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path

from api.audit import get_output_dir

JOB_ID = re.compile(r"[0-9a-f]{32}")


def _path(project_root: Path, job_id: str) -> Path | None:
    if not JOB_ID.fullmatch(job_id):
        return None
    return get_output_dir(project_root) / "jobs" / f"{job_id}.json"


def save(project_root: Path, job_id: str, state: dict) -> None:
    path = _path(project_root, job_id)
    if path is None:
        raise ValueError("Invalid job ID")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{job_id}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(state, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load(project_root: Path, job_id: str) -> dict | None:
    path = _path(project_root, job_id)
    if path is None or not path.is_file():
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if state.get("status") in {"queued", "running"}:
        return {**state, "status": "failed", "queue_position": 0,
                "label": "Lượt tạo ảnh bị gián đoạn khi máy chủ khởi động lại. Vui lòng tạo lại."}
    return state
