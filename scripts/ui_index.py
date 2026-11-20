# -*- coding: utf-8 -*-
"""Sinh lại phần "tự động" của web_ui/index.html: thẻ <link> CSS và import map JS.

· CSS: theo thứ tự trong web_ui/assets/css/order.json (thứ tự nạp = thứ tự cascade).
· JS:  mọi module có thật trong web_ui/assets/js (trừ vendor/ và config.js).
Mỗi tệp mang ?v=<phiên bản> để trình duyệt không trộn tệp cũ với tệp mới sau khi phát hành.
Thêm, đổi tên hay xoá một file JS/CSS thì chạy lại script này; tests/test_frontend.py kiểm tra index.html luôn khớp.

    python scripts/ui_index.py              # giữ phiên bản hiện tại
    python scripts/ui_index.py finals-80    # đổi phiên bản (CSS, script, import map, mô hình 3D)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web_ui"
INDEX = WEB / "index.html"
VIEWER = WEB / "assets" / "js" / "components" / "viewer3d.js"
CSS_ORDER = WEB / "assets" / "css" / "order.json"
CSS_RE = re.compile(r"(<!-- css:start[^>]*-->\n)(.*?)(\s*<!-- css:end -->)", re.S)
MAP_RE = re.compile(r'(<script type="importmap">\s*)(\{.*?\})(\s*</script>)', re.S)


def modules() -> list[str]:
    js = WEB / "assets" / "js"
    return sorted(f"./{p.relative_to(WEB).as_posix()}" for p in js.rglob("*.js")
                  if "vendor" not in p.relative_to(js).parts and p.name != "config.js")


def css_files() -> list[str]:
    files = json.loads(CSS_ORDER.read_text(encoding="utf-8"))["files"]
    missing = [f for f in files if not (WEB / "assets" / "css" / f).exists()]
    extra = sorted(p.relative_to(WEB / "assets" / "css").as_posix() for p in (WEB / "assets" / "css").rglob("*.css")
                   if p.relative_to(WEB / "assets" / "css").as_posix() not in files)
    if missing or extra:
        raise SystemExit(f"order.json lệch với thư mục css: thiếu tệp {missing}, chưa khai báo {extra}")
    return files


def build(html: str, version: str) -> str:
    links = "\n".join(f'    <link rel="stylesheet" href="./assets/css/{f}?v={version}">' for f in css_files())
    html, n = CSS_RE.subn(lambda m: m.group(1) + links + "\n    <!-- css:end -->", html)
    if n != 1:
        raise SystemExit("Không tìm thấy đúng một cặp <!-- css:start --> … <!-- css:end --> trong index.html")
    imports = {m: f"{m}?v={version}" for m in modules()}
    imports["three"] = "./assets/js/vendor/three/three.module.js"
    body = json.dumps({"imports": imports}, indent=4, ensure_ascii=False)
    body = "\n".join(("    " + line) if i else line for i, line in enumerate(body.splitlines()))
    html, n = MAP_RE.subn(lambda m: m.group(1) + body + m.group(3), html)
    if n != 1:
        raise SystemExit("Không tìm thấy đúng một <script type=\"importmap\"> trong index.html")
    html = re.sub(r"\?v=finals-[\w.-]+", f"?v={version}", html)
    return re.sub(r'Đổi "finals-[\w.-]+"', f'Đổi "{version}"', html)


def current_version(html: str) -> str:
    m = re.search(r"\?v=(finals-[\w.-]+)", html)
    if not m:
        raise SystemExit("index.html chưa có chuỗi ?v=finals-N")
    return m.group(1)


def main() -> None:
    html = INDEX.read_text(encoding="utf-8")
    version = sys.argv[1] if len(sys.argv) > 1 else current_version(html)
    INDEX.write_text(build(html, version), encoding="utf-8", newline="\n")
    viewer = VIEWER.read_text(encoding="utf-8")
    VIEWER.write_text(re.sub(r"MODEL_VERSION = '[^']*'", f"MODEL_VERSION = '{version}'", viewer), encoding="utf-8", newline="\n")
    print(f"index.html: {len(css_files())} tệp CSS, {len(modules())} module JS, phiên bản {version}")


if __name__ == "__main__":
    main()
