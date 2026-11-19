from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path


_write_lock = threading.Lock()

# Danh mục sự kiện được phép ghi. Bản cũ nhận chuỗi tuỳ ý từ client và ghi thẳng
# vào tệp — nay chỉ nhận sự kiện trong danh mục, mỗi trường bị giới hạn độ dài ở
# tầng API (pydantic). Nhật ký không chứa IP hay định danh người dùng.
AUDIT_EVENTS = {
    "heritage_selected", "artifact_viewed", "provenance_viewed",
    "generation_requested", "design_viewed", "design_selected", "passport_viewed",
    "experiment_viewed", "comparison_viewed", "review_form_opened", "review_exported",
    "design_exported",
}
SERVER_EVENTS = {
    "generation_started", "generation_completed", "generation_failed",
    "qc_decision", "expert_review_submitted", "manual_edit_recorded", "design_exported",
}


def append_audit_event(project_root: Path, event: dict) -> bool:
    try:
        audit_dir = project_root / "outputs" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        payload = {"timestamp": datetime.now(timezone.utc).isoformat(), **event}
        with _write_lock, (audit_dir / "audit.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        return False

    return True
