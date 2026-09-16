from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path


_write_lock = threading.Lock()


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
