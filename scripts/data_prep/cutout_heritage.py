"""Tách nền ảnh hiện vật đang dùng để giao diện chỉ hiện chiếc bình trên nền trang (kèm đổ bóng bằng CSS).

Ảnh render cả bình (data/heritage/LR3D_<số>.png, 512x512) có nền xám phẳng. Mỗi ảnh:
  1. Màu nền = trung vị các pixel ở viền ảnh.
  2. Mặt nạ thô = pixel khác màu nền rõ rệt (khoảng cách màu LAB), đóng lỗ, giữ thành phần lớn nhất.
  3. SAM lấy trọn hình bình (men trắng gần trùng màu nền thì mặt nạ thô bị thiếu), khung bao lấy từ mặt nạ thô.
  4. Làm mềm mép 1 px, cắt sát bình (chừa lề nhỏ), lưu PNG trong suốt.

Ảnh render gốc không bị sửa (pipeline sinh ảnh vẫn dùng mảng hoa văn phẳng). Ảnh tách nền chỉ để hiển thị.

    uv run python scripts/data_prep/cutout_heritage.py            # 6 hiện vật đang dùng
    uv run python scripts/data_prep/cutout_heritage.py LR3D_61    # chọn hiện vật

Ra: data/heritage/cutouts/<mã>.png (RGBA)
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data" / "heritage" / "cutouts"
THRESH = 7.0          # ngưỡng khoảng cách màu LAB so với màu nền
MARGIN = 0.04         # lề chừa quanh bình, theo tỉ lệ cạnh ảnh đã cắt


def background_color(lab: np.ndarray) -> np.ndarray:
    """Màu nền (LAB): trung vị các pixel ở viền ảnh."""
    border = np.concatenate([lab[:6].reshape(-1, 3), lab[-6:].reshape(-1, 3),
                             lab[:, :6].reshape(-1, 3), lab[:, -6:].reshape(-1, 3)])
    return np.median(border, axis=0)


def coarse_mask(rgb: np.ndarray, thresh: float = THRESH) -> np.ndarray:
    """Mặt nạ thô của chiếc bình: khác màu nền, đóng lỗ nhỏ, giữ thành phần liên thông lớn nhất, lấp lỗ trong."""
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    dist = np.linalg.norm(lab - background_color(lab), axis=2)
    m = (cv2.GaussianBlur(dist, (0, 0), 1.0) > thresh).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, lab_img, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n < 2:
        raise RuntimeError("không tách được vật thể khỏi nền")
    m = (lab_img == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(m)
    cv2.drawContours(filled, contours, -1, 1, thickness=cv2.FILLED)
    return filled


def sam_refine(img: Image.Image, coarse: np.ndarray) -> np.ndarray:
    """SAM (cùng mô hình với bước tách áo) lấy trọn hình bình, kể cả chỗ men trắng gần như trùng màu nền.

    Gợi ý: khung bao của mặt nạ thô nới ra 20%, kèm điểm dương ở tâm mặt nạ thô và điểm âm ở bốn góc.
    Trong ba mặt nạ SAM trả về, chọn mặt nạ nhỏ nhất mà vẫn chứa ít nhất 90% mặt nạ thô (mặt nạ lớn hơn thường lấy cả nền).
    """
    import torch                                                    # noqa: PLC0415
    from tsds.generation.garment import garment_sam as gs                         # noqa: PLC0415
    model, proc, dev = gs._model()
    w, h = img.size
    ys, xs = np.where(coarse > 0)
    ex = 0.2 * max(xs.max() - xs.min(), ys.max() - ys.min())
    box = [max(0, xs.min() - ex), max(0, ys.min() - ex), min(w, xs.max() + ex), min(h, ys.max() + ex)]
    center = [int(xs.mean()), int(ys.mean())]
    points = [center, [4, 4], [w - 4, 4], [4, h - 4], [w - 4, h - 4]]
    inputs = proc(img.convert("RGB"), input_boxes=[[box]], input_points=[[points]], input_labels=[[1, 0, 0, 0, 0]],
                  return_tensors="pt").to(dev)
    with torch.no_grad():
        out = model(**inputs, multimask_output=True)
    masks = proc.image_processor.post_process_masks(out.pred_masks.cpu(), inputs["original_sizes"].cpu(),
                                                    inputs["reshaped_input_sizes"].cpu())[0][0]
    scores = out.iou_scores.cpu()[0][0].tolist()
    cands = [gs.clean_mask(m.numpy()) for m in masks]
    keep = [float((c & coarse).sum()) / max(int(coarse.sum()), 1) for c in cands]
    ok = [i for i, k in enumerate(keep) if k >= 0.9] or [int(np.argmax(keep))]
    best = min(ok, key=lambda i: int(cands[i].sum()))              # mặt nạ sát nhất: loại mặt nạ lấy cả nền
    m = cv2.morphologyEx(cands[best], cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))   # cắt các mảng nền nhô ra
    return gs.clean_mask(m)


def cutout(img: Image.Image) -> Image.Image:
    """Ảnh RGBA chỉ có chiếc bình, đã cắt sát."""
    rgb = np.asarray(img.convert("RGB"))
    mask = sam_refine(img, coarse_mask(rgb))
    alpha = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 0.8)
    alpha = np.clip((alpha - 0.15) / 0.7, 0, 1)                      # mép mềm 1 px, không bị mờ lan ra nền
    ys, xs = np.where(mask > 0)
    pad = int(MARGIN * max(xs.max() - xs.min(), ys.max() - ys.min()))
    x0, x1 = max(0, xs.min() - pad), min(rgb.shape[1], xs.max() + 1 + pad)
    y0, y1 = max(0, ys.min() - pad), min(rgb.shape[0], ys.max() + 1 + pad)
    rgba = np.dstack([rgb, (alpha * 255).round().astype(np.uint8)])[y0:y1, x0:x1]
    return Image.fromarray(rgba, "RGBA")


def main(argv: list[str]) -> int:
    from tsds.provenance.registry import all_items                          # noqa: PLC0415
    ids = argv or [it["heritage_id"] for it in all_items(ROOT) if it.get("status", "active") == "active"]
    OUT.mkdir(parents=True, exist_ok=True)
    from tsds.generation.garment import garment_sam                                  # noqa: PLC0415
    for hid in ids:
        src = ROOT / "data" / "heritage" / f"{hid}.png"
        out = cutout(Image.open(src))
        out.save(OUT / f"{hid}.png")
        print(f"{hid}: {Image.open(src).size} -> {out.size}")
    garment_sam.free_model()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
