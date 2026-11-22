"""Gói mã đưa lên Modal và Hugging Face Space phải đủ mọi gói Python mà API import (thiếu một gói là bản triển khai hỏng khi chạy)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Các gói Python mà api.main dùng trực tiếp hoặc gián tiếp (streamlit_ui không đưa vào ảnh triển khai)
GOI_CAN_DONG_GOI = {"api", "core", "pipeline", "generation", "evaluation", "provenance", "quality"}


def test_dockerfile_copy_du_goi():
    copied = set(re.findall(r"^COPY (\w+)/ ", (ROOT / "Dockerfile").read_text(encoding="utf-8"), re.M))
    assert GOI_CAN_DONG_GOI <= copied, f"Dockerfile thiếu: {sorted(GOI_CAN_DONG_GOI - copied)}"


def test_hf_space_copy_dirs_du_goi():
    src = (ROOT / "scripts" / "deploy" / "build_hf_space.py").read_text(encoding="utf-8")
    dirs = set(re.findall(r'"(\w+)"', re.search(r"COPY_DIRS = \[(.*?)\]", src, re.S).group(1)))
    assert GOI_CAN_DONG_GOI <= dirs, f"COPY_DIRS thiếu: {sorted(GOI_CAN_DONG_GOI - dirs)}"
    # khớp các lệnh COPY trong Dockerfile
    copied = set(re.findall(r"^COPY (\w+)/ ", (ROOT / "Dockerfile").read_text(encoding="utf-8"), re.M))
    assert dirs == copied
