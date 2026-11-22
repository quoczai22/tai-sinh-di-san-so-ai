# -*- coding: utf-8 -*-
"""Kiểm thử: pipeline lỗi thì job phải báo "failed", worker không được chết.

Giả lập pipeline ném lỗi (như thiếu torch, hết VRAM) cho 2 job liên tiếp.
Mong đợi: cả 2 job chuyển sang "failed" có thông báo lỗi, không job nào kẹt ở "queued".

Chạy từ gốc repo (không cần GPU):
    python tests/manual/test_worker_resilience.py
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import time
import types

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

os.environ["DH_API_KEY"] = "test_key"
os.environ["DH_OUTPUT_DIR"] = tempfile.mkdtemp(prefix="dh_out_")

# Thay module pipeline thật bằng bản luôn ném lỗi.
fake = types.ModuleType("tsds.pipeline.run")


def _boom(*_args, **_kwargs):
    raise RuntimeError("Giả lập lỗi GPU")


fake.generate_design_set = _boom
fake.SEED = 42  # tsds/api/main.py (bản chung kết) import SEED cùng generate_design_set
sys.modules["tsds.pipeline.run"] = fake

from tsds.api import main as api  # noqa: E402
from tsds.api.main import GenerateRequest  # noqa: E402


def main() -> int:
    def wait_done(job_id: str) -> dict:
        deadline = time.time() + 10
        state: dict = {}
        while time.time() < deadline:
            state = api.generate_status(job_id)
            if state.get("status") in {"failed", "completed"}:
                break
            time.sleep(0.2)
        return state

    # Job lỗi phải nhả GPU để job tiếp theo trong hàng chờ vẫn chạy.
    states: dict[str, dict] = {}
    for hid in ("LR3D_33", "LR3D_61"):
        job_id = api.generate_designs(GenerateRequest(heritage_id=hid))["job_id"]
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
