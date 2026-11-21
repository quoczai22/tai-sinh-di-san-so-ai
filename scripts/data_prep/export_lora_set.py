"""Xuất tập huấn luyện LoRA dáng áo dài từ VietFashion đã lọc (kế hoạch mục 6.3, bước 2).

Lấy các dòng trong data/raw/vietfashion/filtered/index.csv (do scripts/11 tạo) thỏa:
  · caption có "fitted" (thân ôm), · CLIP "người mặc áo dài" >= 0,8, · CLIP "tà dài" >= 0,7.
Ghi ảnh gốc 256x344 vào data/raw/vietfashion/lora_train/ kèm metadata.jsonl (file_name, text).
Giữ nguyên caption gốc, kể cả phần mô tả họa tiết: LoRA sẽ gắn họa tiết với chữ đó thay vì với "áo dài".

Chạy:  uv run python scripts/data_prep/export_lora_set.py
"""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "raw" / "vietfashion"
OUT = SRC / "lora_train"
CLIP_AO_DAI, CLIP_DAI = 0.8, 0.7


def chon(rows: list[dict]) -> list[dict]:
    """Giữ dòng ôm thân, giống áo dài và tà dài theo CLIP."""
    return [r for r in rows if re.search("fitted", r["caption"], re.I)
            and float(r["ao_dai_nguoi"]) >= CLIP_AO_DAI and float(r["dai_san"]) >= CLIP_DAI]


def main() -> int:
    import pyarrow.parquet as pq                                    # noqa: PLC0415
    from PIL import Image                                           # noqa: PLC0415
    rows = chon(list(csv.DictReader(open(SRC / "filtered" / "index.csv", encoding="utf-8"))))
    OUT.mkdir(parents=True, exist_ok=True)
    cache: dict[str, list] = {}
    with open(OUT / "metadata.jsonl", "w", encoding="utf-8") as meta:
        for n, r in enumerate(rows):
            if r["file"] not in cache:
                cache[r["file"]] = pq.read_table(SRC / "data" / r["file"], columns=["image"]).column("image").to_pylist()
            im = Image.open(io.BytesIO(cache[r["file"]][int(r["row"])]["bytes"])).convert("RGB")
            name = f"{n:04d}.png"
            im.save(OUT / name)
            meta.write(json.dumps({"file_name": name, "text": r["caption"], "source": f"{r['file']}#{r['row']}"},
                                  ensure_ascii=False) + "\n")
    print(f"Đã xuất {len(rows)} ảnh, {len({r['caption'] for r in rows})} caption khác nhau → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
