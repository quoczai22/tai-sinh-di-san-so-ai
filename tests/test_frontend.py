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
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_every_route_has_a_view():
    app = (WEB / "assets" / "js" / "app.js").read_text(encoding="utf-8")
    routes = set(re.findall(r"views/([a-z]+)\.js", app))
    assert routes
    for r in routes:
        assert (WEB / "assets" / "js" / "views" / f"{r}.js").exists(), r


def test_demo_data_matches_repo():
    passports = json.loads((WEB / "data" / "passports.json").read_text(encoding="utf-8"))
    stored = sorted(p.stem for p in (ROOT / "outputs" / "passports").glob("DP-*.json"))
    assert sorted(p["passport_id"] for p in passports) == stored
    heritage = json.loads((WEB / "data" / "heritage.json").read_text(encoding="utf-8"))
    assert len(heritage["items"]) == 6
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
