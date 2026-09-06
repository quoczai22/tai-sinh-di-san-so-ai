# -*- coding: utf-8 -*-
"""CREATIVE INTENSITY SWEEP — thực nghiệm chính của v6 mục 8.

Câu hỏi: Similarity và Aesthetic đánh đổi nhau thế nào khi đổi Creative Intensity?

Thiết kế một biến số: cùng heritage, cùng seed, cùng ảnh điều kiện — CHỈ đổi
ControlNet weight theo 4 mức. Áo dài giữ nguyên một ảnh mẫu cho mọi thiết kế nên
khác biệt không thể đến từ việc SD vẽ cái áo khác đi.

Chạy:
    python -m evaluation.intensity_sweep
    python -m evaluation.intensity_sweep --items BT001,BT008 --dry-run
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

for _s in (sys.stdout, sys.stderr):
    if getattr(_s, "encoding", "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from generation import controlnet as cn, garment, pattern      # noqa: E402

OUT_DIR = ROOT / "outputs" / "sweep"
CSV_FILE = ROOT / "evaluation" / "intensity_sweep.csv"
DEFAULT_ITEMS = ["BT001", "BT008", "BT010"]
SEED = 42

# Khâu duy nhất trong v6 cần LLM. Chưa có API nên để trống — ghi vào CSV để
# lần chạy này không bị đọc nhầm là đã chạy đủ pipeline (CLAUDE.md mục 11).
USER_DIRECTION = ""
TRANSLATOR_MODE = "not_used"


class Scorer:
    """CLIP dùng cho cả Similarity (mục 6.1) và Aesthetic thay thế (mục 6.2).

    LƯU Ý: đây CHƯA phải LAION-Aesthetics predictor mà v6 mục 6.2 yêu cầu. Ở đây
    dùng một proxy: độ khớp của ảnh với các cụm mô tả thẩm mỹ. Phải thay bằng
    predictor thật trước khi đưa số vào hồ sơ — cột `aesthetic_impl` ghi rõ điều đó.
    """
    GOOD = ["a beautiful elegant textile print design",
            "clean professional graphic design, well composed"]
    BAD = ["an ugly messy cluttered image", "a low quality amateur drawing"]

    def __init__(self) -> None:
        from transformers import CLIPModel, CLIPProcessor    # noqa: PLC0415
        self.m = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").eval()
        self.p = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        with torch.no_grad():
            t = self.p(text=self.GOOD + self.BAD, return_tensors="pt", padding=True)
            self.te = F.normalize(self.m.text_projection(self.m.text_model(**t).pooler_output), dim=-1)

    @torch.no_grad()
    def embed(self, img: Image.Image) -> torch.Tensor:
        i = self.p(images=img, return_tensors="pt")
        return F.normalize(self.m.visual_projection(self.m.vision_model(**i).pooler_output), dim=-1)[0]

    def similarity(self, a: Image.Image, b: Image.Image) -> float:
        return float(self.embed(a) @ self.embed(b))

    def aesthetic(self, img: Image.Image) -> float:
        """Trả về thang 0-10 cho dễ đọc. Proxy, không phải LAION-Aesthetics."""
        s = self.embed(img) @ self.te.T
        good, bad = s[:len(self.GOOD)].mean(), s[len(self.GOOD):].mean()
        return round(float((good - bad + 0.1) * 50), 2)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", default=",".join(DEFAULT_ITEMS))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    ids = [x.strip() for x in args.items.split(",") if x.strip()]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Dựng prompt TRƯỚC khi nạp model — lỗi ngân sách token phải nổ ra ngay.
    print("[GIAI DOAN 1 — prompt hoa van]")
    for hid in ids:
        for lv in pattern.INTENSITY:
            s = pattern.build_prompt(hid, lv, USER_DIRECTION)
            if lv == 1:
                print(f"\n  {hid}  w={s['weight']}  {s['positive_prompt']}")
            else:
                print(f"  {'':7}  w={s['weight']}  muc {lv} — {s['level_name']}")
    if args.dry_run:
        return 0

    from generation.stable_diffusion import Generator          # noqa: PLC0415
    gen = Generator()
    ver = gen.versions()
    print(f"\n[MODEL] {gen.load_seconds:.0f}s | {ver['gpu']}")
    sc = Scorer()

    rows = []
    print("\n[SINH]")
    for hid in ids:
        prep = cn.prepare(hid, ornament_only=True, trim=True)
        prep["reference"].save(OUT_DIR / f"{hid}_00_ref.png")
        prep["control"].save(OUT_DIR / f"{hid}_01_canny_ornament.png")
        print(f"  {hid}: {prep['mode']}, mat do canh {prep['edge_density']:.2f}%")
        for lv in sorted(pattern.INTENSITY):
            r = pattern.generate(gen, hid, lv, SEED, USER_DIRECTION, prepared=prep)
            pat_path = pattern.save(r, OUT_DIR, f"{hid}_L{lv}_pattern")
            design = garment.apply(r["image"])
            des_path = OUT_DIR / f"{hid}_L{lv}_aodai.png"
            design.save(des_path)

            sim = sc.similarity(prep["reference"], r["image"])   # hoa van vs gom
            aes = sc.aesthetic(design)                            # tham my san pham
            print(f"    L{lv} {r['level_name']:16} w={r['weight']}  "
                  f"sim={sim:.4f}  aes={aes:5.2f}  {r['duration_s']:.1f}s")
            rows.append({
                "run_id": f"{hid}_L{lv}",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "translator_mode": TRANSLATOR_MODE,
                "aesthetic_impl": "clip_proxy_NOT_laion",
                "heritage_id": hid, "intensity_level": lv, "level_name": r["level_name"],
                "controlnet_weight": r["weight"], "seed": SEED,
                "similarity_pattern_vs_ceramic": round(sim, 4), "aesthetic_score": aes,
                "control_mode": r["control_mode"],
                "edge_density_pct": round(prep["edge_density"], 2),
                "crop_box": str(prep["crop_box"]),
                "positive_prompt": r["positive_prompt"],
                "negative_prompt": r["negative_prompt"],
                "user_direction": USER_DIRECTION,
                "steps": ver["steps"], "guidance": ver["guidance"],
                "canny_low": cn.CANNY_LOW, "canny_high": cn.CANNY_HIGH,
                "resolution": cn.RESOLUTION,
                "sd_model_id": ver["sd_model_id"], "controlnet_id": ver["controlnet_id"],
                "scheduler": ver["scheduler"], "torch_version": ver["torch"],
                "diffusers_version": ver["diffusers"], "gpu": ver["gpu"],
                "duration_s": round(r["duration_s"], 2),
                "peak_vram_gb": round(r["peak_vram_gb"], 2),
                "pattern_path": str(pat_path.relative_to(ROOT)).replace("\\", "/"),
                "design_path": str(des_path.relative_to(ROOT)).replace("\\", "/"),
                "sha256_design": sha256(des_path),
            })
    gen.close()

    with open(CSV_FILE, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

    print(f"\n[DUONG CONG DANH DOI]  (mục 8 — quan sát sơ bộ, không phải kết luận thống kê)")
    print(f"  {'':8}" + "".join(f"{'L'+str(l):>18}" for l in sorted(pattern.INTENSITY)))
    for hid in ids:
        r = [x for x in rows if x["heritage_id"] == hid]
        print(f"  {hid:8}" + "".join(
            f"{x['similarity_pattern_vs_ceramic']:>10.3f}/{x['aesthetic_score']:<7.1f}" for x in r))
    d = [x for x in rows if x["intensity_level"] in (1, 4)]
    s1 = np.mean([x["similarity_pattern_vs_ceramic"] for x in d if x["intensity_level"] == 1])
    s4 = np.mean([x["similarity_pattern_vs_ceramic"] for x in d if x["intensity_level"] == 4])
    a1 = np.mean([x["aesthetic_score"] for x in d if x["intensity_level"] == 1])
    a4 = np.mean([x["aesthetic_score"] for x in d if x["intensity_level"] == 4])
    print(f"\n  Muc 1 -> Muc 4:  similarity {s1:.3f} -> {s4:.3f} ({s4-s1:+.3f})"
          f"  |  aesthetic {a1:.2f} -> {a4:.2f} ({a4-a1:+.2f})")
    print(f"\n  {len(rows)} dong -> {CSV_FILE.relative_to(ROOT)}")
    print(f"  Anh -> {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
