# -*- coding: utf-8 -*-
"""Căn hai ảnh bằng ECC affine (dùng chung cho đo chất lượng và khoá họa tiết)."""
from __future__ import annotations

import cv2
import numpy as np


def align_to(reference: np.ndarray, moving: np.ndarray) -> tuple[np.ndarray, dict]:
    """Căn `moving` về khung của `reference` bằng ECC affine.

    Tách hai loại sai khác: LỆCH HÌNH HỌC (img2img dịch/co áo) và ĐỔI HỌA TIẾT.
    Nếu không căn trước, một lệch 2 px cũng làm tụt tương quan nét vẽ và ta sẽ
    quy nhầm là "mất họa tiết".
    """
    a = cv2.GaussianBlur(cv2.cvtColor(reference, cv2.COLOR_RGB2GRAY), (0, 0), 2).astype(np.float32)
    b = cv2.GaussianBlur(cv2.cvtColor(moving, cv2.COLOR_RGB2GRAY), (0, 0), 2).astype(np.float32)
    warp = np.eye(2, 3, dtype=np.float32)
    try:
        cc, warp = cv2.findTransformECC(
            a, b, warp, cv2.MOTION_AFFINE,
            (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-5), None, 5)
    except cv2.error:
        cc = float("nan")
    aligned = cv2.warpAffine(moving, warp, (moving.shape[1], moving.shape[0]),
                             flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP,
                             borderMode=cv2.BORDER_REFLECT)
    info = {"ecc": round(float(cc), 4),
            "scale": round(float(np.sqrt(abs(np.linalg.det(warp[:, :2])))), 4),
            "shift_px": round(float(np.hypot(warp[0, 2], warp[1, 2])), 2)}
    return aligned, info
