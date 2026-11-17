# -*- coding: utf-8 -*-
"""Kiểm thử khoá API fail-closed của api/main.py (không cần GPU).

Chạy:
    python scripts/test_api_key_guard.py

Ba trường hợp:
  1. DH_REQUIRE_API_KEY=1, DH_API_KEY trống  -> import api.main phải lỗi RuntimeError rõ ràng.
  2. DH_REQUIRE_API_KEY=1, DH_API_KEY có giá trị -> khởi động được; /generate thiếu khoá -> 401.
  3. Không đặt DH_REQUIRE_API_KEY, DH_API_KEY trống -> khởi động được như cũ (chạy local).
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    if getattr(_s, "encoding", "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

ROOT = Path(__file__).resolve().parent.parent

IMPORT_ONLY = "import api.main; print('STARTED')"
IMPORT_AND_401 = (
    "from fastapi.testclient import TestClient; import api.main as m; "
    "c = TestClient(m.app); "
    "r = c.post('/generate', json={'heritage_id': 'BT_Hac_XP'}); "
    "assert r.status_code == 401, r.status_code; "
    "print('STARTED_401')"
)


def run(code: str, **overrides: str | None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in {"DH_API_KEY", "DH_REQUIRE_API_KEY"}}
    env["PYTHONIOENCODING"] = "utf-8"
    for key, value in overrides.items():
        if value is not None:
            env[key] = value
    return subprocess.run(
        [sys.executable, "-c", code], cwd=str(ROOT), env=env,
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )


def main() -> int:
    # 1. Bắt buộc khoá nhưng khoá trống (kể cả chỉ có khoảng trắng) -> từ chối khởi động
    for empty in ("", "   "):
        res = run(IMPORT_ONLY, DH_REQUIRE_API_KEY="1", DH_API_KEY=empty)
        assert res.returncode != 0, f"Lẽ ra phải từ chối khởi động (DH_API_KEY={empty!r}): {res.stdout}"
        assert "RuntimeError" in res.stderr and "DH_API_KEY" in res.stderr, res.stderr
        assert "STARTED" not in res.stdout
    print("[PASS] DH_REQUIRE_API_KEY=1 + DH_API_KEY trống -> server từ chối khởi động, báo lỗi rõ.")

    # 2. Bắt buộc khoá và có khoá -> khởi động, chặn request thiếu khoá
    res = run(IMPORT_AND_401, DH_REQUIRE_API_KEY="1", DH_API_KEY="test_key_guard")
    assert res.returncode == 0 and "STARTED_401" in res.stdout, res.stderr
    print("[PASS] DH_REQUIRE_API_KEY=1 + có DH_API_KEY -> khởi động, /generate thiếu khoá trả 401.")

    # 3. Chạy local: không đặt biến -> hành vi cũ
    res = run(IMPORT_ONLY)
    assert res.returncode == 0 and "STARTED" in res.stdout, res.stderr
    print("[PASS] Không đặt DH_REQUIRE_API_KEY -> khởi động như cũ (local).")

    print("\n=== KHOÁ API FAIL-CLOSED: 3/3 PASS ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
