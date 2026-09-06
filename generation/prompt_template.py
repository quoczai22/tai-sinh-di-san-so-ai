# -*- coding: utf-8 -*-
"""Template prompt cho kiến trúc hai giai đoạn (v6).

GIAI ĐOẠN 1 sinh HOA VĂN PHẲNG, không nhắc tới áo dài. Đây là thay đổi cốt lõi
so với v6 §5.2 bản gốc: gộp "vẽ hoa văn gì" và "sản phẩm hình dạng gì" vào một
prompt khiến ControlNet (đường bao bình gốm) và prompt (dáng áo dài) đánh nhau
— đo được P(áo dài) = 0,000 ở weight 0,85.

GIAI ĐOẠN 2 không dùng prompt: hoa văn được ghép lên ảnh áo dài mẫu bằng phép
trộn ảnh tất định, nên dáng áo luôn đúng và tái lập được 100%.
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if getattr(_s, "encoding", "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

ROOT = Path(__file__).resolve().parent.parent

TOKEN_LIMIT = 77          # CLIP cắt ở đây và KHÔNG báo lỗi
TOKEN_SAFE = 75           # trừ <bos>/<eos>

# --- GIAI ĐOẠN 1: hoa văn phẳng ---------------------------------------------
# Ép phong cách MEN GỐM VẼ TAY, không phải "in vải hiện đại". Trước đó đầu ra
# ngả sang hoa văn kaleidoscope đối xứng gương — xa hẳn nét vẽ men lam bất đối
# xứng của hiện vật gốc.
STYLE = ("hand-painted ceramic enamel style, bold outline linework, "
         "asymmetric composition, seamless repeating pattern")
# Loại thẳng những gì ControlNet có thể kéo prompt về: hình khối món đồ, ảnh
# chụp, người. Thêm nhóm từ chống đối xứng gương. Negative prompt có ngân sách
# 77 token RIÊNG nên rộng rãi.
NEG_PATTERN = ("vase, pot, jar, vessel, bottle, ceramic object, 3d render, photograph, "
               "person, mannequin, garment, "
               "kaleidoscope, mandala, mirror symmetry, radial symmetry, "
               "neon colors, oversaturated, "
               "blurry, low quality, watermark, text, distorted")

# --- GIAI ĐOẠN 2: ảnh áo dài mẫu (sinh một lần, dùng lại cho mọi thiết kế) ---
# Chi tiết cấu trúc là bắt buộc: pilot cho thấy chỉ ghi "ao dai" thì seed 44 trôi
# sang sườn xám Trung Hoa (P = 0,381). Mô tả đủ cấu trúc thì 3/3 seed đều đúng.
GARMENT_PROMPT = (
    "a plain white Vietnamese ao dai — ankle length silk tunic, high mandarin collar, "
    "long sleeves, front and back panels split from the waist down, worn over loose "
    "white silk trousers, elegant slim silhouette, full body front view, studio photo")
GARMENT_NEG = ("blurry, low quality, watermark, text, deformed, extra limbs, cropped, "
               "pattern, print, embroidery, busy background")


def assemble_pattern(name_en: str, description: str, creative_direction: str = "") -> str:
    """Prompt giai đoạn 1. KHÔNG nhắc áo dài, không nhắc sản phẩm."""
    parts = [f"a flat decorative pattern inspired by {name_en}", f"featuring {description}"]
    if creative_direction:
        parts.append(creative_direction)
    parts.append(STYLE)
    return ", ".join(parts) + "."


@lru_cache(maxsize=1)
def _tokenizer():
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    from transformers import CLIPTokenizer          # noqa: PLC0415
    return CLIPTokenizer.from_pretrained(os.environ["SD15_MODEL_ID"], subfolder="tokenizer")


def n_tokens(text: str) -> int:
    return len(_tokenizer()(text, truncation=False)["input_ids"])


def assert_fits(prompt: str, where: str) -> None:
    """Tràn 77 token = CLIP cắt đuôi ÂM THẦM, không báo lỗi. Phải dừng hẳn."""
    n = n_tokens(prompt)
    if n > TOKEN_LIMIT:
        raise ValueError(
            f"[{where}] prompt {n} token > {TOKEN_LIMIT}, CLIP sẽ cắt âm thầm.\n"
            f"  Rút gọn `base_description` trong data/prompt_terms.json.\n  {prompt}")
