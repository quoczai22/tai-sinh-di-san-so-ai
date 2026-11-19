"""Tách vùng áo dài bằng SAM (Segment Anything) với điểm gợi ý ở giữa thân áo.

Vì sao cần: `garment.garment_mask` tách áo theo màu (độ bão hòa thấp, độ sáng cao), nên khi áo do
mô hình sinh ra nằm trên sàn đá hay tường trắng, mặt nạ tràn ra cả nền. SAM phân đoạn theo hình dạng
nên không bị lỗi này. Điểm gợi ý: vài điểm dọc trục giữa là "áo", các góc ảnh là "không phải áo".

Mô hình facebook/sam-vit-base (Apache-2.0 theo thẻ mô hình, chưa kiểm tra lại) tải lần đầu từ Hugging Face.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np
from PIL import Image

MIN_FRAC, MAX_FRAC = 0.05, 0.65   # diện tích áo hợp lý so với khung ảnh; ngoài khoảng này coi là mặt nạ sai


def prompt_points(w: int, h: int) -> tuple[list[list[int]], list[int]]:
    """Điểm gợi ý cho SAM: nhãn 1 là áo (trục giữa, ngực đến gấu), nhãn 0 là nền (bốn góc, hai bên sát đáy)."""
    pos = [[w // 2, int(h * f)] for f in (0.30, 0.45, 0.60, 0.75)]
    neg = [[int(w * 0.04), int(h * 0.04)], [int(w * 0.96), int(h * 0.04)],
           [int(w * 0.04), int(h * 0.96)], [int(w * 0.96), int(h * 0.96)]]
    return pos + neg, [1] * len(pos) + [0] * len(neg)


def clean_mask(mask: np.ndarray) -> np.ndarray:
    """Giữ thành phần liên thông lớn nhất, lấp lỗ nhỏ, làm mượt viền. Trả về uint8 0/1."""
    m = (np.asarray(mask) > 0).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n > 1:
        m = (lab == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    # Lấp lỗ: vùng nền không chạm mép khung và nằm trọn trong áo
    inv = (m == 0).astype(np.uint8)
    n, lab = cv2.connectedComponents(inv, connectivity=4)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist())
    for i in range(1, n):
        if i not in edge:
            m[lab == i] = 1
    return m


def choose(masks: list[np.ndarray], scores: list[float]) -> int | None:
    """Chọn mặt nạ có điểm SAM cao nhất trong số các mặt nạ có diện tích hợp lý. None nếu không có mặt nạ nào."""
    ok = [i for i, m in enumerate(masks) if MIN_FRAC <= float((np.asarray(m) > 0).mean()) <= MAX_FRAC]
    return max(ok, key=lambda i: scores[i]) if ok else None


@lru_cache(maxsize=1)
def _model(model_id: str = "facebook/sam-vit-base"):
    import torch                                                    # noqa: PLC0415
    from transformers import SamModel, SamProcessor                 # noqa: PLC0415
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    return SamModel.from_pretrained(model_id).to(dev).eval(), SamProcessor.from_pretrained(model_id), dev


def free_model() -> None:
    """Giải phóng SAM khỏi bộ nhớ GPU."""
    import torch                                                    # noqa: PLC0415
    _model.cache_clear()
    torch.cuda.empty_cache()


def garment_mask_sam(image: Image.Image) -> np.ndarray:
    """Mặt nạ vùng áo (uint8 0/1, cùng kích thước ảnh). Ném RuntimeError nếu SAM không cho mặt nạ hợp lý."""
    import torch                                                    # noqa: PLC0415
    model, proc, dev = _model()
    img = image.convert("RGB")
    points, labels = prompt_points(*img.size)
    inputs = proc(img, input_points=[[points]], input_labels=[[labels]], return_tensors="pt").to(dev)
    with torch.no_grad():
        out = model(**inputs, multimask_output=True)
    masks = proc.image_processor.post_process_masks(out.pred_masks.cpu(), inputs["original_sizes"].cpu(),
                                                    inputs["reshaped_input_sizes"].cpu())[0][0]
    scores = out.iou_scores.cpu()[0][0].tolist()
    cands = [clean_mask(m.numpy()) for m in masks]
    k = choose(cands, scores)
    if k is None:
        raise RuntimeError("SAM không cho mặt nạ áo có diện tích hợp lý; dùng áo khác.")
    return cands[k]
