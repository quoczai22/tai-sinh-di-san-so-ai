"""Gói mã đưa lên Modal và Hugging Face Space phải đủ: toàn bộ mã Python nằm trong tsds/, cộng config/ và data/."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAN_DONG_GOI = {"tsds", "config", "data"}


def _dockerfile_copied() -> set[str]:
    return set(re.findall(r"^COPY (\w+)/ ", (ROOT / "Dockerfile").read_text(encoding="utf-8"), re.M))


def test_dockerfile_copy_du_thu_muc():
    assert CAN_DONG_GOI <= _dockerfile_copied(), f"Dockerfile thiếu: {sorted(CAN_DONG_GOI - _dockerfile_copied())}"


def test_dockerfile_chay_dung_module():
    assert '"tsds.api.main:app"' in (ROOT / "Dockerfile").read_text(encoding="utf-8")


def test_hf_space_copy_dirs_khop_dockerfile():
    src = (ROOT / "scripts" / "deploy" / "build_hf_space.py").read_text(encoding="utf-8")
    dirs = set(re.findall(r'"(\w+)"', re.search(r"COPY_DIRS = \[(.*?)\]", src, re.S).group(1)))
    assert CAN_DONG_GOI <= dirs and dirs == _dockerfile_copied()


def test_khong_con_goi_python_o_goc_repo():
    # mọi gói Python phải nằm trong tsds/, không để sót thư mục có __init__.py ở gốc (trừ tests)
    sot = [p.name for p in ROOT.iterdir() if p.is_dir() and (p / "__init__.py").exists() and p.name not in {"tsds", "tests"}]
    assert not sot, f"Gói Python còn ở gốc repo: {sot}"
