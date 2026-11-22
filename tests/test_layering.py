"""Kiểm tra phân tầng import giữa các gói: tầng dưới không được import ngược lên tầng trên (chống phụ thuộc vòng).

Thứ tự từ thấp lên cao: core < generation < quality < provenance < evaluation < pipeline < api, streamlit_ui.
Quét bằng cây cú pháp nên bắt cả import lười đặt trong hàm.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# gói -> các gói dự án mà nó được phép import
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
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module.split(".")[0])
    return found & set(ALLOWED)


def test_khong_import_nguoc_len_tang_tren():
    loi = []
    for pkg, allowed in ALLOWED.items():
        for f in sorted((ROOT / pkg).rglob("*.py")):
            sai = project_imports(f) - allowed - {pkg}
            if sai:
                loi.append(f"{f.relative_to(ROOT).as_posix()} import {sorted(sai)}")
    assert not loi, "Import ngược tầng:\n" + "\n".join(loi)
