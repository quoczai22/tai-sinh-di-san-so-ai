"""Thí nghiệm: in mặt nạ vùng in của từng thiết kế, mô phỏng đúng cách pipeline tính, không sửa pipeline.

"Vùng in" là phần áo mà hoa văn được phép phủ lên. Pipeline (tsds/pipeline/run.py) tính nó như sau, script này lặp lại đúng từng bước:
  1. Lấy áo nền (garment.png) và vùng áo SAM (garment_mask.png, 0/255 đọc lại thành 0/1) của một lần chạy có sẵn.
  2. Với mỗi thiết kế: ghép hoa văn V<n>_pattern.png theo cả 7 bố cục, CLIP chấm điểm và xếp hạng (layout_select.rank).
  3. Chọn bố cục điểm cao nhất mà các thiết kế trước chưa dùng (bố cục khóa cứng trong manifest thì giữ nguyên).
  4. Mặt nạ vùng in = garment._layout_mask(áo, bố cục, vùng áo). Giá trị 0 đến 1, mép nhòe dần, không tràn ra ngoài áo.

Script chỉ đọc lần chạy cũ, không gọi SD hay LoRA, nên chạy được trên CPU (CLIP chạy vài giây mỗi thiết kế).
Ngoài mặt nạ còn có hai phép kiểm chứng với lần chạy thật:
  khớp bố cục : bố cục script chọn có trùng bố cục ghi trong manifest.json không
  đổi ngoài vùng: tỉ lệ pixel ảnh ghép thô thật (V<n>_aodai_raw.png) khác áo nền mà nằm ngoài mặt nạ. Gần 0 nghĩa là mặt nạ khớp.

    uv run python scripts/eval/print_region_mask.py                          # lần chạy mới nhất
    uv run python scripts/eval/print_region_mask.py R20261121T160957-HV07

Kết quả: outputs/experiments/print_region_mask/<run_id>/ gồm V<n>_mask.png (xám, 255 là in đủ đậm), V<n>_mask_overlay.png (tô đỏ)
và print_region_masks.png (bảng tổng hợp).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.docs.build_pipeline_figure import (    # noqa: E402  dùng chung phông, khung ảnh và hàm tô đỏ với hình pipeline
    ACCENT, BG, INK, LINE, MUTED, PAD, draw_wrapped, fit, font, latest_run, red_overlay)
from tsds.generation.garment import garment, layout_select    # noqa: E402

RUNS = ROOT / "outputs" / "runs"
OUT = ROOT / "outputs" / "experiments" / "print_region_mask"
OUTSIDE_LEVEL = 0.01   # dưới mức này coi là ngoài vùng in khi kiểm chứng
DIFF_LEVEL = 2        # chênh lệch tối đa kênh màu (thang 0 đến 255) mới tính là pixel đã đổi


def choose_layout(ranked: list[dict], used: set[str], fixed: str | None = None) -> tuple[dict, str]:
    """Chọn bố cục như run.py: khóa cứng thì lấy đúng bố cục đó, không thì lấy bố cục điểm cao nhất chưa dùng."""
    if fixed:
        return next(x for x in ranked if x["layout"] == fixed), "fixed"
    return next((x for x in ranked if x["layout"] not in used), ranked[0]), "clip_auto"


def outside_ratio(raw: Image.Image, template: Image.Image, mask: np.ndarray) -> float:
    """Tỉ lệ pixel đã đổi (so với áo nền) nằm ngoài vùng in. Không có pixel nào đổi thì trả 0."""
    diff = np.abs(np.asarray(raw.convert("RGB"), np.int16) - np.asarray(template.convert("RGB"), np.int16)).max(axis=2)
    changed = diff > DIFF_LEVEL
    return float((changed & (mask < OUTSIDE_LEVEL)).sum() / max(int(changed.sum()), 1))


def simulate(run_dir: Path) -> list[dict]:
    """Mô phỏng bước chọn bố cục và tính mặt nạ cho từng thiết kế đã hoàn thành của lần chạy."""
    m = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    tpl_path = run_dir / "garment.png"
    tpl = Image.open(tpl_path).convert("RGB")
    region = (np.asarray(Image.open(run_dir / "garment_mask.png").convert("L")) > 127).astype(np.uint8)
    used: set[str] = set()
    rows = []
    for des in (d for d in m["designs"] if d["status"] == "completed"):
        n = des["variant_index"]
        pattern = Image.open(run_dir / f"V{n}_pattern.png")
        ranked = layout_select.rank(pattern, template_path=tpl_path, garment_region=region)
        fixed = des["layout"] if des.get("layout_selected_by") == "fixed" else None
        chosen, selected_by = choose_layout(ranked, used, fixed)
        used.add(chosen["layout"])
        mask = garment._layout_mask(tpl, garment.get_layout(chosen["layout"]), region)
        rows.append({"variant_index": n, "layout": chosen["layout"], "label": chosen["label"], "selected_by": selected_by,
                     "run_layout": des["layout"], "match": chosen["layout"] == des["layout"], "mask": mask,
                     "outside": outside_ratio(Image.open(run_dir / f"V{n}_aodai_raw.png"), tpl, mask)})
    return rows


def contact_sheet(run_dir: Path, rows: list[dict]) -> Image.Image:
    """Bảng tổng hợp: mỗi cột một thiết kế; hàng 1 mặt nạ xám, hàng 2 tô đỏ, hàng 3 ảnh ghép thô thật để đối chiếu."""
    tpl = Image.open(run_dir / "garment.png").convert("RGB")
    tw, th, gap, top = 260, 346, 16, 150
    W = PAD * 2 + 150 + len(rows) * (tw + gap)
    canvas = Image.new("RGB", (W, top + 3 * (th + gap) + 20), BG)
    d = ImageDraw.Draw(canvas)
    d.text((PAD, 24), "Mặt nạ vùng in của từng thiết kế", font=font(26, True), fill=INK)
    d.text((PAD, 62), f"Lần chạy {run_dir.name}  ·  mô phỏng lại bước chọn bố cục và garment._layout_mask của pipeline",
           font=font(15), fill=MUTED)
    labels = ["Mặt nạ (trắng là in đủ đậm)", "Tô đỏ vùng in (viền ở mức 0.5)", "Ảnh ghép thô thật của lần chạy"]
    for r, text in enumerate(labels):
        draw_wrapped(d, (PAD, top + r * (th + gap) + th // 2 - 20), text, font(14, True), INK, 17)
    for c, row in enumerate(rows):
        x = PAD + 150 + c * (tw + gap)
        d.text((x, 94), f"Thiết kế {row['variant_index']}: {row['label']}", font=font(15, True), fill=ACCENT)
        ok = "khớp lần chạy thật" if row["match"] else f"LỆCH: lần chạy thật dùng {row['run_layout']}"
        d.text((x, 118), f"{ok} · đổi ngoài vùng {row['outside']:.2%}", font=font(12), fill=MUTED)
        gray = Image.fromarray((np.clip(row["mask"], 0, 1) * 255).round().astype(np.uint8)).convert("RGB")
        tiles = [gray, red_overlay(tpl, row["mask"]), Image.open(run_dir / f"V{row['variant_index']}_aodai_raw.png")]
        for r, img in enumerate(tiles):
            y = top + r * (th + gap)
            canvas.paste(fit(img, tw, th), (x, y))
            d.rectangle([x - 1, y - 1, x + tw, y + th], outline=LINE)
    return canvas


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="In mặt nạ vùng in của từng thiết kế, mô phỏng đúng cách pipeline tính")
    ap.add_argument("run", nargs="?", help="mã lần chạy trong outputs/runs/ (bỏ trống là lần chạy mới nhất)")
    args = ap.parse_args(argv)
    run_dir = RUNS / args.run if args.run else latest_run()
    rows = simulate(run_dir)
    out = OUT / run_dir.name
    out.mkdir(parents=True, exist_ok=True)
    tpl = Image.open(run_dir / "garment.png").convert("RGB")
    for row in rows:
        n, mask = row["variant_index"], row["mask"]
        Image.fromarray((np.clip(mask, 0, 1) * 255).round().astype(np.uint8)).save(out / f"V{n}_mask.png")
        red_overlay(tpl, mask).save(out / f"V{n}_mask_overlay.png")
        print(f"V{n}: {row['layout']:<16} chọn bởi {row['selected_by']:<9} "
              f"{'khớp' if row['match'] else 'LỆCH (thật: ' + row['run_layout'] + ')'}  đổi ngoài vùng {row['outside']:.2%}")
    contact_sheet(run_dir, rows).save(out / "print_region_masks.png")
    print(out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
