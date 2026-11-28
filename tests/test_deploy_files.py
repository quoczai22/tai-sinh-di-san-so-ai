"""Gói mã đưa lên Modal và Hugging Face Space phải đủ: toàn bộ mã Python nằm trong tsds/, cộng config/ và data/."""
import json
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


def _adjustment_amount_tu_modal_app():
    # modal_app.py import `modal` (CI không cài), nên chỉ tách riêng hàm cần thử.
    import ast
    tree = ast.parse((ROOT / "modal_app.py").read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_adjustment_amount")
    ns: dict = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "modal_app.py", "exec"), {"__builtins__": __builtins__}, ns)
    return ns["_adjustment_amount"]


def test_billing_doc_khoa_credits_khong_phan_biet_hoa_thuong():
    f = _adjustment_amount_tu_modal_app()
    # khóa thật của SDK Modal (kiểm ngày 25/11/2026 trong container): 'Credits' viết hoa
    assert f({"Free Storage": "-0.0018", "Credits": "-4.07"}, "credits") == -4.07
    assert f({"credits": "-4.07"}, "credits") == -4.07  # dạng JSON của CLI
    assert f({"Network Egress Allowance": "-0.05"}, "network_egress_allowance") == -0.05
    # không có mục: None chứ không phải 0, để bot ghi "chưa xác minh"
    assert f({"Free Storage": "-0.0018"}, "credits") is None
    assert f({}, "credits") is None and f(None, "credits") is None


def test_khong_con_goi_python_o_goc_repo():
    # mọi gói Python phải nằm trong tsds/, không để sót thư mục có __init__.py ở gốc (trừ tests)
    sot = [p.name for p in ROOT.iterdir() if p.is_dir() and (p / "__init__.py").exists() and p.name not in {"tsds", "tests"}]
    assert not sot, f"Gói Python còn ở gốc repo: {sot}"

def test_vercel_co_header_bao_mat_co_ban():
    # Header an toàn rủi ro thấp cho mọi đường dẫn. Cố ý chưa đặt CSP (importmap nội tuyến, font Google) và
    # X-Frame-Options (chặn việc nhúng link vào khung của cổng nộp bài); xem báo cáo kiểm thử 24/11.
    cfg = json.loads((ROOT / "web_ui" / "vercel.json").read_text(encoding="utf-8"))
    rule = next((h for h in cfg.get("headers", []) if h.get("source") == "/(.*)"), None)
    assert rule, "web_ui/vercel.json thiếu quy tắc headers cho mọi đường dẫn"
    got = {h["key"]: h["value"] for h in rule["headers"]}
    assert got.get("X-Content-Type-Options") == "nosniff"
    assert got.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "camera=()" in got.get("Permissions-Policy", "")
