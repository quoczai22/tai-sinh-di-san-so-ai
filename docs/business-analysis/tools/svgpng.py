import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    b = pw.chromium.launch(channel="msedge")
    for f in sys.argv[1:]:
        f = Path(f)
        pg = b.new_page(device_scale_factor=2)
        pg.set_content('<html><body style="margin:0;background:#fff">' + f.read_text(encoding="utf-8") + "</body></html>")
        pg.wait_for_timeout(300)
        pg.locator("svg").first.screenshot(path=str(f.with_suffix(".png")))
        pg.close()
    b.close()
print("ok")
