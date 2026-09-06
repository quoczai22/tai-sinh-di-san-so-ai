# -*- coding: utf-8 -*-
"""Giữ nguyên bảng màu của hiện vật gốc (v6 — biến thể 1).

Bài toán: người dùng cần ÍT NHẤT một mẫu trung thành màu sắc với hiện vật, còn
các mẫu sau được tự do biến tấu. Nhưng SD tự chọn màu theo prompt và seed — ảnh
gốm men lam có thể ra tông tím, xanh lá, hay nâu đất tuỳ lần chạy.

Cách làm: KHÔNG ép màu qua prompt (không đáng tin), mà chuyển màu sau khi sinh
bằng phép khớp thống kê trong không gian LAB. Tất định, không cần chạy lại SD,
và không đụng gì tới cấu trúc hoa văn mà ControlNet đã dựng.
"""
from __future__ import annotations

import sys

import cv2
import numpy as np
from PIL import Image

for _s in (sys.stdout, sys.stderr):
    if getattr(_s, "encoding", "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _lab_stats(lab: np.ndarray, mask: np.ndarray | None) -> tuple[np.ndarray, np.ndarray]:
    if mask is None:
        px = lab.reshape(-1, 3)
    else:
        px = lab[mask > 0]
        if len(px) < 64:                       # mask hỏng → lùi về toàn ảnh
            px = lab.reshape(-1, 3)
    return px.mean(axis=0), px.std(axis=0) + 1e-6


def match_palette(pattern: Image.Image, reference: Image.Image,
                  ref_mask: np.ndarray | None = None,
                  strength: float = 1.0) -> Image.Image:
    """Chuyển bảng màu của `reference` sang `pattern`, giữ nguyên cấu trúc.

    ref_mask: mask vùng món đồ trong ảnh tham chiếu. BẮT BUỘC nên truyền — ảnh
    tham chiếu đã letterbox có viền trắng lớn, không loại ra thì thống kê bị kéo
    về trắng và hoa văn sinh ra bị bạc màu.

    strength: 1.0 = khớp hoàn toàn, 0.0 = giữ nguyên màu của pattern.
    """
    p = cv2.cvtColor(np.array(pattern.convert("RGB")), cv2.COLOR_RGB2LAB).astype(np.float32)
    r = cv2.cvtColor(np.array(reference.convert("RGB")), cv2.COLOR_RGB2LAB).astype(np.float32)
    pm, ps = _lab_stats(p, None)
    rm, rs = _lab_stats(r, ref_mask)
    out = (p - pm) / ps * rs + rm
    if strength < 1.0:
        out = p * (1 - strength) + out * strength
    out = np.clip(out, 0, 255).astype(np.uint8)
    return Image.fromarray(cv2.cvtColor(out, cv2.COLOR_LAB2RGB))


def dominant_colors(img: Image.Image, mask: np.ndarray | None = None,
                    k: int = 5) -> list[tuple[int, int, int]]:
    """Bảng màu chủ đạo — để hiển thị trong Design Passport."""
    a = np.array(img.convert("RGB"))
    px = a.reshape(-1, 3) if mask is None else a[mask > 0]
    if len(px) < k:
        return []
    px = px[np.random.default_rng(0).choice(len(px), min(len(px), 20000), replace=False)]
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, lab, centers = cv2.kmeans(px.astype(np.float32), k, None, crit, 3,
                                 cv2.KMEANS_PP_CENTERS)
    order = np.argsort(-np.bincount(lab.flatten(), minlength=k))
    return [tuple(int(v) for v in centers[i]) for i in order]
