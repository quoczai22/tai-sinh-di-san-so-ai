# -*- coding: utf-8 -*-
"""Sửa tất định khi Cổng G3 báo "mất họa tiết sau img2img": KHOÁ HỌA TIẾT.

Đo trên 24 thiết kế 06/09/2026: img2img (strength 0,40) giữ dáng áo gần như tuyệt
đối (ECC lệch < 1 px, tỉ lệ ≈ 1,000) nhưng VẼ LẠI họa tiết (PPS 0,2–0,5). Vì hình
học không lệch, có thể tách tần số mà không bị bóng ma:

    L*_out  = L*_final + M · (DoG(L*_raw) − DoG(L*_final))   # trả lại NÉT VẼ của bản ghép
    ab*_out = ab*_final + M · k · (ab*_raw − ab*_final)       # trả lại SẮC ĐỘ của họa tiết

Giữ phần tần thấp của img2img (bóng nếp vải, ánh sáng — thứ img2img làm tốt) và
trả lại phần tần trung + màu của họa tiết gốc (thứ img2img làm hỏng).

Lưu ý trung thực: PPS của ảnh đã khoá họa tiết CAO DO CẤU TẠO (ta chép nét của
raw). Vì vậy PPS không chứng minh bản khoá "đẹp hơn". Căn cứ quyết định phải là
đánh giá mù của chuyên gia giữa bản img2img và bản khoá (thí nghiệm EXP-B, mức img2img_0.40+pattern_lock).
"""
from __future__ import annotations

import cv2
import numpy as np
from skimage.color import lab2rgb, rgb2lab

from .align import align_to

METHOD = "pattern_lock_v1"
# dog_sigma_low 0,3 (trước là 1,2): khôi phục cả nét mảnh dưới 1,2 px. Thử trên 12 thiết kế: chi tiết mịn so với bản thô
# 0,81 (sigma 1,2) lên 0,98 (sigma 0,3). Với 1,2 ảnh cuối bị nhòe nét mảnh dù PPS cao.
PARAMS = {"dog_sigma_low": 0.3, "dog_sigma_high": 4.0, "chroma_weight": 0.85, "mask_feather_px": 3.0}


def pattern_lock(raw: np.ndarray, final: np.ndarray, layout_mask: np.ndarray,
                 params: dict | None = None) -> tuple[np.ndarray, dict]:
    p = {**PARAMS, **(params or {})}
    warped, geo = align_to(raw, final)
    # Chỉ nội suy lại ảnh khi lệch thật sự (> 1 px hoặc co giãn > 0,5%). Nội suy
    # tuyến tính dù dịch 0,3 px cũng làm mờ vi chi tiết của vải — đo được: độ nét
    # bản sửa tụt còn 0,17–0,39 so với bản ghép khi luôn nội suy.
    resample = geo["shift_px"] > 1.0 or abs(geo["scale"] - 1.0) > 0.005
    aligned = warped if resample else final
    geo = {**geo, "resampled": resample}
    m = cv2.GaussianBlur(np.clip(layout_mask, 0, 1).astype(np.float32), (0, 0), p["mask_feather_px"])
    lab_r = rgb2lab(raw)
    lab_f = rgb2lab(aligned)

    def band(lum):
        return (cv2.GaussianBlur(lum, (0, 0), p["dog_sigma_low"]) -
                cv2.GaussianBlur(lum, (0, 0), p["dog_sigma_high"]))

    lum = lab_f[..., 0] + m * (band(lab_r[..., 0]) - band(lab_f[..., 0]))
    ab = lab_f[..., 1:] + m[..., None] * p["chroma_weight"] * (lab_r[..., 1:] - lab_f[..., 1:])
    out = np.concatenate([np.clip(lum, 0, 100)[..., None], ab], axis=-1)
    rgb = (np.clip(lab2rgb(out), 0, 1) * 255).round().astype(np.uint8)
    return rgb, {"method": METHOD, "params": p, "alignment": geo}
