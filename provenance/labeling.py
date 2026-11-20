# -*- coding: utf-8 -*-
"""Gắn nhãn "AI hỗ trợ tạo" khi xuất ảnh — hai lớp:

1. Nhãn NHÌN THẤY được ở mép dưới ảnh: "Thiết kế hỗ trợ bởi AI · <passport_id>"
   (+ "Ảnh nguồn chưa xác minh quyền" nếu cổng quyền ở mức cảnh báo).
2. Siêu dữ liệu PNG (tEXt): ai_generated, passport_id, sha256 thiết kế gốc,
   nguồn hiện vật, ghi công. Đọc lại được bằng `read_label`.

Chưa dùng chuẩn C2PA (cần chứng thư số); ghi ở mục hướng phát triển.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

FONT_CANDIDATES = ["DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                   "C:/Windows/Fonts/arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"]


def _font(size: int):
    for name in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def label_image(img: Image.Image, *, passport_id: str, design_sha256: str, heritage_name: str,
                attribution: str | None, rights_warning: bool) -> tuple[bytes, dict]:
    img = img.convert("RGB")
    w, h = img.size
    band = max(22, h // 18)
    out = Image.new("RGB", (w, h + band), (250, 247, 240))
    out.paste(img, (0, 0))
    draw = ImageDraw.Draw(out)
    text = f"Thiết kế hỗ trợ bởi AI · {passport_id}"
    if rights_warning:
        text += " · Ảnh nguồn chưa xác minh quyền — không dùng thương mại"
    draw.text((8, h + band // 5), text, fill=(40, 52, 64), font=_font(max(10, band // 2)))
    meta = {"ai_generated": "true", "ai_label": "Thiết kế hỗ trợ bởi AI", "passport_id": passport_id,
            "design_sha256": design_sha256, "heritage": heritage_name,
            "attribution": attribution or "", "rights_warning": str(rights_warning).lower()}
    info = PngInfo()
    for k, v in meta.items():
        info.add_itxt(k, v)
    buf = BytesIO()
    out.save(buf, format="PNG", pnginfo=info)
    return buf.getvalue(), meta


def read_label(path_or_bytes) -> dict:
    src = BytesIO(path_or_bytes) if isinstance(path_or_bytes, (bytes, bytearray)) else Path(path_or_bytes)
    with Image.open(src) as im:
        return {k: v for k, v in im.info.items() if isinstance(v, str)}
