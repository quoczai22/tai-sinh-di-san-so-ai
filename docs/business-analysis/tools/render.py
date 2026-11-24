# -*- coding: utf-8 -*-
"""Nạp từng tệp .bpmn bằng bpmn-js (thư viện của bpmn.io), báo cảnh báo khi đọc, xuất SVG và PNG.

    python render.py <thư mục chứa .bpmn>
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://unpkg.com/bpmn-js@17.11.1/dist/assets/bpmn-js.css">
<script src="https://unpkg.com/bpmn-js@17.11.1/dist/bpmn-viewer.development.js"></script>
<style>html,body{margin:0;background:#fff}#c{width:4000px;height:2400px}</style></head>
<body><div id="c"></div></body></html>"""

out_dir = Path(sys.argv[1])
report = {}
with sync_playwright() as pw:
    browser = browser = pw.chromium.launch(channel="msedge")
    page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=2)
    page.set_content(PAGE)
    page.wait_for_function("typeof BpmnJS === 'function'", timeout=30000)
    for f in sorted(out_dir.glob("*.bpmn")):
        xml = f.read_text(encoding="utf-8")
        res = page.evaluate("""async (xml) => {
            const el = document.getElementById('c'); el.innerHTML = '';
            const v = new BpmnJS({ container: el });
            try {
                const r = await v.importXML(xml);
                const { svg } = await v.saveSVG();
                window.__v = v;
                return { ok: true, warnings: r.warnings.map(w => w.message), svg };
            } catch (e) { return { ok: false, error: String(e), warnings: (e.warnings||[]).map(w => w.message) }; }
        }""", xml)
        report[f.name] = {"ok": res["ok"], "warnings": res.get("warnings", []), "error": res.get("error")}
        if not res["ok"]:
            continue
        svg = res["svg"]
        f.with_suffix(".svg").write_text(svg, encoding="utf-8")
        # PNG: vẽ SVG lên một trang riêng rồi chụp
        p2 = browser.new_page(device_scale_factor=2)
        p2.set_content('<html><body style="margin:0;background:#fff">' + svg + "</body></html>")
        p2.locator("svg").first.screenshot(path=str(f.with_suffix(".png")))
        p2.close()
    browser.close()
print(json.dumps(report, ensure_ascii=False, indent=1))
