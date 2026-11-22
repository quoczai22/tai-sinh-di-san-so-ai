"""Thử cách hoàn thiện ảnh (polish và khóa họa tiết) trên các bản ghép thô của bộ demo hiện tại.

Với mỗi bản ghép thô trong outputs/runs/: polish có mặt nạ ở nhiều độ nhiễu, rồi (a) giữ nguyên, (b) khóa họa tiết
với dog_sigma_low 1,2 (cũ), (c) khóa họa tiết với dog_sigma_low 0,3 (hiện tại). Chấm cổng G3 cho từng biến thể.
Ghi tsds/evaluation/polish_finish_trial.csv. Cần GPU (polish chạy Stable Diffusion img2img).

    uv run python -m tsds.evaluation.polish_finish_trial
"""
from __future__ import annotations

import csv
import glob
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tsds.generation.garment import garment                                      # noqa: E402
from tsds.quality import gate as QG                                      # noqa: E402
from tsds.core.pattern_lock import PARAMS, pattern_lock                     # noqa: E402

OUT = ROOT / "tsds" / "evaluation" / "polish_finish_trial.csv"
STRENGTHS = (0.30, 0.20)
VARIANTS = {"polish": None, "lock_sigma_1.2": {"dog_sigma_low": 1.2}, "lock_sigma_0.3": {"dog_sigma_low": 0.3}}
DESIGNS = (2, 3)            # mỗi lần chạy lấy thiết kế mức 2 và 3 (cùng seed hoa văn, bố cục khác nhau)


def main() -> int:
    cfg = QG.load_config()
    rows = []
    for run in sorted(glob.glob(str(ROOT / "outputs" / "runs" / "R*"))):
        run = Path(run)
        man = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        tpl = Image.open(run / "garment.png").convert("RGB")
        region = (np.asarray(Image.open(run / "garment_mask.png").convert("L")) > 0).astype(np.uint8)
        for d in man["designs"]:
            if d["variant_index"] not in DESIGNS:
                continue
            raw = Image.open(run / f"V{d['variant_index']}_aodai_raw.png").convert("RGB")
            lay = garment._layout_mask(tpl, garment.get_layout(d["layout"]), region)
            raw_a, tpl_a = np.asarray(raw), np.asarray(tpl)
            for s in STRENGTHS:
                polished = np.asarray(garment.polish_masked(raw, strength=s, seed=42, mask=region).convert("RGB"))
                for name, params in VARIANTS.items():
                    img = polished if params is None else np.where(
                        (region > 0)[:, :, None], pattern_lock(raw_a, polished, lay, {**PARAMS, **params})[0], raw_a)
                    g3 = QG.evaluate_final(raw_a, img, tpl_a, lay, region, cfg)
                    m = g3["metrics"]
                    rows.append({"design": f"{run.name.split('-')[-1]}_V{d['variant_index']}", "strength": s, "variant": name,
                                 "pps": m["pattern_preservation"]["value"], "iou": m["garment_shape_iou"]["value"],
                                 "sharpness_ratio": m["sharpness_ratio"]["value"], "detail_ratio": m["detail_ratio"]["value"],
                                 "palette_shift_de": m["palette_shift_de"]["value"], "g3": g3["decision"]})
            print(run.name, d["variant_index"], flush=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"Ghi {len(rows)} dòng vào {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
