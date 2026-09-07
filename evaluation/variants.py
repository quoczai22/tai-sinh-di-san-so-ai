# -*- coding: utf-8 -*-
"""Sinh BỘ MẪU cho một hiện vật — người dùng chọn một trong nhiều thiết kế.

Mỗi biến thể khác nhau ở ba trục:
  · Creative Intensity  → mức biến tấu hoa văn (ControlNet weight)
  · Bảng màu            → giữ nguyên màu hiện vật, hay để SD tự chọn
  · Bố trí trên áo      → thân trước, gấu tà, vai, phủ toàn thân...

Biến thể 1 LUÔN giữ nguyên bảng màu hiện vật gốc — đây là mẫu "trung thành" để
người dùng có mốc đối chiếu. Các biến thể sau được tự do.

Chạy:
    python -m evaluation.variants --item BT_Hac_XP
    python -m evaluation.variants --item BT_Hac_XP --layouts       # xem cac layout
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if getattr(_s, "encoding", "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from generation import controlnet as cn, garment, layout_select, palette, pattern  # noqa: E402

OUT_DIR = ROOT / "outputs" / "variants"
CSV_FILE = ROOT / "evaluation" / "variants.csv"
SEED = 42
POLISH_STRENGTH = 0.40      # 0,25-0,35 giu net hon; >0,45 bat dau bien dang hoa van

# Bốn biến thể theo Creative Intensity. Bố cục KHÔNG cố định sẵn — với mỗi hoa
# văn, hệ thống ghép thử cả 7 bố cục rồi chọn cái điểm cao nhất chưa dùng
# (generation/layout_select.py). Nhờ vậy mỗi hiện vật tự có bộ bố trí riêng.
#
# Biến thể 1 luôn giữ bảng màu hiện vật gốc — mốc trung thành để đối chiếu.
VARIANTS = [
    {"level": 1, "palette": "original"},
    {"level": 2, "palette": "free"},
    {"level": 3, "palette": "free"},
    {"level": 4, "palette": "free"},
]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--item", required=False, default="BT_Hac_XP")
    ap.add_argument("--layouts", action="store_true", help="liet ke layout roi thoat")
    args = ap.parse_args()

    if args.layouts:
        cfg = garment.load_layouts()
        for k, v in cfg["layouts"].items():
            print(f"  {k:18} {v['label']:22} scale={v['scale']}  {len(v['regions'])} vung")
        print(f"\n  mac dinh: {cfg.get('default')}")
        return 0

    hid = args.item
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prep = cn.prepare(hid, ornament_only=True, trim=True)
    prep["reference"].save(OUT_DIR / f"{hid}_00_ref.png")
    prep["control"].save(OUT_DIR / f"{hid}_01_canny.png")
    print(f"[{hid}] {prep['mode']} | {prep['n_edge_px']:,} px canh | "
          f"alpha={'co' if prep['has_alpha'] else 'khong'}")

    src_colors = palette.dominant_colors(prep["reference"], prep["reference_mask"])
    print(f"  Bang mau hien vat: {src_colors}")

    from generation.stable_diffusion import Generator          # noqa: PLC0415
    from evaluation.intensity_sweep import Scorer              # noqa: PLC0415
    gen = Generator()
    ver = gen.versions()
    sc = Scorer()

    rows = []
    used: set[str] = set()
    print("\n[SINH BO MAU]  (bo cuc do he thong tu chon cho tung hoa van)")
    for i, v in enumerate(VARIANTS, 1):
        r = pattern.generate(gen, hid, v["level"], SEED, prepared=prep)
        pat = r["image"]
        if v["palette"] == "original":
            pat = palette.match_palette(pat, prep["reference"], prep["reference_mask"])
        pat_path = OUT_DIR / f"{hid}_V{i}_pattern.png"
        pat.save(pat_path)

        ranked = layout_select.rank(pat)
        pick = next((x for x in ranked if x["layout"] not in used), ranked[0])
        used.add(pick["layout"])
        design = pick["image"]
        design.save(OUT_DIR / f"{hid}_V{i}_aodai_raw.png")
        # Luot hoan thien: hoa hoa van vao soi vai, pha tinh lap may moc cua
        # lat gach. Ghep anh thuan khong lam duoc ba viec do.
        design = garment.polish(design, strength=POLISH_STRENGTH, seed=SEED)
        des_path = OUT_DIR / f"{hid}_V{i}_aodai.png"
        design.save(des_path)

        sim = sc.similarity(prep["reference"], pat)
        aes = sc.aesthetic(design)
        lay = garment.get_layout(pick["layout"])
        top3 = " > ".join(f"{x['layout']}({x['score']:+.3f})" for x in ranked[:3])
        print(f"  V{i}  L{v['level']} w={r['weight']:<5} mau={v['palette']:<8} "
              f"{lay['label']:22} sim={sim:.4f}  {r['duration_s']:.1f}s")
        print(f"      xep hang bo cuc: {top3}")

        rows.append({
            "variant": f"{hid}_V{i}",
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "aesthetic_impl": "clip_proxy_NOT_laion",
            "translator_mode": "not_used",
            "heritage_id": hid, "variant_index": i,
            "intensity_level": v["level"], "level_name": r["level_name"],
            "controlnet_weight": r["weight"],
            "palette_mode": v["palette"], "layout": pick["layout"],
            "layout_label": lay["label"], "layout_scale": lay["scale"],
            "layout_selected_by": "clip_auto", "layout_score": pick["score"],
            "layout_ranking": ";".join(f"{x['layout']}:{x['score']}" for x in ranked),
            "polish_strength": POLISH_STRENGTH,
            "seed": SEED, "similarity_pattern_vs_ceramic": round(sim, 4),
            "aesthetic_score": aes,
            "source_palette": ";".join(f"#{r_:02x}{g_:02x}{b_:02x}" for r_, g_, b_ in src_colors),
            "n_edge_px": prep["n_edge_px"], "control_mode": prep["mode"],
            "positive_prompt": r["positive_prompt"],
            "negative_prompt": r["negative_prompt"],
            "steps": ver["steps"], "guidance": ver["guidance"],
            "sd_model_id": ver["sd_model_id"], "controlnet_id": ver["controlnet_id"],
            "torch_version": ver["torch"], "diffusers_version": ver["diffusers"],
            "gpu": ver["gpu"], "duration_s": round(r["duration_s"], 2),
            "pattern_path": str(pat_path.relative_to(ROOT)).replace("\\", "/"),
            "design_path": str(des_path.relative_to(ROOT)).replace("\\", "/"),
            "sha256_design": sha256(des_path),
        })
    gen.close()
    garment.free_polish_pipe()

    write_header = not CSV_FILE.exists()
    with open(CSV_FILE, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        if write_header:
            w.writeheader()
        w.writerows(rows)
    print(f"\n  {len(rows)} bien the -> {OUT_DIR.relative_to(ROOT)}")
    print(f"  Nhat ky -> {CSV_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
