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


GAP_TOL = 16          # khoảng cách màu RGB tối đa giữa điểm trong mặt nạ và màu nền dự đoán để coi là nền chắc chắn (lõi khe)
GAP_MIN_AREA = 80     # lõi khe nhỏ hơn số điểm này bỏ qua (nhiễu)
GAP_GROW = 2          # nới khe thêm bấy nhiêu điểm để loại luôn viền tối sát mép vải
GAP_REACH = 90        # khe trong bóng (tối hơn nền) chỉ được nới ra tối đa chừng này điểm quanh lõi khe
GAP_WIDTH = 61        # phần nới phải là thung lũng ngang hẹp hơn bề rộng này; bóng đổ rộng trên vải không tính
GAP_DEPTH = 45        # và tối hơn vải hai bên ít nhất chừng này mức sáng
MAX_GAP_FRAC = 0.08   # bỏ khe nền quá 8% diện tích mặt nạ thì không tin bộ phát hiện (có thể cắt nhầm bóng đổ trên vải): loại áo này


def expected_wall(img: np.ndarray, mask: np.ndarray, side: int = 40) -> np.ndarray:
    """Màu nền dự đoán tại mọi điểm: mỗi hàng nội suy tuyến tính giữa màu nền ngay trái và ngay phải của áo (float32, H x W x 3)."""
    h, w, _ = img.shape
    est = np.zeros((h, w, 3), np.float32)
    last = np.array([128, 128, 128], np.float32)
    t = np.linspace(0, 1, w)[:, None]
    for y in range(h):
        xs = np.where(mask[y] > 0)[0]
        if len(xs) == 0:
            continue
        l0, r0 = int(xs.min()), int(xs.max())
        left = img[y, max(0, l0 - side):max(1, l0 - 2)].reshape(-1, 3)
        right = img[y, min(w - 1, r0 + 3):min(w, r0 + side)].reshape(-1, 3)
        lc = np.median(left, axis=0) if len(left) else None
        rc = np.median(right, axis=0) if len(right) else None
        if lc is None and rc is None:
            lc = rc = last
        elif lc is None:
            lc = rc
        elif rc is None:
            rc = lc
        last = (lc + rc) / 2
        est[y] = lc[None, :] * (1 - t) + rc[None, :] * t
    return est


def remove_background_gaps(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Bỏ khỏi mặt nạ các khe nền lọt vào trong (ví dụ khe giữa tay và thân, khe giữa hai tà): lõi khe là điểm trong mặt nạ có màu
    gần màu nền dự đoán cùng hàng, rồi nới có giới hạn vào phần khe trong bóng. SAM coi khe này là áo, nên hoa văn bị in lên nền nhìn thấy qua khe.
    Trả về mặt nạ mới (uint8 0/1, chỉ thành phần liên thông lớn nhất); không thấy khe nào thì trả lại đúng mặt nạ cũ."""
    m = (np.asarray(mask) > 0).astype(np.uint8)
    est = expected_wall(img, m)
    luma = np.array([0.299, 0.587, 0.114], np.float32)
    dist = np.sqrt(((img.astype(np.float32) - est) ** 2).sum(axis=2))
    # Lõi khe: điểm trong mặt nạ có màu gần màu nền dự đoán cùng hàng
    core = cv2.morphologyEx(((m > 0) & (dist < GAP_TOL)).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(core, 8)
    gap = np.zeros_like(m)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= GAP_MIN_AREA:
            gap[lab == i] = 1
    if gap.any():
        # Phần khe nằm trong bóng tối hơn nền nên lõi bỏ sót: nới ra từ lõi, chỉ ở nơi tối bằng hoặc hơn nền và là thung lũng ngang
        # hẹp và sâu (đóng theo chiều ngang rồi lấy chênh lệch). Bóng rộng trên vải trắng không phải thung lũng hẹp nên không bị nới tới.
        gray = img.astype(np.float32) @ luma
        valley = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, np.ones((1, GAP_WIDTH), np.uint8)) - gray >= GAP_DEPTH
        near = cv2.dilate(gap, np.ones((2 * GAP_REACH + 1, 2 * GAP_REACH + 1), np.uint8)) > 0
        ext = (m > 0) & valley & (gray < est @ luma + GAP_TOL) & near
        ext = cv2.morphologyEx(ext.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        gap = np.maximum(gap, ext)
    if not gap.any():
        return m
    gap = cv2.dilate(gap, np.ones((2 * GAP_GROW + 1, 2 * GAP_GROW + 1), np.uint8))
    out = (m > 0) & (gap == 0)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(out.astype(np.uint8), 8)
    if n <= 1:
        return m
    return (lab == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)


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
    # Bỏ khe nền lọt vào mặt nạ (khe giữa tay và thân, khe giữa hai tà) để hoa văn không in lên nền
    before = cands[k]
    after = remove_background_gaps(np.asarray(img), before)
    removed = 1.0 - float(after.sum()) / max(1.0, float(before.sum()))
    if removed > MAX_GAP_FRAC:
        raise RuntimeError(f"bỏ khe nền cắt mất {removed:.0%} mặt nạ áo (tối đa {MAX_GAP_FRAC:.0%}), không phân biệt được khe với bóng đổ; dùng áo khác.")
    return after
