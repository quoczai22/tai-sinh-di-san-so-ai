from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


_write_lock = threading.Lock()


def get_output_dir(project_root: Path) -> Path:
    raw = os.getenv("DH_OUTPUT_DIR", "outputs").strip() or "outputs"
    path = Path(raw)
    return path if path.is_absolute() else (project_root / path)


def append_audit_event(project_root: Path, event: dict, output_dir: Path | None = None) -> bool:
    try:
        base_dir = output_dir or get_output_dir(project_root)
        audit_dir = base_dir / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        payload = {"timestamp": datetime.now(timezone.utc).isoformat(), **event}
        with _write_lock, (audit_dir / "audit.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        return False

    return True
