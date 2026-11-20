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
fake.SEED = 42  # api/main.py (bản chung kết) import SEED cùng generate_design_set
sys.modules["generation.streamlit_runner"] = fake

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402


def main() -> int:
    client = TestClient(app)
    headers = {"X-API-Key": "test_key"}

    def wait_done(job_id: str) -> dict:
        deadline = time.time() + 10
        state: dict = {}
        while time.time() < deadline:
            state = client.get(f"/generate/{job_id}", headers=headers).json()
            if state.get("status") in {"failed", "completed"}:
                break
            time.sleep(0.2)
        return state

    # API bản chung kết chạy MỘT job mỗi lúc (job thứ hai trong lúc bận nhận 409), nên gửi
    # tuần tự: job lỗi phải nhả khoá, job sau vẫn được nhận và cũng báo "failed" (không kẹt).
    states: dict[str, dict] = {}
    for hid in ("LR3D_33", "LR3D_61"):
        res = client.post("/generate", json={"heritage_id": hid}, headers=headers)
        assert res.status_code == 202, f"{hid}: HTTP {res.status_code} {res.text}"
        job_id = res.json()["job_id"]
        states[job_id] = wait_done(job_id)

    # Bản chung kết ẩn chi tiết lỗi khỏi người dùng (chỉ ghi log máy chủ): job phải "failed",
    # có nhãn thông báo, và KHÔNG lộ thông điệp exception nội bộ.
    ok = len(states) == 2 and all(
        s.get("status") == "failed" and s.get("label") and "Giả lập lỗi GPU" not in s["label"]
        for s in states.values()
    )
    for job_id, state in states.items():
        print(f"  {job_id[:8]}: {state['status']} — {state['label']}")
    print("[PASS] Worker sống sót, job lỗi được báo 'failed'." if ok else "[FAIL] Có job kẹt hoặc sai trạng thái.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
