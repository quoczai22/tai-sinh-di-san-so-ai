"""Lọc ảnh VietFashion để huấn luyện LoRA dáng áo dài (kế hoạch mục 6.3).

Hai bước lọc:
  1. Caption: giữ ảnh có cổ trụ (mandarin collar), không không tay, không dây, tà không ngắn.
     Áo dài truyền thống có cổ trụ và dài quá gối; các kiểu khác trong dataset hay là váy, áo choàng.
  2. CLIP (openai/clip-vit-base-patch32): điểm "người mặc áo dài" so với ma-nơ-canh, váy, áo choàng, kimono.
     CLIP bản nhỏ chỉ phân biệt thô, nên kết quả luôn phải xem lại bằng mắt.

Chạy:  uv run python scripts/data_prep/filter_vietfashion.py [file.parquet ...]
Ghi data/raw/vietfashion/filtered/index.csv (chỉ số dòng, điểm, caption) và ảnh xem thử.
Dữ liệu VietFashion theo CC BY-NC 4.0, không commit (data/raw/vietfashion/ nằm trong .gitignore).
"""
from __future__ import annotations

import csv
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "data" / "raw" / "vietfashion" / "data"
OUT_DIR = ROOT / "data" / "raw" / "vietfashion" / "filtered"

# Caption bị loại nếu có cụm này (kiểu áo không phải áo dài truyền thống)
LOAI = re.compile(r"sleeveless|strapless|off[- ]shoulder|halter|spaghetti|\bshort(/midi)? tunic|\bmidi\b|\bmini\b|knee[- ]length|short length", re.I)
CO_TRU = re.compile(r"mandarin collar", re.I)

PROMPTS = {
    "ao_dai_nguoi": "a photo of a woman wearing a Vietnamese ao dai",
    "ma_no_canh": "a photo of a dress on a mannequin",
    "vay": "a photo of a woman wearing a long dress",
    "ao_choang": "a photo of a long coat or robe",
    "kimono": "a photo of a kimono",
}


# Cặp mô tả để chấm độ dài tà từ ảnh (caption ít khi nói rõ độ dài). Điểm "dai_san" là xác suất ở mô tả đầu.
PROMPTS_DAI = ["a photo of a long floor-length gown", "a photo of a short knee-length dress"]


def caption_ok(caption: str) -> tuple[bool, str]:
    """Lọc theo caption. Trả về (giữ hay không, lý do)."""
    if not CO_TRU.search(caption):
        return False, "không có cổ trụ"
    m = LOAI.search(caption)
    if m:
        return False, f"kiểu không phải áo dài truyền thống: {m.group(0)}"
    return True, ""


def clip_scores(images, prompts: dict | list | None = None, batch: int = 64) -> list[dict]:
    """Xác suất (softmax) của từng mô tả trong `prompts` (mặc định PROMPTS) cho mỗi ảnh PIL."""
    prompts = prompts if prompts is not None else PROMPTS
    prompts = prompts if isinstance(prompts, dict) else {t: t for t in prompts}
    import torch                                                    # noqa: PLC0415
    from transformers import CLIPModel, CLIPProcessor               # noqa: PLC0415
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(dev).eval()
    proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    out = []
    with torch.no_grad():
        for i in range(0, len(images), batch):
            inp = proc(text=list(prompts.values()), images=images[i:i + batch], return_tensors="pt", padding=True).to(dev)
            p = model(**inp).logits_per_image.softmax(dim=-1).cpu().numpy()
            out += [dict(zip(prompts, row.tolist())) for row in p]
    return out


def main(files: list[str]) -> int:
    import pyarrow.parquet as pq                                    # noqa: PLC0415
    from PIL import Image                                           # noqa: PLC0415
    paths = [Path(f) for f in files] or sorted(SRC_DIR.glob("train-*.parquet"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in paths:
        table = pq.read_table(path).to_pydict()
        n = len(table["caption"])
        keep = [(i, caption_ok(c)) for i, c in enumerate(table["caption"])]
        cand = [i for i, (ok, _) in keep if ok]
        print(f"{path.name}: {n} mẫu, qua lọc caption {len(cand)} ({len(cand) / n:.0%})")
        imgs = [Image.open(io.BytesIO(table["image"][i]["bytes"])).convert("RGB") for i in cand]
        dai = clip_scores(imgs, {"dai_san": PROMPTS_DAI[0], "ngan": PROMPTS_DAI[1]})
        for i, im, sc, ln in zip(cand, imgs, clip_scores(imgs), dai):
            rows.append({"file": path.name, "row": i, **{k: round(v, 4) for k, v in sc.items()},
                         "dai_san": round(ln["dai_san"], 4),
                         "caption": table["caption"][i]})
    with open(OUT_DIR / "index.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"Đã ghi {len(rows)} dòng → {OUT_DIR / 'index.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
