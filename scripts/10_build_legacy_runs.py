# -*- coding: utf-8 -*-
"""Dựng lại hồ sơ truy vết cho lần chạy 06/09/2026 (24 thiết kế) + chạy Quality Gate.

Không sinh ảnh mới bằng AI, không cần GPU. Script:
  1. Đối chiếu từng ảnh cuối với mã băm 16 ký tự trong evaluation/variants.csv để
     tìm ĐÚNG bộ ảnh của lần chạy đã ghi nhật ký (bản trong web_ui/assets khớp
     24/24; bản trong outputs/variants chỉ khớp 4/24 vì bị một lần chạy qua API
     ghi đè cùng tên tệp — đây là nguyên nhân lỗi "không tái lập" BTC nêu).
  2. Tạo manifest cho mỗi run (outputs/runs/<run_id>/manifest.json).
  3. Chạy Cổng G2 (hoa văn) và G3 (thiết kế cuối) trên từng thiết kế.
  4. Với thiết kế FAIL ở G3 nhưng đạt G2: tạo bản sửa tất định "khoá họa tiết"
     (quality/repair.py) và đo lại.
  5. Dựng Design Passport đầy đủ (outputs/passports/) và bảng tổng hợp
     evaluation/quality_gate_legacy.csv.
  6. Xuất tờ đối chiếu ảnh đầu vào → hoa văn → bản ghép → áo cuối (→ bản sửa)
     cho phiếu nhận xét chuyên gia (docs/evidence/quality_gate/).

    python scripts/10_build_legacy_runs.py
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from generation import garment                                   # noqa: E402
from provenance import passport as P                             # noqa: E402
from provenance.builder import build_design_passport             # noqa: E402
from provenance.hashing import sha256_file                       # noqa: E402
from provenance.labeling import _font                            # noqa: E402
from provenance.registry import load_registry                    # noqa: E402
from quality import gate as QG                                   # noqa: E402
from quality.assess import assess_design                         # noqa: E402

CSV_FILE = ROOT / "evaluation" / "variants.csv"
OUT_CSV = ROOT / "evaluation" / "quality_gate_legacy.csv"
RUNS = ROOT / "outputs" / "runs"
PASSPORTS = ROOT / "outputs" / "passports"
SHEETS = ROOT / "docs" / "evidence" / "quality_gate"
TERMS = json.loads((ROOT / "data" / "prompt_terms.json").read_text(encoding="utf-8"))
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")


def arr(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def stamp(ts: str) -> str:
    return datetime.fromisoformat(ts).strftime("%Y%m%dT%H%M%S")


def contact_sheet(paths: list[tuple[str, Path]], title: str, out: Path) -> None:
    size = 256
    sheet = Image.new("RGB", (size * len(paths), size + 46), (250, 247, 240))
    draw = ImageDraw.Draw(sheet)
    font = _font(13)
    draw.text((6, 4), title, fill=(30, 40, 50), font=font)
    for i, (label, path) in enumerate(paths):
        im = Image.open(path).convert("RGB")
        im.thumbnail((size, size))
        sheet.paste(im, (i * size + (size - im.width) // 2, 24))
        draw.text((i * size + 6, size + 26), label, fill=(60, 70, 80), font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=86)


def main() -> int:
    rows = list(csv.DictReader(CSV_FILE.open(encoding="utf-8")))
    registry = load_registry(ROOT)["items"]
    cfg = QG.load_config()
    out_rows = []
    by_item: dict[str, list[dict]] = {}
    for r in rows:
        by_item.setdefault(r["heritage_id"], []).append(r)

    for hid, variants in by_item.items():
        item = registry[hid]
        code = item["code"]
        run_stamp = stamp(variants[0]["timestamp"])
        run_id = f"R{run_stamp}-{code}"
        run_dir = RUNS / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        ref_path = ROOT / f"outputs/variants/{hid}_00_ref.png"
        canny_path = ROOT / f"outputs/variants/{hid}_01_canny.png"
        src_rec = P.file_record(ROOT / item["image_path"], "source_image")
        ref_rec = P.file_record(ref_path, "reference_512")
        canny_rec = P.file_record(canny_path, "control_canny")
        manifest = {"schema": "run-manifest/1.0", "run_id": run_id, "heritage_id": hid, "code": code,
                    "source": "evaluation/variants.py (log: evaluation/variants.csv)",
                    "reconstructed_on": NOW, "artifacts": [src_rec, ref_rec, canny_rec], "designs": [],
                    "integrity": []}
        for r in variants:
            i = int(r["variant_index"])
            design_id = f"{run_id}.V{i}"
            pid = P.passport_id_for(code, run_stamp[:8], i)
            pat_path = ROOT / r["pattern_path"]
            raw_path = ROOT / f"outputs/variants/{hid}_V{i}_aodai_raw.png"
            fin_logged = ROOT / "web_ui/assets/images/variants" / Path(r["design_path"]).name
            fin_other = ROOT / r["design_path"]
            fin_sha = sha256_file(fin_logged)
            other_sha = sha256_file(fin_other)
            manifest["integrity"].append({
                "design_id": design_id, "logged_sha256_prefix": r["sha256_design"],
                "web_ui_copy_matches": fin_sha.startswith(r["sha256_design"]),
                "outputs_copy_matches": other_sha.startswith(r["sha256_design"]),
                "note": None if other_sha.startswith(r["sha256_design"]) else
                "Tệp cùng tên trong outputs/variants đã bị một lần chạy sau (API, không ghi nhật ký) ghi đè.",
            })
            assessment = assess_design(reference=ref_path, pattern=pat_path, raw=raw_path, final=fin_logged,
                                       layout=r["layout"], repair_dir=run_dir, repair_name=f"V{i}_pattern_lock.png",
                                       cfg=cfg)
            g2, g3, ov, repair = (assessment["G2_pattern"], assessment["G3_final"], assessment["overall"],
                                  assessment["repair"])
            rec = {**r, "pipeline": "two-stage v6 (evaluation/variants.py)"}
            paths = {"source": ROOT / item["image_path"], "reference": ref_path, "canny": canny_path,
                     "pattern": pat_path, "raw": raw_path, "final": fin_logged}
            pp = build_design_passport(item=item, run_id=run_id, run_stamp=run_stamp[:8], rec=rec, paths=paths,
                                       assessment=assessment, now=NOW, root=ROOT,
                                       polish_prompt=garment.POLISH_PROMPT, polish_negative=garment.POLISH_NEG)
            P.save(pp, PASSPORTS)
            manifest["designs"].append({"design_id": design_id, "passport_id": pid, "variant_index": i,
                                        "artifacts": [a for a in pp["artifacts"] if a["role"] in
                                                      ("pattern", "composite_raw", "final_img2img", "repair_pattern_lock")],
                                        "quality_decision": ov["decision"],
                                        "repair_decision": repair["overall"]["decision"] if repair else None})

            sheet = [("Hiện vật", ref_path), ("Hoa văn", pat_path), ("Bản ghép", raw_path), ("Áo cuối (img2img)", fin_logged)]
            if repair:
                sheet.append(("Bản sửa: khoá họa tiết", repair["path"]))
            contact_sheet(sheet, f"{pid} · {item['name']} · G2 {g2['decision']} · G3 {g3['decision']}"
                          + (f" → sửa: {repair['G3_final']['decision']}" if repair else ""),
                          SHEETS / f"{pid}.jpg")

            m2, m3 = g2["metrics"], g3["metrics"]
            out_rows.append({
                "passport_id": pid, "design_id": design_id, "heritage_id": hid, "heritage_status": item["status"],
                "variant": i, "controlnet_weight": r["controlnet_weight"], "layout": r["layout"],
                "vessel_leakage": m2["vessel_leakage"]["value"], "seam_ratio": m2["seam_ratio"]["value"],
                "G2": g2["decision"],
                "pattern_preservation": m3["pattern_preservation"]["value"],
                "structure_ncc": g3["details"]["structure_ncc"], "chroma_ncc": g3["details"]["chroma_ncc"],
                "garment_shape_iou": m3["garment_shape_iou"]["value"],
                "sharpness_ratio": m3["sharpness_ratio"]["value"], "palette_shift_de": m3["palette_shift_de"]["value"],
                "align_shift_px": g3["details"]["alignment"]["shift_px"], "G3": g3["decision"],
                "overall": ov["decision"], "route_to": ov["route_to"],
                "repair_pps": repair["G3_final"]["metrics"]["pattern_preservation"]["value"] if repair else "",
                "repair_G3": repair["G3_final"]["decision"] if repair else "",
                "approval_status": pp["approval"]["status"],
                "clip_similarity_ref": r["similarity_pattern_vs_ceramic"],
            })
            print(f"{pid:24} G2 {g2['decision']:4} G3 {g3['decision']:4} "
                  f"PPS {m3['pattern_preservation']['value']:+.3f} GSC {m3['garment_shape_iou']['value']:.3f} "
                  f"VLS {m2['vessel_leakage']['value']:.3f}"
                  + (f" | sửa → {repair['G3_final']['decision']} PPS {repair['G3_final']['metrics']['pattern_preservation']['value']:+.3f}" if repair else ""))
        (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0]))
        w.writeheader()
        w.writerows(out_rows)
    print(f"\n{len(out_rows)} thiết kế → {OUT_CSV.relative_to(ROOT)}; passport → {PASSPORTS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
