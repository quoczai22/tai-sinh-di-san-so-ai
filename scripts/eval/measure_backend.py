# -*- coding: utf-8 -*-
"""Đo số liệu triển khai thật của một backend GPU (Modal hoặc HF Space).

Đọc cấu hình từ biến môi trường, KHÔNG in khoá ra màn hình:
    BACKEND_URL   URL gốc của backend (vd. https://<workspace>--tai-sinh-di-san-so-api-fastapi-app.modal.run)
    BACKEND_KEY   Khoá ứng dụng, khớp DH_API_KEY của backend (gửi qua X-API-Key)
    HF_TOKEN      (tuỳ chọn, chỉ cho HF Space Private) gửi qua Authorization: Bearer

Chạy (PowerShell), tốt nhất khi backend đang ở trạng thái 0 container để đo cold start:
    python scripts/eval/measure_backend.py [heritage_id]

Cảnh báo: lệnh này bật GPU thật (tốn credit) và sinh 1 bộ 4 thiết kế.
"""
from __future__ import annotations

import json
import os
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

POLL_SECONDS = 3.0
MAX_WAIT_SECONDS = 20 * 60


def _headers() -> dict:
    headers = {"Accept": "application/json"}
    key = os.getenv("BACKEND_KEY", "").strip()
    if key:
        headers["X-API-Key"] = key
    hf_token = os.getenv("HF_TOKEN", "").strip()
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"
    return headers


def call(base: str, path: str, method: str = "GET", body: dict | None = None,
         timeout: float = 600.0) -> tuple[int, dict | str, float]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = _headers()
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{base}{path}", data=data, headers=headers, method=method)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            code = resp.status
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8", errors="replace")
        code = err.code
    elapsed = time.perf_counter() - t0
    try:
        return code, json.loads(raw), elapsed
    except ValueError:
        return code, raw[:300], elapsed


def main() -> int:
    base = os.getenv("BACKEND_URL", "").strip().rstrip("/")
    if not base:
        print("Thiếu BACKEND_URL.")
        return 2
    if not os.getenv("BACKEND_KEY", "").strip():
        print("Thiếu BACKEND_KEY (khoá khớp DH_API_KEY của backend).")
        return 2
    heritage_id = sys.argv[1] if len(sys.argv) > 1 else "LR3D_33"
    print(f"Backend: {base}\nHiện vật: {heritage_id}\n")

    code, res, t_health = call(base, "/health")
    print(f"[1] /health            -> {code} sau {t_health:.1f}s  (gồm cold start nếu đang 0 container) {res}")
    if code != 200:
        return 1

    code, res, t_gpu = call(base, "/health/gpu")
    print(f"[2] /health/gpu        -> {code} sau {t_gpu:.1f}s  {res}")

    t_start = time.perf_counter()
    code, res, t_post = call(base, "/generate", method="POST", body={"heritage_id": heritage_id})
    print(f"[3] POST /generate     -> {code} sau {t_post:.1f}s  {res}")
    if code != 202 or not isinstance(res, dict):
        return 1
    job_id = res["job_id"]

    last_label = ""
    while True:
        if time.perf_counter() - t_start > MAX_WAIT_SECONDS:
            print("Quá 20 phút chưa xong, dừng đo.")
            return 1
        time.sleep(POLL_SECONDS)
        code, job, _ = call(base, f"/generate/{job_id}", timeout=120.0)
        if code != 200 or not isinstance(job, dict):
            print(f"    poll -> {code} {job}")
            continue
        label = f"{job.get('status')} {job.get('progress')}% {job.get('label', '')}"
        if label != last_label:
            print(f"    +{time.perf_counter() - t_start:6.1f}s  {label}")
            last_label = label
        if job.get("status") in ("completed", "failed"):
            break

    total = time.perf_counter() - t_start
    print(f"\n[4] Job {job_id[:8]}... kết thúc: {job.get('status')} sau {total:.1f}s (từ lúc POST tới lúc poll thấy xong)")
    if job.get("status") != "completed":
        return 1
    print(f"    GPU: {job.get('gpu')}")
    for v in job.get("variants", []):
        print(f"    V{v.get('variant_index')}: {v.get('duration_s')}s  layout={v.get('layout')}  "
              f"similarity={v.get('similarity_pattern_vs_ceramic')}  file={v.get('image_url')}")

    first_file = (job.get("variants") or [{}])[0].get("image_url", "")
    if first_file:
        code, _, t_img = call(base, first_file, timeout=120.0)
        print(f"[5] Tải ảnh V1         -> {code} sau {t_img:.1f}s")

    print("\nGhi vào docs/DEPLOY.md mục 6: cold start ≈ [1], thời gian sinh 4 thiết kế ≈ [4] "
          "(lưu ý: mỗi job nạp lại model SD/ControlNet/CLIP, nên [4] đã gồm thời gian nạp model).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
