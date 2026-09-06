# -*- coding: utf-8 -*-
"""Tự chọn cách bố trí hoa văn cho từng hoa văn cụ thể.

SD1.5 KHÔNG làm được việc này — nó sinh ảnh, không quyết định bố cục. Nhưng hệ
thống làm được, và rẻ: ghép ảnh là phép numpy trên 512×512, nên sinh đủ cả 7 bố
cục rồi chấm điểm chọn chỉ mất ~2 giây, ít hơn một lần chạy Stable Diffusion.

Cách chấm: CLIP so ảnh thiết kế với hai nhóm mô tả đối lập (đẹp/rối), lấy hiệu.
Đo trên hoa văn thật cho biên độ 0,0325 giữa bố cục cao nhất và thấp nhất —
đủ để xếp hạng, và `full_body` xuống chót đúng như trực giác thiết kế.

Điểm số này KHÔNG phải phán quyết. Hệ thống xếp hạng, người dùng chọn — cùng
nguyên tắc "không tự diễn giải con số thành quyết định" áp cho Similarity.
"""
from __future__ import annotations

import sys
from functools import lru_cache

import torch
import torch.nn.functional as F
from PIL import Image

from . import garment

for _s in (sys.stdout, sys.stderr):
    if getattr(_s, "encoding", "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

GOOD = ["an elegant Vietnamese ao dai with beautifully placed decorative pattern",
        "a tasteful balanced traditional dress design, harmonious composition"]
BAD = ["a cluttered messy dress with badly placed random pattern",
       "an unbalanced awkward garment design"]


@lru_cache(maxsize=1)
def _clip():
    from transformers import CLIPModel, CLIPProcessor      # noqa: PLC0415
    m = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").eval()
    p = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    with torch.no_grad():
        t = p(text=GOOD + BAD, return_tensors="pt", padding=True)
        te = F.normalize(m.text_projection(m.text_model(**t).pooler_output), dim=-1)
    return m, p, te


@torch.no_grad()
def score_design(img: Image.Image) -> float:
    m, p, te = _clip()
    i = p(images=img, return_tensors="pt")
    iv = F.normalize(m.visual_projection(m.vision_model(**i).pooler_output), dim=-1)
    s = (iv @ te.T)[0]
    return round(float(s[:len(GOOD)].mean() - s[len(GOOD):].mean()), 4)


def rank(pattern: Image.Image, only: list[str] | None = None) -> list[dict]:
    """Ghép hoa văn theo mọi bố cục rồi xếp hạng. Cao nhất đứng đầu."""
    out = []
    for name in (only or garment.layout_names()):
        img = garment.apply(pattern, layout=name)
        lay = garment.get_layout(name)
        out.append({"layout": name, "label": lay["label"], "scale": lay["scale"],
                    "score": score_design(img), "image": img})
    return sorted(out, key=lambda r: -r["score"])


def best(pattern: Image.Image, exclude: set[str] | None = None) -> dict:
    """Bố cục điểm cao nhất, bỏ qua những bố cục đã dùng cho biến thể trước.

    Loại trùng để bộ mẫu đưa cho người dùng thật sự khác nhau — nếu không, cả 4
    biến thể có thể cùng rơi vào một bố cục và mất ý nghĩa "nhiều lựa chọn".
    """
    ex = exclude or set()
    for r in rank(pattern):
        if r["layout"] not in ex:
            return r
    return rank(pattern)[0]
