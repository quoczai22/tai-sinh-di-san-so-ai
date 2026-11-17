# -*- coding: utf-8 -*-
"""Đóng gói thư mục riêng để upload lên Hugging Face Space (Docker, backend dự phòng).

Vì sao không `git push` cả repo lên Space:
  - Hugging Face từ chối push file nhị phân (PNG/JPG) không đi qua LFS/Xet.
  - Space cần README.md có khối YAML khai báo (sdk: docker, app_port: 7860).
  - Space chỉ cần backend + dữ liệu, không cần web_ui, docs, outputs.

Chạy từ gốc repo:
    python scripts/build_hf_space.py
Sau đó upload (lệnh upload tự xử lý file nhị phân qua Xet/LFS):
    hf upload <user>/<space-name> dist/hf_space . --repo-type space
    # CLI cũ: huggingface-cli upload <user>/<space-name> dist/hf_space . --repo-type space
"""
from __future__ import annotations

from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "hf_space"

COPY_FILES = [
    "Dockerfile",
    "requirements-api.txt",
    "streamlit_ui/__init__.py",
    "streamlit_ui/heritage_data.py",
]
COPY_DIRS = ["api", "generation", "evaluation", "data"]
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".gitkeep")

SPACE_README = """---
title: Tai Sinh Di San So API
emoji: 🏺
colorFrom: blue
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

Backend GPU dự phòng của dự án Tái Sinh Di Sản Số (FastAPI + SD1.5 + ControlNet).
Space để chế độ Private; chỉ cổng Vercel của nhóm gọi vào.

Secret cần đặt trong Settings của Space:
- `DH_API_KEY`: khớp `HF_API_KEY` trên Vercel (hoặc `MODAL_KEY` nếu không đặt `HF_API_KEY`).
"""


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    for rel in COPY_FILES:
        src = ROOT / rel
        if not src.is_file():
            print(f"[LỖI] Thiếu file: {rel}")
            return 1
        dst = OUT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    for rel in COPY_DIRS:
        src = ROOT / rel
        if not src.is_dir():
            print(f"[LỖI] Thiếu thư mục: {rel}")
            return 1
        shutil.copytree(src, OUT / rel, ignore=IGNORE)

    (OUT / "README.md").write_text(SPACE_README, encoding="utf-8")

    n_files = sum(1 for p in OUT.rglob("*") if p.is_file())
    size_mb = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file()) / 1024**2
    print(f"Đã đóng gói {n_files} file ({size_mb:.1f} MB) vào {OUT.relative_to(ROOT)}")
    print("Upload: hf upload <user>/<space-name> dist/hf_space . --repo-type space")
    return 0


if __name__ == "__main__":
    sys.exit(main())
