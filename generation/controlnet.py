# -*- coding: utf-8 -*-
"""Tiền xử lý ảnh heritage → bản đồ cạnh Canny cho ControlNet (spec mục 12.1).

ControlNet KHÔNG nhận ảnh gốc. Nó nhận một ma trận nhị phân 512×512 trong đó
trắng là cạnh. Thứ được bảo tồn chính xác là những đường trắng đó — không hơn.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

for _s in (sys.stdout, sys.stderr):
    if getattr(_s, "encoding", "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

ROOT = Path(__file__).resolve().parent.parent
HERITAGE_DIR = ROOT / "data" / "heritage"

RESOLUTION = 512          # native SD1.5, an toàn với 8GB VRAM
CANNY_LOW = 100
CANNY_HIGH = 200


def load_reference(heritage_id: str) -> tuple[Image.Image, np.ndarray | None]:
    """Trả về (ảnh RGB, mask alpha nếu có).

    Nhiều ảnh gốm tải về là PNG đã tách nền sẵn. Kênh alpha là mask món đồ
    CHÍNH XÁC — tốt hơn hẳn dò ngưỡng sáng, vốn hỏng khi nền tối hoặc khi món đồ
    có phần trắng sát nền. Có alpha thì dùng alpha.
    """
    for f in sorted(HERITAGE_DIR.glob(f"{heritage_id}.*")):
        if f.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        im = Image.open(f)
        alpha = None
        if im.mode in ("RGBA", "LA") or "transparency" in im.info:
            alpha = np.array(im.convert("RGBA"))[:, :, 3]
            # Nền trong suốt hoá thành TRẮNG, không phải đen — nền đen sẽ tạo ra
            # một đường viền Canny giả quanh toàn bộ món đồ.
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGB"), mask=Image.fromarray(alpha))
            return bg, alpha
        return im.convert("RGB"), None
    raise FileNotFoundError(f"Khong thay anh cho {heritage_id} trong {HERITAGE_DIR}")


def letterbox(img: Image.Image, size: int = RESOLUTION) -> Image.Image:
    """Co giữ nguyên tỷ lệ rồi chèn viền trắng cho vuông.

    KHÔNG kéo giãn: tỷ lệ ảnh trong data/heritage/ chênh từ 0,42 (BT002) tới
    1,33 (BT005); kéo giãn sẽ biến dạng chính hoạ tiết đang cần bảo tồn —
    mâu thuẫn trực tiếp với mục đích của `preserve`.
    """
    w, h = img.size
    s = size / max(w, h)
    small = img.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
    canvas = Image.new("RGB", (size, size), (255, 255, 255))
    canvas.paste(small, ((size - small.size[0]) // 2, (size - small.size[1]) // 2))
    return canvas


def to_canny(img: Image.Image, low: int = CANNY_LOW, high: int = CANNY_HIGH) -> Image.Image:
    edges = cv2.Canny(np.array(img), low, high)
    return Image.fromarray(np.stack([edges] * 3, axis=-1))


def edge_density(control: Image.Image) -> float:
    """% pixel là cạnh. Quá thấp (<1%) nghĩa là ControlNet gần như không có gì
    để bám — weight cao cũng không giữ được cấu trúc."""
    return float((np.array(control)[:, :, 0] > 0).mean() * 100)


def trim_background(img: Image.Image, thr: int = 245, pad: int = 8,
                    use_bg_color: bool = True) -> tuple[Image.Image, tuple]:
    """Cắt bỏ nền phông xung quanh món đồ.

    Hiện vật thường chỉ chiếm 30% khung ảnh chụp studio; cắt lề rồi mới letterbox
    thì nó chiếm ~60%, tức gấp đôi số pixel cho hoa văn. Đo trên BT010: mật độ
    cạnh 3,97% → 7,53%.

    Hỏng an toàn: nền không phải trắng thì mask phủ toàn ảnh, hộp bao bằng cả
    ảnh, và hàm trả về ảnh nguyên vẹn thay vì cắt sai.
    """
    if use_bg_color:
        m = object_mask(img)          # dùng màu nền suy từ viền, không giả định trắng
        ys, xs = np.where(m > 0)
    else:
        a = np.array(img.convert("L"))
        ys, xs = np.where(a < thr)
    if len(xs) == 0:
        return img, (0, 0, *img.size)
    w, h = img.size
    box = (max(0, int(xs.min()) - pad), max(0, int(ys.min()) - pad),
           min(w, int(xs.max()) + 1 + pad), min(h, int(ys.max()) + 1 + pad))
    return img.crop(box), box


def estimate_background(img: Image.Image, border: int = 6) -> np.ndarray:
    """Suy màu nền từ viền ảnh (trung vị), thay vì giả định nền trắng."""
    a = np.array(img.convert("RGB"))
    edge = np.concatenate([a[:border].reshape(-1, 3), a[-border:].reshape(-1, 3),
                           a[:, :border].reshape(-1, 3), a[:, -border:].reshape(-1, 3)])
    return np.median(edge, axis=0)


def object_mask(img: Image.Image, thr: int = 245, erode_px: int = 0,
                alpha: np.ndarray | None = None, tol: int = 26) -> np.ndarray:
    """Mask vùng món đồ.

    Ưu tiên alpha. Không có alpha thì so với MÀU NỀN suy từ viền ảnh — không
    giả định nền trắng. Giả định nền trắng làm hỏng ảnh nền xám hoặc nền tối:
    mask phủ toàn khung, đường bao món đồ không bị loại, và ControlNet lại ép ra
    hình cái bình (quan sát được trên ảnh nền xám 200,200,200).
    """
    if alpha is not None:
        m = (alpha > 10).astype(np.uint8)
    else:
        a = np.array(img.convert("RGB")).astype(np.int16)
        bg = estimate_background(img)
        dist = np.abs(a - bg).max(axis=2)
        m = (dist > tol).astype(np.uint8)
        # Nền quá gần màu món đồ → mask phủ gần hết khung, không đáng tin.
        # Lùi về ngưỡng sáng để ít nhất không tệ hơn cách cũ.
        if m.mean() > 0.92:
            m = (np.array(img.convert("L")) < thr).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    if erode_px:
        m = cv2.erode(m, np.ones((erode_px, erode_px), np.uint8))
    return m


def to_canny_ornament(img: Image.Image, erode_px: int = 14,
                      low: int = CANNY_LOW, high: int = CANNY_HIGH,
                      alpha: np.ndarray | None = None) -> Image.Image:
    """Bản đồ cạnh CHỈ giữ hoa văn bề mặt, BỎ đường bao món đồ.

    Đây là mấu chốt của giai đoạn 1. Canny thường trả về cả đường viền ngoài của
    cái bình lẫn nét hoa văn trên thân. ControlNet không phân biệt hai loại đó,
    nên ở weight cao nó ép ảnh sinh ra thành hình cái bình — đo được: prompt yêu
    cầu áo dài nhưng P(áo dài) = 0,000 ở weight 0,85.

    Co mask món đồ vào trong `erode_px` pixel rồi nhân với bản đồ cạnh: mọi nét
    nằm trên hoặc sát đường bao bị loại, chỉ còn hoa văn bên trong.
    """
    edges = cv2.Canny(np.array(img), low, high)
    inner = object_mask(img, erode_px=erode_px, alpha=alpha)
    return Image.fromarray(np.stack([edges * inner] * 3, axis=-1))


def prepare(heritage_id: str, ornament_only: bool = True,
            trim: bool = True) -> dict:
    """Chuẩn bị ảnh điều kiện cho giai đoạn 1.

    ornament_only=True  → bỏ đường bao, chỉ giữ hoa văn (mặc định cho v6)
    ornament_only=False → Canny đầy đủ, giữ cả dáng món đồ
    """
    src, alpha = load_reference(heritage_id)
    box = (0, 0, *src.size)
    if trim:
        # Cắt theo alpha nếu có — chính xác hơn dò ngưỡng
        if alpha is not None:
            ys, xs = np.where(alpha > 10)
            if len(xs):
                w, h = src.size
                box = (max(0, int(xs.min()) - 8), max(0, int(ys.min()) - 8),
                       min(w, int(xs.max()) + 9), min(h, int(ys.max()) + 9))
                src = src.crop(box)
                alpha = alpha[box[1]:box[3], box[0]:box[2]]
        else:
            src, box = trim_background(src)
    ref = letterbox(src)
    a_lb = None
    if alpha is not None:
        # Đưa alpha qua đúng phép letterbox để khớp `ref` từng pixel. Viền chèn
        # phải là 0 (nền) — dùng letterbox() sẽ chèn 255 và biến viền thành
        # "vùng đặc", khiến mask sai toàn bộ.
        w, h = src.size
        s = RESOLUTION / max(w, h)
        aw, ah = max(1, int(w * s)), max(1, int(h * s))
        small = np.array(Image.fromarray(alpha).resize((aw, ah), Image.NEAREST))
        a_lb = np.zeros((RESOLUTION, RESOLUTION), np.uint8)
        x0, y0 = (RESOLUTION - aw) // 2, (RESOLUTION - ah) // 2
        a_lb[y0:y0 + ah, x0:x0 + aw] = small
    control = (to_canny_ornament(ref, alpha=a_lb) if ornament_only else to_canny(ref))
    # Mask vùng món đồ trong khung 512 — cần cho việc khớp bảng màu gốc
    # (generation/palette.py): không loại viền letterbox trắng ra khỏi thống kê
    # thì màu bị kéo về trắng và hoa văn ra bạc màu.
    ref_mask = object_mask(ref, alpha=a_lb)
    return {"reference": ref, "control": control, "crop_box": box,
            "reference_mask": ref_mask,
            "edge_density": edge_density(control),
            "n_edge_px": int((np.array(control)[:, :, 0] > 0).sum()),
            "has_alpha": alpha is not None,
            "mode": "ornament_only" if ornament_only else "full_canny"}
