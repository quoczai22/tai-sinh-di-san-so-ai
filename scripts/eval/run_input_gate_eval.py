# -*- coding: utf-8 -*-
"""Đo cổng kiểm tra ảnh đầu vào trên tập thử data/eval/input_filter/ (xem scripts/eval/prepare_input_gate_data.py).

Cách làm:
  1. Nhúng mọi ảnh trong labels.csv bằng CLIP, chấm theo nguyên mẫu (s_proto).
     Đo kiểu "bỏ một bình ra": ảnh của bình X được chấm với nguyên mẫu đã loại hết ảnh của bình X.
  2. Chọn MỘT ngưỡng trên các ảnh split=tune: điểm giữa của phân vị thấp (mặc định 10%) điểm ảnh hợp lệ
     và phân vị cao (mặc định 90%) điểm ảnh lạc đề. Điểm >= ngưỡng là pass, thấp hơn là block.
  3. Chấm trên split=test, in bảng từng nhóm kèm khoảng tin cậy Wilson 95%.
Kết quả: outputs/experiments/input_gate/results.csv (từng ảnh) và summary.json. Thêm --write-config để ghi ngưỡng vào config/input_gate.json.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))       # chạy từ thư mục gốc repo vẫn import được tsds
from tsds.core.paths import EXPERIMENTS_DIR, ROOT
from tsds.quality import input_gate as G

EVAL = ROOT / "data" / "eval" / "input_filter"
OUT = EXPERIMENTS_DIR / "input_gate"


def threshold(pos: np.ndarray, neg: np.ndarray, q_pos: float, q_neg: float) -> float:
    """Ngưỡng duy nhất: điểm giữa của phân vị q_pos điểm ảnh hợp lệ (pos) và phân vị q_neg điểm ảnh lạc đề (neg), trên tune."""
    return float((np.percentile(pos, q_pos) + np.percentile(neg, q_neg)) / 2)


def score_rows(rows: list[dict], cfg: dict) -> list[dict]:
    imgs = [Image.open(EVAL / "images" / r["file"]) for r in rows]
    emb = G.embed_images(imgs)
    protos, objs = G.load_prototypes()
    objs_arr = np.array(objs)
    exclude = np.stack([objs_arr == r["object_id"] if r["object_id"] else np.zeros(len(objs), bool) for r in rows])
    sp = G.score_p(emb, protos, k=cfg["P"]["k"], exclude=exclude)
    return [{**r, "s_proto": float(sp[i])} for i, r in enumerate(rows)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--q-pos", type=float, default=10.0, help="phân vị của điểm ảnh hợp lệ dùng để đặt ngưỡng")
    ap.add_argument("--q-neg", type=float, default=90.0, help="phân vị của điểm ảnh lạc đề dùng để đặt ngưỡng")
    ap.add_argument("--write-config", action="store_true")
    args = ap.parse_args()

    cfg = G.load_config()
    with open(EVAL / "labels.csv", encoding="utf-8", newline="") as f:
        rows = score_rows(list(csv.DictReader(f)), cfg)

    # Chọn ngưỡng trên tune
    tune = [r for r in rows if r["split"] == "tune"]
    pos = np.array([r["s_proto"] for r in tune if r["label_expected"] == "pass"])
    neg = np.array([r["s_proto"] for r in tune if r["label_expected"] == "block"])
    if len(pos) == 0 or len(neg) == 0:
        raise SystemExit(f"Tập tune thiếu ảnh {'hợp lệ' if len(pos) == 0 else 'lạc đề'}: chưa chọn được ngưỡng.")
    t = threshold(pos, neg, args.q_pos, args.q_neg)

    for r in rows:
        r["verdict"] = G.verdict(r["s_proto"], t)

    OUT.mkdir(parents=True, exist_ok=True)
    cols = ["file", "group", "label_expected", "split", "object_id", "s_proto", "verdict"]
    with open(OUT / "results.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows([{**r, "s_proto": round(r["s_proto"], 4)} for r in rows])

    summary = {"threshold": t, "tables": {}}
    print(f"Ngưỡng chọn trên tune: {t:.4f}")
    for split in ("tune", "test"):
        print(f"\n[{split}]")
        print(f"{'nhóm':<6}{'n':>4}{'pass':>6}{'block':>7}   tỉ lệ đúng (khoảng 95%)")
        for g in "ABCD":
            sub = [r for r in rows if r["split"] == split and r["group"] == g]
            if not sub:
                continue
            cnt = {v: sum(r["verdict"] == v for r in sub) for v in ("pass", "block")}
            want = "block" if g == "D" else "pass"
            lo, hi = G.wilson(cnt[want], len(sub))
            print(f"{g:<6}{len(sub):>4}{cnt['pass']:>6}{cnt['block']:>7}   {cnt[want] / len(sub):.0%} ({lo:.0%} đến {hi:.0%})")
            summary["tables"].setdefault(split, {})[g] = {"n": len(sub), **cnt}
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")

    n_d = sum(r["group"] == "D" for r in rows)
    if n_d < 30:
        print(f"\nCẢNH BÁO: nhóm D mới có {n_d} ảnh (cần 30 đến 40). Ngưỡng và bảng chỉ để thử luồng, chưa dùng làm kết quả.")
    if args.write_config:
        # Hậu tố "-proto" ghi cách chấm (chỉ nguyên mẫu); đổi cách chấm thì đổi hậu tố để log tự phân biệt bản cổng
        cfg = {"version": f"input-gate/{date.today():%Y%m%d}-proto", "calibrated": n_d >= 30, "note": cfg.get("note", ""),
               "P": {"k": cfg["P"]["k"], "t": t}}
        (ROOT / "config" / "input_gate.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Đã ghi config/input_gate.json")


if __name__ == "__main__":
    main()
