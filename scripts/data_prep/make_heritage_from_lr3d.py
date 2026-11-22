"""Tạo ảnh "hiện vật" cho hệ thống từ vật thể LR3D-CULT2 (thay cho ảnh chụp bình cũ).

Chạy (sau scripts/data_prep/extract_lr3d.py):
    uv run --no-project --python .venv/Scripts/python.exe python scripts/data_prep/make_heritage_from_lr3d.py

Mỗi vật thể cho hai ảnh:
- Ảnh hiện vật mặc định = ảnh render cả bình (script 08 đã trích), đúng luồng hồ sơ gốc.
- Mảng texture phẳng (biến thể so sánh), cắt tự động:
  1. Vùng hợp lệ = phần texture được mô hình 3D phủ lên (UV), như tsds/generation/pattern/elements.py.
  2. Tách các mảnh UV rời nhau (đảo). Chọn đảo có nhiều nét mực nhất (diện tích nhân tỉ lệ pixel sẫm hơn nền men).
  3. Cắt khung bao của đảo, thu nhỏ nếu cạnh dài hơn 2048 pixel, kênh alpha là mặt nạ của đảo.
  Ảnh ra là PNG RGBA: tsds/generation/pattern/controlnet.py đã biết dùng kênh alpha làm mặt nạ món đồ.
Không dùng mặt nạ tay. Việc chọn 6 vật thể là bước chọn nguồn, ghi ở SELECTED bên dưới.

Đầu ra:
- data/heritage/LR3D_<số>.png         : ảnh render cả bình (ảnh hiện vật mặc định)
- data/heritage/panels/LR3D_<số>.png  : mảng texture phẳng
- data/heritage/lr3d_crops.json       : khung cắt mảng, nguồn ảnh render, để ghi vào hồ sơ nguồn
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tsds.generation.pattern.elements import get_valid_mask, read_rgb  # noqa: E402

# 6 vật chọn bằng mắt ngày 18/11/2026 từ 14 vật lam trắng sạch (xem docs/HUONG_CAI_TIEN_V2.md mục 2.2)
SELECTED = [33, 61, 50, 38, 97, 124]
MAX_SIDE = 2048
IMAGE_EXT = (".png", ".jpg", ".jpeg")


def find_texture(folder: Path) -> Path:
    """Texture ghi ở map_Kd trong .mtl, nếu không có thì lấy ảnh lớn nhất."""
    imgs = [p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXT]
    mtl = next(folder.glob("*.mtl"), None)
    if mtl:
        m = re.search(r"^\s*map_Kd\s+(.+?)\s*$", mtl.read_text(errors="ignore"), re.MULTILINE)
        if m:
            named = [p for p in imgs if p.name == Path(m.group(1)).name]
            if named:
                return named[0]
    return max(imgs, key=lambda p: p.stat().st_size)


def islands(valid: np.ndarray, small: int = 2048) -> tuple[np.ndarray, int]:
    """Gán nhãn từng đảo UV. Đếm ở ảnh thu nhỏ rồi phóng nhãn về kích thước gốc."""
    h, w = valid.shape
    k = min(1.0, small / max(h, w))
    v = cv2.resize(valid.astype(np.uint8), (max(1, int(w * k)), max(1, int(h * k))), interpolation=cv2.INTER_NEAREST)
    v = cv2.morphologyEx(v, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))  # chỉ nối khe hở li ti, không nối các đảo gần nhau
    n, lab = cv2.connectedComponents(v, connectivity=8)
    lab_full = cv2.resize(lab.astype(np.int32), (w, h), interpolation=cv2.INTER_NEAREST)
    return lab_full, n - 1


def best_island(rgb: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, dict]:
    """Chọn đảo có nhiều nét mực lam nhất (diện tích nhân tỉ lệ nét mực nhân tỉ lệ pixel thiên xanh lam).

    Nhân thêm tỉ lệ xanh lam vì kho này là gốm men lam trắng: không có nó thì đáy bình nâu sẫm
    (nhiều pixel tối) thắng các mảng hoa văn lam.
    """
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    ground = float(np.percentile(gray[valid], 90))  # mức sáng của nền men
    r, g, b = (rgb[..., c].astype(np.int16) for c in range(3))
    bluish = (b > r + 12) & (b >= g)
    lab, n = islands(valid)
    best, best_score, info = None, -1.0, {}
    for i in range(1, n + 1):
        m = (lab == i) & valid
        area = int(m.sum())
        if area < 0.01 * valid.sum():
            continue
        ink = float((gray[m] < ground - 40).mean())
        blue = float(bluish[m].mean())
        score = area * ink * blue
        if score > best_score:
            best, best_score = m, score
            info = {"island_area_px": area, "ink_frac": round(ink, 3), "blue_frac": round(blue, 3)}
    if best is None:
        raise RuntimeError("không tìm thấy đảo UV nào đủ lớn")
    return drop_thin_attachments(best), {**info, "islands_found": n}


def drop_thin_attachments(mask: np.ndarray, small: int = 1024) -> np.ndarray:
    """Bỏ các mảnh nhỏ dính vào đảo chính qua một cổ hẹp (ví dụ đĩa dán nhãn kiểm kê ở đáy vật #38).

    Ở ảnh thu nhỏ: mở hình thái với nhân lớn để cắt cổ hẹp, giữ thành phần lớn nhất, nở ra lại rồi giao với mặt nạ gốc.
    """
    h, w = mask.shape
    k = min(1.0, small / max(h, w))
    sm = cv2.resize(mask.astype(np.uint8), (max(1, int(w * k)), max(1, int(h * k))), interpolation=cv2.INTER_NEAREST)
    r = max(3, small // 12)  # nhân đủ lớn để bỏ cả đĩa nhỏ dán nhãn dính ở rìa (đường kính khoảng 7% cạnh dài)
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (r, r))
    op = cv2.morphologyEx(sm, cv2.MORPH_OPEN, ker)
    n, lab, st, _ = cv2.connectedComponentsWithStats(op, connectivity=8)
    if n <= 1:
        return mask
    big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    keep = cv2.dilate((lab == big).astype(np.uint8), ker)
    keep_full = cv2.resize(keep, (w, h), interpolation=cv2.INTER_NEAREST) > 0
    return mask & keep_full


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default="data/raw/lr3d_src")
    ap.add_argument("--out", default="data/heritage")
    ap.add_argument("--ids", type=int, nargs="*", default=SELECTED)
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    panels = out / "panels"
    panels.mkdir(exist_ok=True)
    crops_file = out / "lr3d_crops.json"
    # chạy một phần (--ids) chỉ thay bản ghi của các vật đó, giữ bản ghi của vật khác
    records = json.loads(crops_file.read_text(encoding="utf-8")) if crops_file.exists() else {}
    for n in a.ids:
        folder = Path(a.src) / f"ceramic_vases_{n}"
        render_src = folder / "render.png"
        if not render_src.is_file():  # kiểm tra trước khi ghi bất cứ file nào của vật này
            raise FileNotFoundError(f"chưa có {render_src}, chạy scripts/data_prep/extract_lr3d.py trước")
        tex = find_texture(folder)
        obj = next(iter(sorted(p for p in folder.iterdir() if p.suffix.lower() == ".obj")), None)
        rgb = read_rgb(tex)
        valid, method, cov = get_valid_mask(rgb, obj)
        mask, info = best_island(rgb, valid)
        ys, xs = np.where(mask)
        x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
        crop = rgb[y0:y1, x0:x1].copy()
        alpha = (mask[y0:y1, x0:x1].astype(np.uint8)) * 255
        s = min(1.0, MAX_SIDE / max(crop.shape[:2]))
        if s < 1.0:
            size = (max(1, round(crop.shape[1] * s)), max(1, round(crop.shape[0] * s)))
            crop = cv2.resize(crop, size, interpolation=cv2.INTER_AREA)
            alpha = cv2.resize(alpha, size, interpolation=cv2.INTER_AREA)
            alpha = (alpha > 127).astype(np.uint8) * 255
        rgba = np.dstack([crop, alpha])
        name = f"LR3D_{n}"
        ok, buf = cv2.imencode(".png", cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
        if not ok:
            raise IOError(f"không mã hóa được PNG cho {name}")
        (panels / f"{name}.png").write_bytes(buf.tobytes())
        # ảnh hiện vật mặc định = ảnh render cả bình (đã trích bởi script 08), đúng luồng hồ sơ gốc
        shutil.copyfile(render_src, out / f"{name}.png")
        rsrc = folder / "render_source.json"
        render_info = json.loads(rsrc.read_text(encoding="utf-8")) if rsrc.is_file() else {}
        records[name] = {"object_id": f"ceramic_vases_{n}", "render_source": render_info,
                         "texture_file": tex.name, "valid_mask_method": method,
                         "uv_coverage": cov, "crop_box_xyxy": [x0, y0, x1, y1], "scale": round(s, 4),
                         "size_wh": [int(rgba.shape[1]), int(rgba.shape[0])], **info}
        crops_file.write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")  # ghi sau mỗi vật
        print(name, records[name], flush=True)


if __name__ == "__main__":
    main()
