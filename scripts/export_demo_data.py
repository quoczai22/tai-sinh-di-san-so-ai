# -*- coding: utf-8 -*-
"""Xuất dữ liệu thực nghiệm thật từ evaluation/variants.csv sang JSON tĩnh cho chế độ Demo.

Kiểm tra nghiêm ngặt sự tồn tại của từng file ảnh thiết kế trong
web_ui/assets/images/variants/ (và ảnh hiện vật gốc). Nếu thiếu bất kỳ ảnh nào
sẽ báo lỗi và dừng ngay (exit code != 0), không bỏ qua im lặng.
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if getattr(_s, "encoding", "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "evaluation" / "variants.csv"
METADATA_PATH = ROOT / "data" / "heritage" / "metadata.json"
WEB_UI_DIR = ROOT / "web_ui"
VARIANTS_IMG_DIR = WEB_UI_DIR / "assets" / "images" / "variants"
HERITAGE_IMG_DIR = WEB_UI_DIR / "assets" / "images" / "heritage"
OUT_DEMO_JSON = WEB_UI_DIR / "assets" / "data" / "demo_variants.json"
OUT_HERITAGE_JSON = WEB_UI_DIR / "assets" / "data" / "heritage_items.json"

INT_FIELDS = {"variant_index", "intensity_level", "seed", "n_edge_px", "steps"}
FLOAT_FIELDS = {
    "controlnet_weight",
    "layout_scale",
    "layout_score",
    "polish_strength",
    "similarity_pattern_vs_ceramic",
    "aesthetic_score",
    "guidance",
    "duration_s",
}


def _parse_value(key: str, raw: str):
    if key in INT_FIELDS:
        return int(raw)
    if key in FLOAT_FIELDS:
        return float(raw)
    return raw


def export_demo_variants() -> dict:
    if not CSV_PATH.is_file():
        raise FileNotFoundError(f"Không tìm thấy file CSV thực nghiệm: {CSV_PATH}")

    by_heritage: dict[str, list[dict]] = {}
    with CSV_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_num, row in enumerate(reader, start=2):
            parsed = {k: _parse_value(k, v) for k, v in row.items()}
            heritage_id = parsed["heritage_id"]
            variant_index = parsed["variant_index"]
            filename = f"{heritage_id}_V{variant_index}_aodai.png"
            web_img_path = VARIANTS_IMG_DIR / filename

            if not web_img_path.is_file():
                # Thử kiểm tra trong outputs/variants/ nếu chưa copy sang web_ui
                out_img_path = ROOT / parsed["design_path"]
                if out_img_path.is_file():
                    VARIANTS_IMG_DIR.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(out_img_path, web_img_path)
                else:
                    raise FileNotFoundError(
                        f"[Dòng {row_num}] Thiếu ảnh thiết kế tham chiếu cho {heritage_id} V{variant_index}: "
                        f"không tồn tại ở {web_img_path} lẫn {out_img_path}"
                    )

            full_sha256 = hashlib.sha256(web_img_path.read_bytes()).hexdigest()
            csv_sha = str(parsed.get("sha256_design", "")).strip()
            if csv_sha and not full_sha256.startswith(csv_sha):
                raise ValueError(
                    f"[Dòng {row_num}] Hash SHA-256 của ảnh {web_img_path.name} ({full_sha256[:16]}) "
                    f"không khớp với giá trị trong variants.csv ({csv_sha})."
                )

            rel_web_path = f"assets/images/variants/{filename}"
            parsed["sha256_csv"] = csv_sha
            parsed["sha256_design"] = full_sha256
            parsed["design_path"] = rel_web_path
            parsed["image_url"] = f"./{rel_web_path}"

            by_heritage.setdefault(heritage_id, []).append(parsed)

    if not by_heritage:
        raise RuntimeError("File evaluation/variants.csv rỗng, không có dữ liệu để xuất.")

    for heritage_id, variants in by_heritage.items():
        variants.sort(key=lambda item: item["variant_index"])
        if len(variants) != 4:
            raise ValueError(
                f"Hiện vật {heritage_id!r} có {len(variants)} biến thể (yêu cầu đúng 4 biến thể V1..V4)."
            )

    payload = {
        "_meta": {
            "source": "evaluation/variants.csv",
            "note": "Kết quả thực nghiệm thật đã sinh sẵn — không phải sinh trực tiếp.",
            "label": "Kết quả đã sinh sẵn — không phải sinh trực tiếp",
        },
        "items": by_heritage,
    }
    OUT_DEMO_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_DEMO_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def export_heritage_catalog() -> list[dict]:
    if not METADATA_PATH.is_file():
        raise FileNotFoundError(f"Không tìm thấy metadata hiện vật: {METADATA_PATH}")

    raw = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    items_dict = raw.get("items", {})
    HERITAGE_IMG_DIR.mkdir(parents=True, exist_ok=True)

    catalog = []
    for heritage_id, item in items_dict.items():
        src_img = ROOT / item["image_path"]
        if not src_img.is_file():
            raise FileNotFoundError(f"Thiếu ảnh hiện vật gốc cho {heritage_id}: {src_img}")
        dst_img = HERITAGE_IMG_DIR / src_img.name
        if not dst_img.is_file() or dst_img.stat().st_size != src_img.stat().st_size:
            shutil.copy2(src_img, dst_img)

        catalog.append({
            "id": item["heritage_id"],
            "name": item["name"],
            "dynasty": "Di sản Bát Tràng",
            "description": item.get("team_description", ""),
            "conditioningMode": item["conditioning_mode"],
            "image": f"./assets/images/heritage/{src_img.name}",
            "colors": [],
            "colorNames": [],
            "licenseNote": item["license_note"],
            "variantImageBase": f"./assets/images/variants/{item['heritage_id']}_V",
        })

    OUT_HERITAGE_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_HERITAGE_JSON.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return catalog


def main() -> int:
    demo = export_demo_variants()
    catalog = export_heritage_catalog()
    total_variants = sum(len(v) for v in demo["items"].values())
    print(f"Đã xuất {len(demo['items'])} hiện vật ({total_variants} thiết kế) -> {OUT_DEMO_JSON.relative_to(ROOT)}")
    print(f"Đã xuất {len(catalog)} mục danh mục hiện vật -> {OUT_HERITAGE_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
