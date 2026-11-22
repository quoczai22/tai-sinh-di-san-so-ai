# -*- coding: utf-8 -*-
"""Kiểm thử cảnh báo Discord Webhook khi Modal gặp sự cố (Task 9).

Kịch bản:
1. Khởi chạy Mock Discord Webhook server ghi nhận các request POST.
2. Gateway chạy với ALERT_DISCORD_WEBHOOK_URL trỏ vào mock, KHÔNG có Modal backend (lỗi kết nối).
   - Lần 1: Gọi /api/generate -> rơi về demo -> Mock webhook nhận đúng 1 tin cảnh báo tiếng Việt.
   - Lần 2: Gọi tiếp ngay sau đó -> rơi về demo -> Không gửi tin mới (cooldown 30 phút).
3. Khi vượt Rate limit -> rơi về demo -> KHÔNG gửi cảnh báo (không phải sự cố).
4. Khi KHÔNG cấu hình ALERT_DISCORD_WEBHOOK_URL -> rơi về demo mượt mà, không lỗi.

Chạy:
    python tests/manual/test_alert_webhook.py
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

for _s in (sys.stdout, sys.stderr):
    if getattr(_s, "encoding", "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

ROOT = Path(__file__).resolve().parents[2]

received_messages: list[dict] = []


class MockWebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        try:
            data = json.loads(body)
        except Exception:
            data = {"raw": body}
        received_messages.append(data)
        self.send_response(204)
        self.end_headers()

    def log_message(self, format, *args):
        # Tắt in log ra stdout để màn hình test sạch
        pass


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
        time.sleep(0.2)
    return False


def main() -> int:
    procs: list[subprocess.Popen] = []
    webhook_server: HTTPServer | None = None
    try:
        print("=== KIỂM THỬ CẢNH BÁO DISCORD WEBHOOK (TASKS 7-9) ===\n")

        # 1. Khởi chạy Mock Webhook Server ở cổng 8089
        webhook_server = HTTPServer(("127.0.0.1", 8089), MockWebhookHandler)
        webhook_thread = threading.Thread(target=webhook_server.serve_forever, daemon=True)
        webhook_thread.start()
        print("[SETUP] Mock Discord Webhook listening at http://127.0.0.1:8089")

        # ------------------------------------------------------------------
        # KỊCH BẢN 1 & 2: Có ALERT_DISCORD_WEBHOOK_URL + Modal lỗi kết nối
        # ------------------------------------------------------------------
        env_gw = {
            **os.environ,
            "PORT": "3020",
            "MODAL_URL": "http://127.0.0.1:9999",  # Cổng không tồn tại -> lỗi kết nối
            "MODAL_TIMEOUT_MS": "1000",
            "ALERT_DISCORD_WEBHOOK_URL": "http://127.0.0.1:8089/webhook",
            "ALERT_COOLDOWN_MIN": "30",
            "RATE_LIMIT_PER_HOUR": "10",
        }
        # Đảm bảo không có biến HF
        env_gw.pop("HF_SPACE_URL", None)
        env_gw.pop("HF_TOKEN", None)

        pgw = subprocess.Popen(["node", "scripts/deploy/dev_gateway.js"], cwd=str(ROOT), env=env_gw)
        procs.append(pgw)

        assert wait_for_url("http://127.0.0.1:3020/health"), "Gateway 3020 không khởi động được"

        # Lần 1: Gọi /api/generate khi Modal sập
        received_messages.clear()
        t0 = time.time()
        c1, r1 = http_json("http://127.0.0.1:3020/api/generate", method="POST", body={"heritage_id": "LR3D_33"})
        elapsed1 = time.time() - t0

        assert c1 == 200, f"Lần 1 phải trả 200 Demo, nhận {c1}: {r1}"
        assert r1.get("backend") == "demo", f"Lần 1 backend phải là demo: {r1}"
        assert r1.get("reason") == "all_backends_unavailable"
        time.sleep(0.3)  # Chờ webhook xử lý

        assert len(received_messages) == 1, f"Kỳ vọng nhận 1 tin cảnh báo, thực tế: {len(received_messages)}"
        msg_content = received_messages[0].get("content", "")
        print(f"[THỰC TẾ TIN NHẮN 1] {msg_content}")
        assert "⚠️ Modal lỗi" in msg_content, "Tin nhắn phải có biểu tượng và thông báo Modal lỗi"
        assert "LR3D_33" in msg_content, "Tin nhắn phải nêu hiện vật LR3D_33"
        assert "giờ VN" in msg_content, "Tin nhắn phải có mốc giờ VN"
        assert "giám khảo đang thấy bản demo" in msg_content, "Tin nhắn phải thông báo giám khảo đang thấy demo"
        print(f"[PASS 1] Lần 1 Modal lỗi: trả về Demo sau {elapsed1:.2f}s và gửi đúng 1 cảnh báo Discord.")

        # Lần 2: Gọi tiếp ngay sau đó (trong 30 phút cooldown)
        c2, r2 = http_json("http://127.0.0.1:3020/api/generate", method="POST", body={"heritage_id": "LR3D_33"})
        assert c2 == 200 and r2.get("backend") == "demo"
        time.sleep(0.3)
        assert len(received_messages) == 1, f"Lần 2 phải bị chặn bởi cooldown 30p, nhưng có {len(received_messages)} tin"
        print("[PASS 2] Lần 2 gọi ngay sau đó: Cooldown 30 phút hoạt động tốt, không bị spam webhook.")

        # Tắt gateway 3020
        pgw.terminate()
        pgw.wait()
        procs.remove(pgw)

        # ------------------------------------------------------------------
        # KỊCH BẢN 3: Vượt Rate Limit -> KHÔNG gửi cảnh báo sự cố
        # ------------------------------------------------------------------
        received_messages.clear()
        env_gw_ratelimit = {
            **os.environ,
            "PORT": "3021",
            "MODAL_URL": "http://127.0.0.1:9999",
            "ALERT_DISCORD_WEBHOOK_URL": "http://127.0.0.1:8089/webhook",
            "RATE_LIMIT_PER_HOUR": "1",  # Chỉ cho phép 1 lượt
        }
        env_gw_ratelimit.pop("HF_SPACE_URL", None)
        pgw_rl = subprocess.Popen(["node", "scripts/deploy/dev_gateway.js"], cwd=str(ROOT), env=env_gw_ratelimit)
        procs.append(pgw_rl)
        assert wait_for_url("http://127.0.0.1:3021/health")

        # Lượt 1: dùng hết quota
        c_rl1, _ = http_json("http://127.0.0.1:3021/api/generate", method="POST", body={"heritage_id": "LR3D_33"})
        assert c_rl1 == 200
        time.sleep(0.2)
        # Reset tin nhắn để kiểm tra lượt 2 vượt quota
        received_messages.clear()

        # Lượt 2: Vượt rate limit
        c_rl2, r_rl2 = http_json("http://127.0.0.1:3021/api/generate", method="POST", body={"heritage_id": "LR3D_33"})
        assert c_rl2 == 200
        assert r_rl2.get("reason") == "rate_limit_exceeded"
        assert r_rl2.get("rate_limited") is True
        time.sleep(0.3)
        assert len(received_messages) == 0, f"Rơi về demo do rate limit KHÔNG ĐƯỢC gửi cảnh báo, nhưng có: {len(received_messages)}"
        print("[PASS 3] Rơi về demo do vượt Rate limit không gửi cảnh báo Discord (đúng hành vi).")

        pgw_rl.terminate()
        pgw_rl.wait()
        procs.remove(pgw_rl)

        # ------------------------------------------------------------------
        # KỊCH BẢN 4: Không đặt ALERT_DISCORD_WEBHOOK_URL -> Vẫn hoạt động bình thường
        # ------------------------------------------------------------------
        env_gw_no_alert = {
            **os.environ,
            "PORT": "3022",
            "MODAL_URL": "http://127.0.0.1:9999",
            "RATE_LIMIT_PER_HOUR": "10",
        }
        env_gw_no_alert.pop("ALERT_DISCORD_WEBHOOK_URL", None)
        env_gw_no_alert.pop("HF_SPACE_URL", None)
        pgw_no_alert = subprocess.Popen(["node", "scripts/deploy/dev_gateway.js"], cwd=str(ROOT), env=env_gw_no_alert)
        procs.append(pgw_no_alert)
        assert wait_for_url("http://127.0.0.1:3022/health")

        c4, r4 = http_json("http://127.0.0.1:3022/api/generate", method="POST", body={"heritage_id": "LR3D_33"})
        assert c4 == 200
        assert r4.get("backend") == "demo"
        print("[PASS 4] Không cấu hình biến ALERT_DISCORD_WEBHOOK_URL: Gateway rơi về Demo mượt mà, không lỗi.")

        # Modal chết sau khi gateway đã nhận job: chỉ lượt poll thất bại gửi cảnh báo.
        received_messages.clear()
        env_modal = {**os.environ, "PORT": "8030", "DELAY": "3"}
        for key in ("DH_API_KEY", "HF_TOKEN"):
            env_modal.pop(key, None)
        pmodal = subprocess.Popen([sys.executable, "mock_backend.py"], cwd=str(ROOT), env=env_modal)
        procs.append(pmodal)
        assert wait_for_url("http://127.0.0.1:8030/heritage")
        env_job = {**env_gw, "PORT": "3030", "MODAL_URL": "http://127.0.0.1:8030"}
        pgw_job = subprocess.Popen(["node", "scripts/deploy/dev_gateway.js"], cwd=str(ROOT), env=env_job)
        procs.append(pgw_job)
        assert wait_for_url("http://127.0.0.1:3030/health")
        c_job, r_job = http_json("http://127.0.0.1:3030/api/generate", method="POST", body={"heritage_id": "LR3D_33"})
        assert c_job == 202 and r_job.get("backend") == "modal", r_job
        status_url = f"http://127.0.0.1:3030/api/status?job_id={r_job['job_id']}&backend=modal&heritage_id=LR3D_33"
        c_pending, r_pending = http_json(status_url)
        assert c_pending == 200 and r_pending.get("status") in ("queued", "running"), r_pending
        pmodal.kill()
        pmodal.wait(timeout=5)
        c_lost, r_lost = http_json(status_url)
        assert c_lost == 200 and r_lost.get("backend") == "demo" and r_lost.get("status") == "completed", r_lost
        assert len(r_lost.get("variants", [])) == 4 and r_lost.get("demo_label"), r_lost
        assert len(received_messages) == 1, received_messages
        alert = received_messages[0].get("content", "")
        assert "giữa chừng" in alert and "LR3D_33" in alert, alert
        print("[PASS 5] Modal chết giữa job: đúng 1 cảnh báo có mã hiện vật.")
        pgw_job.terminate()
        pgw_job.wait(timeout=5)
        procs.remove(pgw_job)

        received_messages.clear()
        env_demo_only = {**env_gw, "PORT": "3031", "MODAL_URL": ""}
        pgw_demo_only = subprocess.Popen(["node", "scripts/deploy/dev_gateway.js"], cwd=str(ROOT), env=env_demo_only)
        procs.append(pgw_demo_only)
        assert wait_for_url("http://127.0.0.1:3031/health")
        c_only, r_only = http_json("http://127.0.0.1:3031/api/generate", method="POST", body={"heritage_id": "LR3D_33"})
        assert c_only == 200 and r_only.get("backend") == "demo", r_only
        assert len(received_messages) == 1, received_messages
        assert "chưa cấu hình URL" in received_messages[0].get("content", "")
        print("[PASS 6] MODAL_URL trống: Demo và một cảnh báo cấu hình.")

        print("\n=== TẤT CẢ 6 KỊCH BẢN CẢNH BÁO DISCORD ĐỀU ĐẠT CHUẨN (PASS) ===")
        return 0

    finally:
        for p in procs:
            try:
                p.terminate()
                p.wait(timeout=2)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        if webhook_server:
            try:
                webhook_server.shutdown()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
