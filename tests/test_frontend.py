# -*- coding: utf-8 -*-
"""Giao diện tĩnh: cú pháp JS, dữ liệu trình diễn khớp dữ liệu thật, không số viết cứng."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web_ui"
JS = sorted((WEB / "assets" / "js").rglob("*.js"))


@pytest.mark.skipif(shutil.which("node") is None, reason="cần Node.js")
@pytest.mark.parametrize("path", JS, ids=lambda p: p.name)
def test_js_module_syntax(path):
    r = subprocess.run(["node", "--input-type=module", "--check"], input=path.read_text(encoding="utf-8"),
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr


def test_every_route_has_a_view():
    app = (WEB / "assets" / "js" / "app.js").read_text(encoding="utf-8")
    routes = set(re.findall(r"views/([a-z]+)\.js", app))
    assert routes
    for r in routes:
        assert (WEB / "assets" / "js" / "views" / f"{r}.js").exists(), r


def test_demo_data_matches_repo():
    # Trang Kết quả dùng bộ riêng data/result/ (xuất bằng scripts/11_export_demo_data.py --only-result): phải khớp outputs/passports
    stored = sorted(p.stem for p in (ROOT / "outputs" / "passports").glob("DP-*.json"))
    result = json.loads((WEB / "data" / "result" / "passports.json").read_text(encoding="utf-8"))
    assert sorted(p["passport_id"] for p in result) == stored
    for p in result:
        assert (WEB / p["thumb"]).is_file(), p["passport_id"]
    for hid in {p["heritage_id"] for p in result}:
        for v in range(1, 5):
            assert (WEB / "assets" / "images" / "result" / f"{hid}_V{v}_aodai.png").is_file(), (hid, v)
    # Các trang còn lại giữ bộ cũ: mỗi Passport trong passports.json phải có tệp chi tiết và ảnh thu nhỏ
    passports = json.loads((WEB / "data" / "passports.json").read_text(encoding="utf-8"))
    for p in passports:
        assert (WEB / "data" / "passports" / f"{p['passport_id']}.json").is_file(), p["passport_id"]
        assert (WEB / p["thumb"]).is_file(), p["passport_id"]
    heritage = json.loads((WEB / "data" / "heritage.json").read_text(encoding="utf-8"))
    registry = json.loads((ROOT / "data" / "heritage" / "metadata.json").read_text(encoding="utf-8"))
    assert len(heritage["items"]) == len(registry["items"])
    assert sum(it["status"] == "active" for it in heritage["items"]) == 6   # 6 hiện vật LR3D; 6 hiện vật cũ đã ngừng dùng
    for d in ("bpmn_to_be.svg", "bpmn_as_is.svg", "use_case.svg"):
        assert (WEB / "data" / "diagrams" / d).exists()


def test_no_hardcoded_similarity_in_new_ui():
    """Giao diện cũ viết cứng 88,4% / 76,2% / 68,5% / 54,1%; giao diện mới không được có."""
    for p in JS:
        txt = p.read_text(encoding="utf-8")
        for v in ("88.4", "76.2", "68.5", "54.1", "88,4", "76,2"):
            assert v not in txt, (p.name, v)


def test_no_inner_html_with_data():
    for p in JS:
        assert ".innerHTML" not in p.read_text(encoding="utf-8"), p.name


def test_every_active_heritage_has_a_valid_glb_model():
    """Mỗi hiện vật đang dùng có mô hình 3D GLB hợp lệ (đầu file 'glTF') và đủ nhẹ để tải trên web."""
    heritage = json.loads((WEB / "data" / "heritage.json").read_text(encoding="utf-8"))
    for it in heritage["items"]:
        if it["status"] != "active":
            continue
        glb = WEB / "assets" / "models" / f"{it['id']}.glb"
        assert glb.exists(), it["id"]
        assert glb.read_bytes()[:4] == b"glTF", it["id"]
        assert glb.stat().st_size < 8_000_000, it["id"]
