# -*- coding: utf-8 -*-
"""Xuất dữ liệu demo cho cổng Vercel cũ (web_ui/api/generate.js, status.js) từ Design Passport hiện có.

Cổng này trả `web_ui/assets/data/demo_variants.json` khi không nối được GPU. Mọi giá trị lấy từ Passport
trong outputs/passports/, không viết tay.

    uv run python scripts/demo/export_gateway_demo.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tsds.core.paths import PASSPORTS_DIR  # noqa: E402

OUT = ROOT / "web_ui" / "assets" / "data" / "demo_variants.json"


def main() -> int:
    items: dict[str, list[dict]] = {}
    for f in sorted(PASSPORTS_DIR.glob("DP-*.json")):
        p = json.loads(f.read_text(encoding="utf-8"))
        g = p["generation"]
        n = int(p["passport_id"].rsplit("-V", 1)[-1])
        hid = p["heritage"]["heritage_id"]
        items.setdefault(hid, []).append({
            "variant": f"{hid}_V{n}",
            "heritage_id": hid,
            "variant_index": n,
            "intensity_level": g["controlnet"]["intensity_level"],
            "level_name": g["controlnet"]["intensity_name"],
            "controlnet_weight": g["controlnet"]["conditioning_scale"],
            "layout": g["layout"]["name"],
            "layout_label": g["layout"]["label"],
            "polish_strength": g["polish_img2img"]["strength"],
            "seed": g["seed"],
            "sha256_design": p["versions"][0]["sha256"],
            "positive_prompt": g["prompt"],
            "negative_prompt": g["negative_prompt"],
            "passport_id": p["passport_id"],
        })
    for lst in items.values():
        lst.sort(key=lambda v: v["variant_index"])
    data = {"_meta": {"source": "outputs/passports/ (Design Passport)", "note": "Dữ liệu demo cho cổng cũ; không có chỉ số similarity vì luồng hiện tại không đo."},
            "items": items}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Đã ghi {OUT.relative_to(ROOT)}: {len(items)} hiện vật, {sum(len(v) for v in items.values())} biến thể")
    return 0


if __name__ == "__main__":
    sys.exit(main())
