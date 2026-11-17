# -*- coding: utf-8 -*-
"""Kiểm thử: pipeline lỗi thì job phải báo "failed", worker không được chết.

Giả lập pipeline ném lỗi (như thiếu torch, hết VRAM) cho 2 job liên tiếp.
Mong đợi: cả 2 job chuyển sang "failed" có thông báo lỗi, không job nào kẹt ở "queued".

Chạy từ gốc repo (không cần GPU):
    python scripts/test_worker_resilience.py
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import time
import types

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["DH_API_KEY"] = "test_key"
os.environ["DH_OUTPUT_DIR"] = tempfile.mkdtemp(prefix="dh_out_")

# Thay module pipeline thật bằng bản luôn ném lỗi.
fake = types.ModuleType("generation.streamlit_runner")


def _boom(*_args, **_kwargs):
    raise RuntimeError("Giả lập lỗi GPU")


fake.generate_design_set = _boom
sys.modules["generation.streamlit_runner"] = fake

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402


def main() -> int:
    client = TestClient(app)
    headers = {"X-API-Key": "test_key"}
    job_ids = [
        client.post("/generate", json={"heritage_id": hid}, headers=headers).json()["job_id"]
        for hid in ("BT_Hac_XP", "BT010_2")
    ]

    deadline = time.time() + 10
    states: dict[str, dict] = {}
    while time.time() < deadline:
        states = {j: client.get(f"/generate/{j}", headers=headers).json() for j in job_ids}
        if all(s["status"] in {"failed", "completed"} for s in states.values()):
            break
        time.sleep(0.2)

    ok = all(s["status"] == "failed" and "Giả lập lỗi GPU" in s["label"] for s in states.values())
    for job_id, state in states.items():
        print(f"  {job_id[:8]}: {state['status']} — {state['label']}")
    print("[PASS] Worker sống sót, job lỗi được báo 'failed'." if ok else "[FAIL] Có job kẹt hoặc sai trạng thái.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
