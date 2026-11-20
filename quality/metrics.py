# -*- coding: utf-8 -*-
"""Các phép đo kỹ thuật cho Quality Gate.

Ký hiệu ảnh trong một thiết kế:
  reference  — ảnh hiện vật đã letterbox 512 (đầu vào giai đoạn 1)
  pattern    — hoa văn phẳng do SD1.5 + ControlNet sinh (đầu ra giai đoạn 1)
  raw        — bản ghép TẤT ĐỊNH hoa văn lên áo mẫu (trước img2img)
  final      — thiết kế cuối sau lượt hoàn thiện img2img
  template   — ảnh áo dài trắng mẫu

Vì sao so `final` với `raw` chứ không với `pattern`: raw là phiên bản đúng tuyệt
đối về dáng áo và vị trí họa tiết (ghép tất định). Mọi khác biệt raw→final đều do
lượt img2img gây ra — đúng điểm BTC nêu: "sau img2img toàn ảnh, dáng áo và hoa văn
gốc có thể biến dạng".
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image
from skimage.color import rgb2lab


def to_rgb_array(img: Image.Image | np.ndarray) -> np.ndarray:
    if isinstance(img, np.ndarray):
        return img[..., :3].astype(np.uint8)
    return np.asarray(img.convert("RGB"))


def _ncc(a: np.ndarray, b: np.ndarray, region: np.ndarray) -> float:
    a = a[region].astype(np.float64)
    b = b[region].astype(np.float64)
    if a.size < 64:
        return float("nan")
    a -= a.mean()
    b -= b.mean()
    denom = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / denom) if denom > 1e-9 else float("nan")


def _dog(lum: np.ndarray, s1: float = 1.2, s2: float = 4.0) -> np.ndarray:
    """Dải tần trung (Difference of Gaussians): giữ NÉT VẼ họa tiết, bỏ bóng
    nếp vải (tần thấp) và nhiễu hạt (tần rất cao)."""
    return cv2.GaussianBlur(lum, (0, 0), s1) - cv2.GaussianBlur(lum, (0, 0), s2)


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


def pattern_region(raw: np.ndarray, template: np.ndarray, layout_mask: np.ndarray,
                   delta_e: float = 8.0) -> np.ndarray:
    """Pixel thực sự mang họa tiết: nằm trong vùng in của bố cục VÀ khác áo trắng
    mẫu rõ rệt (ΔE76 > 8). Vùng in thường gồm cả phần vải trắng — tính chỉ số
    trên cả vùng sẽ thưởng điểm cho vải trắng giữ nguyên."""
    lab_r = rgb2lab(raw)
    lab_t = rgb2lab(template)
    d = np.sqrt(((lab_r - lab_t) ** 2).sum(axis=2))
    return (layout_mask > 0.3) & (d > delta_e)


def pattern_preservation(raw: np.ndarray, final: np.ndarray, template: np.ndarray,
                         layout_mask: np.ndarray) -> dict:
    """Pattern Preservation Score (PPS), thang [-1, 1], cao là giữ tốt.

    PPS = trung bình của
      · tương quan nét vẽ: NCC của dải DoG trên kênh L*  (hình dạng họa tiết)
      · tương quan sắc độ: NCC trung bình của kênh a*, b* (bố cục màu họa tiết)
    tính trên vùng họa tiết P, SAU khi căn final về raw.

    Diễn giải: NCC = r. r = 0,6 nghĩa là ~36% phương sai nét vẽ của bản ghép còn
    giải thích được trong thiết kế cuối.
    """
    warped, geo = align_to(raw, final)
    # Lệch dưới 1 px thì không nội suy (nội suy cũng làm mờ, gây thiệt cho final)
    resample = geo["shift_px"] > 1.0 or abs(geo["scale"] - 1.0) > 0.005
    aligned = warped if resample else final
    geo = {**geo, "resampled": resample}
    region = pattern_region(raw, template, layout_mask)
    region_d = cv2.dilate(region.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    lab_r = rgb2lab(raw)
    lab_f = rgb2lab(aligned)
    structure = _ncc(_dog(lab_r[..., 0]), _dog(lab_f[..., 0]), region_d)
    chroma = np.nanmean([_ncc(lab_r[..., 1], lab_f[..., 1], region_d),
                         _ncc(lab_r[..., 2], lab_f[..., 2], region_d)])
    mean_r = lab_r[region].mean(axis=0) if region.any() else np.zeros(3)
    mean_f = lab_f[region].mean(axis=0) if region.any() else np.zeros(3)
    palette_shift = float(np.linalg.norm(mean_r - mean_f))
    pps = float(np.nanmean([structure, chroma]))
    return {"pattern_preservation": round(pps, 4),
            "structure_ncc": round(float(structure), 4),
            "chroma_ncc": round(float(chroma), 4),
            "palette_shift_de": round(palette_shift, 2),
            "pattern_area_pct": round(float(region.mean() * 100), 2),
            "alignment": geo}


def garment_silhouette(img: np.ndarray, prior_mask: np.ndarray) -> np.ndarray:
    """Tách dáng áo bằng GrabCut khởi tạo từ mask áo của ảnh mẫu.

    Lõi (co 25 px) là chắc chắn áo, vành (giãn 15 px) là "có thể áo", ngoài 61 px
    là chắc chắn nền. Nếu img2img kéo vạt áo ra ngoài hay bóp vào trong, GrabCut
    theo màu thật của ảnh sẽ trả về đường viền mới.
    """
    cv2.setRNGSeed(0)
    prior = prior_mask.astype(np.uint8)
    mask = np.full(prior.shape, cv2.GC_PR_BGD, np.uint8)
    mask[cv2.dilate(prior, np.ones((15, 15), np.uint8)) > 0] = cv2.GC_PR_FGD
    mask[cv2.erode(prior, np.ones((25, 25), np.uint8)) > 0] = cv2.GC_FGD
    mask[cv2.dilate(prior, np.ones((61, 61), np.uint8)) == 0] = cv2.GC_BGD
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(cv2.cvtColor(img, cv2.COLOR_RGB2BGR), mask, None, bgd, fgd, 4,
                cv2.GC_INIT_WITH_MASK)
    return np.isin(mask, (cv2.GC_FGD, cv2.GC_PR_FGD))


def garment_shape_consistency(raw: np.ndarray, final: np.ndarray, prior_mask: np.ndarray) -> dict:
    """Garment Shape Consistency (GSC) = IoU dáng áo raw vs final, thang [0, 1]."""
    s_raw = garment_silhouette(raw, prior_mask)
    s_fin = garment_silhouette(final, prior_mask)
    inter = (s_raw & s_fin).sum()
    union = (s_raw | s_fin).sum()
    iou = float(inter / union) if union else 0.0
    area_change = float((s_fin.sum() - s_raw.sum()) / max(s_raw.sum(), 1))
    return {"garment_shape_iou": round(iou, 4), "garment_area_change_pct": round(area_change * 100, 2)}


def visual_quality(raw: np.ndarray, final: np.ndarray, region: np.ndarray) -> dict:
    """Chỉ số chất lượng ảnh kỹ thuật (không phải thẩm mỹ):
      · sharpness_ratio: phương sai Laplacian của final / raw trong vùng áo — img2img
        làm mềm quá mức thì họa tiết nhoè.
      · clipping_pct: % pixel cháy sáng/bết tối trong vùng áo.
    """
    gr = cv2.Laplacian(cv2.cvtColor(raw, cv2.COLOR_RGB2GRAY), cv2.CV_64F)
    gf = cv2.Laplacian(cv2.cvtColor(final, cv2.COLOR_RGB2GRAY), cv2.CV_64F)
    var_r = float(gr[region].var()) if region.any() else 0.0
    var_f = float(gf[region].var()) if region.any() else 0.0
    gray = cv2.cvtColor(final, cv2.COLOR_RGB2GRAY)[region]
    clip = float(((gray <= 2) | (gray >= 253)).mean() * 100) if gray.size else 0.0
    return {"sharpness_ratio": round(var_f / var_r, 4) if var_r > 1e-9 else float("nan"),
            "clipping_pct": round(clip, 3)}


def detail_preservation(raw: np.ndarray, final: np.ndarray, region: np.ndarray) -> dict:
    """Giữ chi tiết mịn (detail_ratio): phương sai Laplacian của final / raw TRONG VÙNG HỌA TIẾT, cao là tốt.

    Khác sharpness_ratio (đo trên cả vùng áo, phần lớn là vải trơn nên pha loãng): chỉ số này đo ngay chỗ có họa tiết,
    nên bắt được việc nét mảnh bị nhòe sau polish. PPS chỉ đo dải tần trung (sigma 1,2 đến 4 px) nên không bắt được.
    """
    if region.sum() < 200:
        return {"detail_ratio": float("nan")}
    lap = lambda a: cv2.Laplacian(cv2.cvtColor(a, cv2.COLOR_RGB2GRAY).astype(np.float64), cv2.CV_64F)[region].var()
    var_r = float(lap(raw))
    return {"detail_ratio": round(float(lap(final)) / var_r, 4) if var_r > 1e-9 else float("nan")}


def vessel_leakage(pattern: np.ndarray, reference: np.ndarray, border: int = 24) -> dict:
    """Vessel Leakage Score (VLS) cho hoa văn giai đoạn 1, thang [0, 1], THẤP là tốt.

    Lỗi đã biết: ở trọng số ControlNet cao, "hoa văn" sinh ra là ảnh nguyên chiếc
    bình trên nền trơn (BT_Hac_XP V1/V2). Một tile hoa văn đúng nghĩa thì phủ kín
    khung. VLS = (tỉ lệ viền khung là nền trơn) × (IoU dáng vật thể trong hoa văn
    với dáng hiện vật gốc). Cả hai cùng cao → hoa văn đang vẽ lại cái bình.

    Giới hạn đã biết: KHÔNG bắt được dạng "mảnh ghép thân bình" phủ kín khung
    (ví dụ hiện vật sen dát vàng V1/V2) — đó là lý do vẫn cần người rà soát.
    """
    from generation import controlnet as cn                # noqa: PLC0415

    img = Image.fromarray(pattern)
    bg = cn.estimate_background(img, border=6)
    dist = np.abs(pattern.astype(np.int16) - bg).max(axis=2)
    gray = cv2.cvtColor(pattern, cv2.COLOR_RGB2GRAY).astype(np.float32)
    local_var = cv2.blur(gray ** 2, (9, 9)) - cv2.blur(gray, (9, 9)) ** 2
    flat = (dist < 18) & (local_var < 60)
    frame = np.zeros(flat.shape, bool)
    frame[:border] = frame[-border:] = True
    frame[:, :border] = frame[:, -border:] = True
    border_bg = float(flat[frame].mean())
    # tol=26 và không lấp lỗ: giữ nguyên phép đo của cổng chất lượng bản 09/2026 để số đã ghi trong Passport
    # còn tái lập được (generation.controlnet mặc định nay tự chọn ngưỡng và lấp lỗ cho ảnh nền xám).
    m_pat = cn.object_mask(img, tol=26, fill_holes=False) > 0
    m_ref = cn.object_mask(Image.fromarray(reference), tol=26, fill_holes=False) > 0
    union = (m_pat | m_ref).sum()
    iou = float((m_pat & m_ref).sum() / union) if union else 0.0
    return {"vessel_leakage": round(border_bg * iou, 4), "border_background": round(border_bg, 4),
            "silhouette_iou_vs_artifact": round(iou, 4)}


def outside_drift(raw: np.ndarray, final: np.ndarray, garment_mask: np.ndarray) -> dict:
    """Trôi ngoài vùng áo (M2): sai khác tuyệt đối giữa bản ghép thô và thiết kế cuối ở
    NGOÀI mặt nạ áo, thang 0 đến 255 (trung bình trên mọi pixel và kênh màu).

    Polish có mặt nạ giữ nguyên từng pixel ngoài áo nên kỳ vọng đúng 0. Polish toàn ảnh
    vẽ lại cả nền, tay, mặt nên cho giá trị lớn. Chỉ đo và ghi vào chi tiết, chưa dùng làm
    ngưỡng loại: ngưỡng cần hiệu chỉnh sau.
    """
    outside = garment_mask == 0
    if not outside.any():
        return {"outside_drift": float("nan"), "outside_drift_max": float("nan")}
    d = np.abs(raw.astype(np.int16) - final.astype(np.int16))[outside]
    return {"outside_drift": round(float(d.mean()), 3), "outside_drift_max": int(d.max())}


def seam_ratio(pattern: np.ndarray) -> dict:
    """Độ lộ đường nối khi lát tile: chênh lệch mép trái↔phải (trên↔dưới) chia cho
    chênh lệch trung bình giữa hai cột (hàng) kề nhau bên trong. ≈1 là liền mạch."""
    g = cv2.cvtColor(pattern, cv2.COLOR_RGB2GRAY).astype(np.float32)
    inner_h = np.abs(np.diff(g, axis=1)).mean()
    inner_v = np.abs(np.diff(g, axis=0)).mean()
    h = float(np.abs(g[:, 0] - g[:, -1]).mean() / max(inner_h, 1e-6))
    v = float(np.abs(g[0] - g[-1]).mean() / max(inner_v, 1e-6))
    return {"seam_ratio": round(max(h, v), 3), "seam_h": round(h, 3), "seam_v": round(v, 3)}
