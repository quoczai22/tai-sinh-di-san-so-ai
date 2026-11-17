# -*- coding: utf-8 -*-
"""Kiểm thử tự động các Tiêu chí nghiệm thu #1 đến #8 (Mục 5).

Chạy:
    python scripts/test_acceptance_1_8.py
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

for _s in (sys.stdout, sys.stderr):
    if getattr(_s, "encoding", "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

ROOT = Path(__file__).resolve().parent.parent


def http_json(url: str, method: str = "GET", body: dict | None = None, headers: dict | None = None, timeout: float = 10.0) -> tuple[int, dict]:
    req_headers = {"Accept": "application/json", **(headers or {})}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8", errors="replace")
        try:
            return err.code, json.loads(raw)
        except Exception:
            return err.code, {"detail": raw}


def wait_for_url(url: str, timeout_s: float = 10.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            code, _ = http_json(url, timeout=1.5)
            if code in (200, 503):
                return True
        except Exception:
            pass
        time.sleep(0.25)
    return False


def main() -> int:
    procs: list[subprocess.Popen] = []
    try:
        print("=== KIỂM THỬ TIÊU CHÍ NGHIỆM THU 1–8 ===\n")

        # ------------------------------------------------------------------
        # Tiêu chí #6: Gọi /health của api.main không import torch
        # ------------------------------------------------------------------
        check_code = (
            "import sys; import api.main as m; "
            "res = m.health(); "
            "assert res == {'status': 'ok'}, res; "
            "assert 'torch' not in sys.modules, 'torch đã bị import khi gọi /health!'; "
            "print('OK_NO_TORCH')"
        )
        out = subprocess.check_output([sys.executable, "-c", check_code], cwd=str(ROOT), text=True)
        assert "OK_NO_TORCH" in out
        print("[PASS #6] Gọi /health không import torch, không đánh thức GPU.")

        # ------------------------------------------------------------------
        # Khởi chạy Mock 8001 (Modal) và Mock 8002 (HF) + Cổng 3000
        # ------------------------------------------------------------------
        env_8001 = {
            **os.environ,
            "PORT": "8001",
            "DELAY": "1.2",
            "DH_API_KEY": "secret_modal_key_test",
            "BACKEND_NAME": "Modal NVIDIA T4",
        }
        env_8002 = {
            **os.environ,
            "PORT": "8002",
            "DELAY": "0.8",
            "HF_TOKEN": "secret_hf_token_test",
            "BACKEND_NAME": "HF Space NVIDIA T4",
        }
        env_gw = {
            **os.environ,
            "PORT": "3010",
            "MODAL_URL": "http://127.0.0.1:8001",
            "MODAL_KEY": "secret_modal_key_test",
            "HF_SPACE_URL": "http://127.0.0.1:8002",
            "HF_TOKEN": "secret_hf_token_test",
            "MODAL_TIMEOUT_MS": "1500",
            "RATE_LIMIT_PER_HOUR": "50",
        }

        p8001 = subprocess.Popen([sys.executable, "mock_backend.py"], cwd=str(ROOT), env=env_8001)
        procs.append(p8001)
        p8002 = subprocess.Popen([sys.executable, "mock_backend.py"], cwd=str(ROOT), env=env_8002)
        procs.append(p8002)
        pgw = subprocess.Popen(["node", "scripts/dev_gateway.js"], cwd=str(ROOT), env=env_gw)
        procs.append(pgw)

        assert wait_for_url("http://127.0.0.1:8001/health"), "8001 không khởi động được"
        assert wait_for_url("http://127.0.0.1:8002/health"), "8002 không khởi động được"
        assert wait_for_url("http://127.0.0.1:3010/health"), "Gateway 3010 không khởi động được"

        # ------------------------------------------------------------------
        # Tiêu chí #7: Gọi /generate trên backend khi không có X-API-Key -> 401
        # ------------------------------------------------------------------
        code_no_key, _ = http_json("http://127.0.0.1:8001/generate", method="POST", body={"heritage_id": "BT_Hac_XP"})
        assert code_no_key == 401, f"Mong đợi 401 nhưng nhận {code_no_key}"
        print("[PASS #7] Gọi /generate không có X-API-Key trả về HTTP 401.")

        # ------------------------------------------------------------------
        # Tiêu chí #8: Xem source trang + toàn bộ JS trên trình duyệt không chứa HF_TOKEN hay MODAL_KEY
        # ------------------------------------------------------------------
        for rel in ("index.html", "assets/js/config.js", "assets/js/app.js", "assets/js/services/heritage-api.js"):
            with urllib.request.urlopen(f"http://127.0.0.1:3010/{rel}", timeout=5) as resp:
                text = resp.read().decode("utf-8")
                assert "secret_modal_key_test" not in text
                assert "secret_hf_token_test" not in text
                assert "HF_TOKEN" not in text
                assert "MODAL_KEY" not in text
        print("[PASS #8] Source trang và toàn bộ JS trình duyệt không lộ HF_TOKEN hay MODAL_KEY.")

        # ------------------------------------------------------------------
        # Tiêu chí #1: Cả 8001 (Modal) và 8002 (HF) đều chạy -> Phục vụ bởi Modal
        # ------------------------------------------------------------------
        code1, res1 = http_json("http://127.0.0.1:3010/api/generate", method="POST", body={"heritage_id": "BT_Hac_XP"})
        assert code1 in (200, 202) and res1.get("backend") == "modal", f"Mong đợi modal, nhận: {res1}"
        print(f"[PASS #1] Cả 8001 & 8002 chạy -> Phục vụ bởi backend='{res1['backend']}' (job_id={res1['job_id'][:8]}...).")

        # ------------------------------------------------------------------
        # Tiêu chí #5: 2 trình duyệt bấm cùng lúc -> Không có lỗi 409; người thứ 2 thấy vị trí hàng đợi
        # ------------------------------------------------------------------
        c_a, r_a = http_json("http://127.0.0.1:3010/api/generate", method="POST", body={"heritage_id": "BT_Hac_XP"})
        c_b, r_b = http_json("http://127.0.0.1:3010/api/generate", method="POST", body={"heritage_id": "BT010_2"})
        assert c_a != 409 and c_b != 409, f"Bị lỗi 409: {c_a}, {c_b}"
        _, st_b = http_json(f"http://127.0.0.1:3010/api/status?job_id={r_b['job_id']}&backend=modal&heritage_id=BT010_2")
        assert "queue_position" in st_b and st_b["queue_position"] >= 1, f"Không thấy queue_position >= 1: {st_b}"
        print(f"[PASS #5] 2 trình duyệt bấm cùng lúc -> Không lỗi 409; người thứ 2 thấy queue_position={st_b['queue_position']}.")

        # Chờ job hoàn tất trên 8001
        for _ in range(25):
            _, st_done = http_json(f"http://127.0.0.1:3010/api/status?job_id={res1['job_id']}&backend=modal&heritage_id=BT_Hac_XP")
            if st_done.get("status") == "completed":
                break
            time.sleep(0.25)
        assert st_done.get("status") == "completed", f"Job modal chưa completed: {st_done}"
        assert st_done["variants"][0]["image_url"].startswith("/api/media?backend=modal&file="), st_done["variants"][0]

        # ------------------------------------------------------------------
        # Tiêu chí #4: DELAY=120 trên 8001 -> Timeout đúng cấu hình (1.5s) rồi failover sang 8002, không treo
        # ------------------------------------------------------------------
        p8001.terminate()
        p8001.wait(timeout=5)
        env_8001_slow = {**env_8001, "DELAY": "120"}
        p8001_slow = subprocess.Popen([sys.executable, "mock_backend.py"], cwd=str(ROOT), env=env_8001_slow)
        procs.append(p8001_slow)
        time.sleep(1.0)

        t0 = time.time()
        code4, res4 = http_json("http://127.0.0.1:3010/api/generate", method="POST", body={"heritage_id": "BT_Hac_XP"}, timeout=8.0)
        elapsed4 = time.time() - t0
        assert code4 in (200, 202) and res4.get("backend") == "hf", f"Mong đợi failover sang hf, nhận: {res4}"
        assert elapsed4 < 5.0, f"Bị treo quá lâu: {elapsed4:.2f}s"
        print(f"[PASS #4] DELAY=120 trên 8001 -> Timeout sau {elapsed4:.2f}s và tự động failover sang backend='{res4['backend']}'.")

        # ------------------------------------------------------------------
        # Tiêu chí #2: Tắt mock 8001 -> Tự chuyển sang 8002 (HF Space)
        # ------------------------------------------------------------------
        p8001_slow.terminate()
        p8001_slow.wait(timeout=5)

        code2, res2 = http_json("http://127.0.0.1:3010/api/generate", method="POST", body={"heritage_id": "BT_Hac_XP"})
        assert code2 in (200, 202) and res2.get("backend") == "hf", f"Mong đợi hf, nhận: {res2}"
        print(f"[PASS #2] Tắt mock 8001 -> Tự động chuyển sang 8002 (backend='{res2['backend']}').")

        # ------------------------------------------------------------------
        # Tiêu chí #3: Tắt cả hai (8001 & 8002) -> Demo mode, có nhãn, số khớp variants.csv
        # ------------------------------------------------------------------
        p8002.terminate()
        p8002.wait(timeout=5)

        code3, res3 = http_json("http://127.0.0.1:3010/api/generate", method="POST", body={"heritage_id": "BT_Hac_XP"})
        assert code3 == 200 and res3.get("backend") == "demo", f"Mong đợi demo, nhận: {res3}"
        assert res3.get("demo_label") == "Kết quả đã sinh sẵn — không phải sinh trực tiếp"
        assert len(res3.get("variants", [])) == 4

        with (ROOT / "evaluation" / "variants.csv").open("r", encoding="utf-8") as f:
            csv_rows = [r for r in csv.DictReader(f) if r["heritage_id"] == "BT_Hac_XP"]
        for idx, v in enumerate(res3["variants"]):
            expected_sim = float(csv_rows[idx]["similarity_pattern_vs_ceramic"])
            assert abs(float(v["similarity_pattern_vs_ceramic"]) - expected_sim) < 1e-6
            assert len(v["sha256_design"]) == 64
        print("[PASS #3] Tắt cả 8001 & 8002 -> Trả về Demo mode, đúng nhãn và khớp 100% số liệu variants.csv.")

        print("\n=== TẤT CẢ TIÊU CHÍ NGHIỆM THU 1–8 ĐỀU ĐẠT (8/8 PASS) ===")
        return 0
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=3)
                except Exception:
                    p.kill()


if __name__ == "__main__":
    sys.exit(main())
