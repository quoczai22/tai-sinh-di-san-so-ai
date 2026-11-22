"""Kiểm tra phân tầng import giữa các gói con của tsds: tầng dưới không được import ngược lên tầng trên (chống phụ thuộc vòng).

Thứ tự từ thấp lên cao: tsds.core < generation < quality < provenance < evaluation < pipeline < api, streamlit_ui (đều là gói con của tsds).
Quét bằng cây cú pháp nên bắt cả import lười đặt trong hàm.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSDS = ROOT / "tsds"
# gói con -> các gói con khác mà nó được phép import
ALLOWED = {
    "core": set(),
    "generation": {"core"},
    "quality": {"core", "generation"},
    "provenance": {"core", "generation", "quality"},
    "evaluation": {"core", "generation", "quality", "provenance"},
    "pipeline": {"core", "generation", "quality", "provenance", "evaluation"},
    "api": {"core", "generation", "quality", "provenance", "evaluation", "pipeline"},
    "streamlit_ui": {"core", "generation", "quality", "provenance", "evaluation", "pipeline"},
}


def project_imports(path: Path) -> set[str]:
    """Các gói con của tsds mà file này import (tsds.<gói con>...)."""
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            for a in node.names:
                parts = a.name.split(".")
                if parts[0] == "tsds" and len(parts) > 1:
                    found.add(parts[1])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            parts = node.module.split(".")
            if parts[0] == "tsds":
                if len(parts) > 1:
                    found.add(parts[1])
                else:                                   # from tsds import generation
                    found |= {a.name for a in node.names}
    return found & set(ALLOWED)


def test_moi_goi_con_ton_tai_va_co_file():
    # tránh "đạt giả" khi đổi tên thư mục mà test quét nhầm chỗ
    for pkg in ALLOWED:
        assert list((TSDS / pkg).rglob("*.py")), f"tsds/{pkg} không có file .py"


def test_khong_import_nguoc_len_tang_tren():
    loi = []
    for pkg, allowed in ALLOWED.items():
        for f in sorted((TSDS / pkg).rglob("*.py")):
            sai = project_imports(f) - allowed - {pkg}
            if sai:
                loi.append(f"{f.relative_to(ROOT).as_posix()} import {sorted(sai)}")
    assert not loi, "Import ngược tầng:\n" + "\n".join(loi)


def test_khong_con_import_kieu_cu():
    # mọi import gói dự án phải qua tsds.*, không còn "from generation import ..." kiểu cũ
    cu = []
    for f in list(TSDS.rglob("*.py")) + list((ROOT / "scripts").rglob("*.py")) + list((ROOT / "tests").rglob("*.py")):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module] if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module else []
            if any(n.split(".")[0] in ALLOWED for n in names):
                cu.append(f.relative_to(ROOT).as_posix())
    assert not cu, "Còn import kiểu cũ:\n" + "\n".join(sorted(set(cu)))


def _import_garment(path: Path) -> bool:
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.level >= 2:        # import tương đối đi lên generation/
            mod = node.module or ""
            if mod.split(".")[0] == "garment" or (not mod and any(a.name == "garment" for a in node.names)):
                return True
        if isinstance(node, ast.ImportFrom) and node.level == 0:
            mod = node.module or ""
            if mod.startswith("tsds.generation.garment"):
                return True
            if mod == "tsds.generation" and any(a.name == "garment" for a in node.names):
                return True
        elif isinstance(node, ast.Import):
            if any(a.name.startswith("tsds.generation.garment") for a in node.names):
                return True
    return False


def test_generation_pattern_khong_import_garment():
    # Giai doan 2 (garment) duoc dung giai doan 1 (pattern), khong duoc nguoc lai: tranh vong pattern <-> garment
    loi = [f.relative_to(ROOT).as_posix() for f in sorted((TSDS / "generation" / "pattern").rglob("*.py")) if _import_garment(f)]
    assert not loi, "pattern import garment: " + ", ".join(loi)


CHUNG = {"stable_diffusion.py", "prompt_template.py"}   # module dùng chung của hai giai đoạn, nằm ở generation/


def test_generation_chi_co_hai_goi_con_va_module_chung():
    # moi module sinh anh nam trong pattern/ hoac garment/; chi 2 module dung chung duoc o generation/
    le = sorted(f.name for f in (TSDS / "generation").glob("*.py") if f.name != "__init__.py")
    assert set(le) == CHUNG, f"Module o generation/: {le}"
    for sub in ("pattern", "garment"):
        assert (TSDS / "generation" / sub / "__init__.py").exists()


def test_module_chung_khong_import_pattern_hay_garment():
    # module dung chung o tang thap hon: pattern va garment import chung, khong duoc nguoc lai
    loi = []
    for name in sorted(CHUNG):
        f = TSDS / "generation" / name
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            mods = []
            if isinstance(node, ast.ImportFrom):
                base = node.module or ""
                mods = [base] + [base + "." + a.name for a in node.names]
                if node.level >= 1:      # import tuong doi trong generation/: from . import pattern / from .garment import x
                    mods += ["tsds.generation." + (base or a.name) for a in node.names]
            elif isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            if any(m.startswith(("tsds.generation.pattern", "tsds.generation.garment")) for m in mods):
                loi.append(name)
    assert not loi, "Module chung import pattern/garment: " + ", ".join(sorted(set(loi)))
