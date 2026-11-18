"""Cắt phần tử họa tiết (ảnh RGBA) từ texture trải phẳng của vật thể gốm LR3D-CULT2.

Mỗi vật thể có hai thứ liên quan:
- ảnh texture: tấm da phẳng của mô hình 3D, chứa hoa văn thật;
- file .obj: có tọa độ UV (vt) cho biết mỗi mặt của mô hình nằm ở đâu trên texture.

Quy trình cho một vật thể:
1. Vùng hợp lệ = phần texture mà các mặt của mô hình phủ lên (tính từ UV).
   Vùng ngoài (nền đen, vệt nội suy do phần mềm quét ảnh tự lấp) bị loại.
2. Chạy bộ phân đoạn (SAM, chia ảnh thành các ô) để lấy các vùng ứng viên.
3. Lọc ứng viên: đủ lớn, nằm trong vùng hợp lệ, không bị biên ô cắt cụt,
   đủ chi tiết (không phải nền phẳng), không bị kéo giãn, bỏ trùng.
4. Cắt từ ảnh gốc độ phân giải đầy đủ thành ảnh RGBA, giao mặt nạ với vùng hợp lệ,
   giữ nguyên giá trị pixel bên trong mặt nạ (không vẽ lại, không qua diffusion).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np

# Bộ phân đoạn: nhận ảnh RGB uint8 (một ô), trả về danh sách mặt nạ bool cùng kích thước ô.
Segmenter = Callable[[np.ndarray], list]

VERSION = "elements-0.2"


@dataclass
class Config:
    """Tham số cắt phần tử. Giá trị mặc định là đề xuất ban đầu, cần chỉnh sau khi xem ảnh thật."""
    work_max: int = 2048          # cạnh dài tối đa của ảnh làm việc đưa vào SAM
    tile: int = 1024              # kích thước ô SAM (pixel trên ảnh làm việc)
    overlap: int = 512            # phần ô chồng nhau: phần tử rộng đến mức này luôn nằm trọn trong ít nhất một ô
    min_tile_valid: float = 0.25  # ô có ít hơn 25% vùng hợp lệ thì bỏ qua
    min_side_src: int = 96        # cạnh ngắn nhất của khung bao, tính theo pixel ảnh gốc
    max_area_frac: float = 0.5    # phần tử không được chiếm quá 50% vùng hợp lệ (tránh mặt nạ cả bề mặt)
    min_inside_valid: float = 0.98  # tỉ lệ mặt nạ (ở ảnh làm việc) nằm trong vùng hợp lệ
    min_std: float = 15.0         # độ lệch chuẩn độ sáng tối thiểu (loại vùng phẳng)
    iou_dup: float = 0.6          # IoU lớn hơn mức này coi là trùng
    pad: int = 6                  # viền thêm quanh phần tử khi cắt (pixel ảnh gốc)
    erode_px: int = 2             # co mặt nạ vào để không lấy lẹm pixel nền (pixel ảnh gốc)
    max_per_object: int = 60      # giới hạn số phần tử mỗi vật thể
    min_ink_frac: float = 0.12    # phần tử phải có ít nhất 12% pixel sẫm hơn nền men (loại mảng nền trắng)
    ink_margin: float = 40.0      # pixel được coi là nét mực nếu sẫm hơn nền men ít nhất 40 mức xám
    min_density_rel: float = 0.45  # mật độ texel tương đối tối thiểu (loại vùng bị kéo giãn nên mờ)
    hu_dist: float = 0.25         # khoảng cách hình dạng (mô-men Hu) dưới mức này và diện tích gần nhau là trùng
    hu_dist_any: float = 0.08     # hình bất đối xứng gần như y hệt thì coi là trùng, bất kể cỡ
    speck_frac: float = 0.03      # mảnh rời nhỏ hơn 3% diện tích mặt nạ bị bỏ
    min_blue_frac: float = 0.0    # tỉ lệ pixel thiên xanh lam tối thiểu (0 là không lọc theo màu)


@dataclass
class Region:
    """Một vùng ứng viên: mặt nạ bool cắt theo khung bao, tọa độ trên ảnh làm việc."""
    mask: np.ndarray
    x0: int
    y0: int

    @property
    def area(self) -> int:
        return int(self.mask.sum())

    @property
    def box(self) -> tuple[int, int, int, int]:
        h, w = self.mask.shape
        return self.x0, self.y0, self.x0 + w, self.y0 + h


# ---------- Đọc và ghi ảnh (qua byte để chạy được với đường dẫn có dấu tiếng Việt trên Windows) ----------

def read_rgb(path: Path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    bgr = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(f"không đọc được ảnh: {path}")
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def write_rgba_png(path: Path, rgba: np.ndarray) -> None:
    ok, buf = cv2.imencode(".png", cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
    if not ok:
        raise IOError(f"không mã hóa được PNG: {path}")
    Path(path).write_bytes(buf.tobytes())


# ---------- 1. Vùng hợp lệ từ UV ----------

def read_obj_polygons(obj_path: Path) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Đọc các mặt trong .obj. Trả về (danh sách đa giác UV (n,2), danh sách đa giác 3D (n,3)), cùng thứ tự."""
    v: list[tuple[float, float, float]] = []
    vt: list[tuple[float, float]] = []
    uvs: list[np.ndarray] = []
    xyz: list[np.ndarray] = []
    with open(obj_path, "r", errors="ignore") as f:
        for line in f:
            if line.startswith("v "):
                p = line.split()
                v.append((float(p[1]), float(p[2]), float(p[3])))
            elif line.startswith("vt "):
                p = line.split()
                vt.append((float(p[1]), float(p[2])))
            elif line.startswith("f "):
                vi, ti = [], []
                for tok in line.split()[1:]:
                    parts = tok.split("/")
                    if len(parts) < 2 or not parts[1]:
                        vi = []
                        break  # mặt không có UV thì bỏ qua
                    a, b = int(parts[0]), int(parts[1])
                    vi.append(len(v) + a if a < 0 else a - 1)  # chỉ số âm là tương đối
                    ti.append(len(vt) + b if b < 0 else b - 1)
                if len(vi) >= 3 and all(0 <= i < len(v) for i in vi) and all(0 <= i < len(vt) for i in ti):
                    uvs.append(np.array([vt[i] for i in ti], dtype=np.float64))
                    xyz.append(np.array([v[i] for i in vi], dtype=np.float64))
    return uvs, xyz


def read_uv_polygons(obj_path: Path) -> list[np.ndarray]:
    """Chỉ phần UV của read_obj_polygons."""
    return read_obj_polygons(obj_path)[0]


def uv_out_of_range_frac(polys: list[np.ndarray]) -> float:
    """Tỉ lệ mặt có tọa độ UV nằm ngoài [0,1] (nếu khác 0 thì texture có thể lát lặp, cách xử lý hiện tại không đúng)."""
    if not polys:
        return 0.0
    return float(np.mean([bool(((p < -1e-6) | (p > 1 + 1e-6)).any()) for p in polys]))


def _to_pixels(uv: np.ndarray, width: int, height: int) -> np.ndarray:
    x = np.clip(uv[:, 0], 0, 1) * (width - 1)
    y = (1 - np.clip(uv[:, 1], 0, 1)) * (height - 1)  # trục v của UV hướng lên, trục y của ảnh hướng xuống
    return np.stack([x, y], axis=1)


def uv_valid_mask(obj_path: Path, width: int, height: int, erode: int = 2) -> Optional[np.ndarray]:
    """Mặt nạ bool: pixel texture nào được ít nhất một mặt của mô hình phủ lên. None nếu .obj không có UV."""
    polys = read_uv_polygons(obj_path)
    if not polys:
        return None
    pts = [np.round(_to_pixels(p, width, height)).astype(np.int32) for p in polys]
    mask = np.zeros((height, width), np.uint8)
    cv2.fillPoly(mask, pts, 255)
    if erode > 0:
        mask = cv2.erode(mask, np.ones((2 * erode + 1, 2 * erode + 1), np.uint8))
    return mask > 0


def _fan_area(p: np.ndarray) -> float:
    """Diện tích đa giác (2D hoặc 3D) bằng cách chia thành tam giác quạt từ đỉnh đầu."""
    a = p[1:-1] - p[0]
    b = p[2:] - p[0]
    if p.shape[1] == 2:
        return float(np.abs(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]).sum() / 2)
    return float(np.linalg.norm(np.cross(a, b), axis=1).sum() / 2)


def texel_density_map(obj_path: Path, width: int, height: int) -> Optional[np.ndarray]:
    """Bản đồ mật độ texel: mỗi pixel texture ứng với bao nhiêu pixel trên một đơn vị chiều dài bề mặt 3D.

    Chỗ mật độ thấp là chỗ texture bị kéo giãn để phủ bề mặt, ảnh ở đó thường mờ. Trả về None nếu không có UV.
    """
    uvs, xyz = read_obj_polygons(obj_path)
    if not uvs:
        return None
    dens = np.zeros((height, width), np.float32)
    for uv, p in zip(uvs, xyz):
        px = _to_pixels(uv, width, height)
        a3, auv = _fan_area(p), _fan_area(px)
        if a3 <= 1e-12 or auv <= 0:
            continue
        val = float(np.sqrt(auv / a3))
        pi = np.round(px).astype(np.int32)
        for i in range(1, len(pi) - 1):  # chia tam giác quạt để luôn là đa giác lồi
            cv2.fillConvexPoly(dens, np.array([pi[0], pi[i], pi[i + 1]]), val)
    return dens


def nonblack_mask(rgb: np.ndarray, thr: int = 25) -> np.ndarray:
    """Phương án dự phòng khi không có UV: pixel nào không đen thì coi là hợp lệ."""
    m = (rgb.max(axis=2) > thr).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return m > 0


def get_valid_mask(rgb: np.ndarray, obj_path: Optional[Path], min_uv_coverage: float = 0.10) -> tuple[np.ndarray, str, Optional[float]]:
    """Trả về (mặt nạ hợp lệ, phương pháp, tỉ lệ phủ UV).

    Ưu tiên UV. Nếu UV phủ dưới min_uv_coverage (nghĩa là phần lớn texture không gắn với mô hình,
    ví dụ vật #15) hoặc không có UV thì dùng phương án dự phòng loại nền đen, và ghi rõ vào phương pháp.
    """
    h, w = rgb.shape[:2]
    cov = None
    if obj_path is not None and Path(obj_path).exists():
        m = uv_valid_mask(Path(obj_path), w, h)
        if m is not None:
            cov = round(float(m.mean()), 4)
            if cov >= min_uv_coverage:
                return m, "uv", cov
    return nonblack_mask(rgb), "nonblack", cov


# ---------- 2. Vùng ứng viên bằng phân đoạn theo ô ----------

def _starts(dim: int, tile: int, stride: int) -> list[int]:
    """Các tọa độ bắt đầu của ô dọc một trục, ô cuối luôn chạm mép ảnh."""
    if dim <= tile:
        return [0]
    s = list(range(0, dim - tile, stride))
    s.append(dim - tile)
    return s


def _drop_specks(m: np.ndarray, frac: float) -> np.ndarray:
    """Bỏ các mảnh rời nhỏ hơn frac diện tích mặt nạ (đốm nhiễu dính theo phần tử)."""
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    if n <= 2:
        return m
    areas = st[1:, cv2.CC_STAT_AREA]
    keep = [i + 1 for i, a in enumerate(areas) if a >= frac * areas.sum()]
    return np.isin(lab, keep)


def _region_from_mask(m: np.ndarray, x0: int, y0: int) -> Optional[Region]:
    ys, xs = np.nonzero(m)
    if len(ys) == 0:
        return None
    bx0, bx1, by0, by1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    return Region(m[by0:by1, bx0:bx1].astype(bool), x0 + int(bx0), y0 + int(by0))


def propose_regions(rgb: np.ndarray, valid: np.ndarray, segment: Segmenter, cfg: Config):
    """Chạy bộ phân đoạn theo ô trên ảnh làm việc.

    Trả về (ảnh làm việc, vùng hợp lệ làm việc, (sx, sy) là tỉ lệ ảnh làm việc trên ảnh gốc, các vùng).
    """
    h, w = rgb.shape[:2]
    s = min(1.0, cfg.work_max / max(h, w))
    ww, wh = max(1, round(w * s)), max(1, round(h * s))
    scale = (ww / w, wh / h)  # tỉ lệ thực sau khi làm tròn kích thước, dùng để đổi tọa độ cho chính xác
    work = cv2.resize(rgb, (ww, wh), interpolation=cv2.INTER_AREA)
    vw = cv2.resize(valid.astype(np.uint8), (ww, wh), interpolation=cv2.INTER_NEAREST).astype(bool)
    work = work.copy()
    work[~vw] = 128  # tô xám vùng không hợp lệ để bộ phân đoạn không coi nó là họa tiết

    stride = max(1, cfg.tile - cfg.overlap)
    regions: list[Region] = []
    for y0 in _starts(wh, cfg.tile, stride):
        for x0 in _starts(ww, cfg.tile, stride):
            th, tw = min(cfg.tile, wh - y0), min(cfg.tile, ww - x0)
            if vw[y0:y0 + th, x0:x0 + tw].mean() < cfg.min_tile_valid:
                continue
            for m in segment(work[y0:y0 + th, x0:x0 + tw]):
                r = _region_from_mask(_drop_specks(np.asarray(m, dtype=bool), cfg.speck_frac), x0, y0)
                if r is None:
                    continue
                bx0, by0 = r.x0 - x0, r.y0 - y0
                bx1, by1 = bx0 + r.mask.shape[1], by0 + r.mask.shape[0]
                # vùng chạm biên ô (mà biên đó không phải mép ảnh) có thể đã bị cắt cụt, bỏ đi
                if (bx0 == 0 and x0 > 0) or (by0 == 0 and y0 > 0) \
                        or (bx1 == tw and x0 + tw < ww) or (by1 == th and y0 + th < wh):
                    continue
                regions.append(r)
    return work, vw, scale, regions


# ---------- 3. Lọc và bỏ trùng ----------

def _full_slice(r: Region):
    return slice(r.y0, r.y0 + r.mask.shape[0]), slice(r.x0, r.x0 + r.mask.shape[1])


def iou(a: Region, b: Region) -> float:
    """IoU của hai vùng (cùng hệ tọa độ ảnh làm việc)."""
    ax0, ay0, ax1, ay1 = a.box
    bx0, by0, bx1, by1 = b.box
    x0, y0, x1, y1 = max(ax0, bx0), max(ay0, by0), min(ax1, bx1), min(ay1, by1)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    ma = a.mask[y0 - ay0:y1 - ay0, x0 - ax0:x1 - ax0]
    mb = b.mask[y0 - by0:y1 - by0, x0 - bx0:x1 - bx0]
    inter = int((ma & mb).sum())
    union = a.area + b.area - inter
    return inter / union if union else 0.0


def _shape_key(r: Region) -> tuple[np.ndarray, bool]:
    """Đặc trưng hình dạng không đổi khi xoay và đổi tỉ lệ: ba mô-men Hu đầu, lấy log.

    Cờ thứ hai cho biết hình có đủ bất đối xứng (Hu2, Hu3 lớn hơn nhiễu số) để so khớp bất kể cỡ.
    """
    hu = cv2.HuMoments(cv2.moments(r.mask.astype(np.uint8), binaryImage=True))[:3, 0]
    informative = bool(abs(hu[1]) > 1e-6 and abs(hu[2]) > 1e-8)
    return -np.sign(hu) * np.log10(np.abs(hu) + 1e-30), informative


def filter_regions(work: np.ndarray, vw: np.ndarray, scale: tuple[float, float], regions: list[Region], cfg: Config,
                   dens: Optional[np.ndarray] = None) -> list[tuple[Region, dict]]:
    """Giữ vùng đạt yêu cầu và bỏ trùng. Trả về danh sách (vùng, số đo).

    dens: bản đồ mật độ texel ở kích thước ảnh làm việc (None thì bỏ qua điều kiện kéo giãn).
    """
    sx, sy = scale
    gray = cv2.cvtColor(work, cv2.COLOR_RGB2GRAY).astype(np.float32)
    total_valid = max(int(vw.sum()), 1)
    ground = float(np.percentile(gray[vw], 90)) if vw.any() else 255.0  # mức sáng của nền men
    dens_med = None
    if dens is not None:
        d = dens[vw & (dens > 0)]
        dens_med = float(np.median(d)) if d.size else None
    kept: list[tuple[Region, dict]] = []
    keys: list[tuple[np.ndarray, bool]] = []
    for r in sorted(regions, key=lambda r: r.area, reverse=True):  # lớn trước để giữ bản đầy đủ
        h, w = r.mask.shape
        if min(w / sx, h / sy) < cfg.min_side_src:
            continue
        if r.area / total_valid > cfg.max_area_frac:
            continue
        sl = _full_slice(r)
        inside = float(vw[sl][r.mask].mean())
        if inside < cfg.min_inside_valid:
            continue
        g = gray[sl][r.mask]
        std = float(g.std())
        if std < cfg.min_std:
            continue
        ink = float((g < ground - cfg.ink_margin).mean())
        if ink < cfg.min_ink_frac:
            continue
        px = work[sl][r.mask].astype(np.int32)
        blue = float(((px[:, 2] > px[:, 0] + 12) & (px[:, 2] >= px[:, 1])).mean())  # thiên xanh lam
        if blue < cfg.min_blue_frac:
            continue
        rel = None
        if dens_med:
            dv = dens[sl][r.mask]
            dv = dv[dv > 0]  # bỏ khe làm tròn không có dữ liệu mật độ
            if dv.size:
                rel = float(np.median(dv)) / dens_med
                if rel < cfg.min_density_rel:
                    continue
        if any(iou(r, k) > cfg.iou_dup for k, _ in kept):
            continue
        key, inf = _shape_key(r)
        dup = False
        for (k, k_inf), (k_r, _) in zip(keys, kept):
            d = float(np.linalg.norm(key - k))
            if (inf and k_inf and d < cfg.hu_dist_any) or (d < cfg.hu_dist and 0.67 < r.area / max(k_r.area, 1) < 1.5):
                dup = True  # cùng hình dạng với một phần tử đã giữ (họa tiết lặp)
                break
        if dup:
            continue
        keys.append((key, inf))
        kept.append((r, {"inside_valid": round(inside, 4), "std_luma": round(std, 1), "ink_frac": round(ink, 3),
                         "blue_frac": round(blue, 3),
                         "texel_density_rel": None if rel is None else round(rel, 3),
                         "area_frac_valid": round(r.area / total_valid, 4)}))
        if len(kept) >= cfg.max_per_object:
            break
    return kept


# ---------- 4. Cắt ảnh RGBA từ ảnh gốc ----------

def to_rgba(rgb: np.ndarray, r: Region, scale: tuple[float, float], cfg: Config,
            valid: Optional[np.ndarray] = None) -> Optional[tuple[np.ndarray, tuple[int, int, int, int]]]:
    """Cắt phần tử từ ảnh gốc. Trả về (ảnh RGBA, khung bao trên ảnh gốc), hoặc None nếu mặt nạ rỗng.

    Mặt nạ được giao với vùng hợp lệ ở độ phân giải gốc, nên không có pixel alpha 255 nào nằm ngoài UV.
    """
    sx, sy = scale
    H, W = rgb.shape[:2]
    bx0, by0, bx1, by1 = r.box
    x0, y0 = int(np.floor(bx0 / sx)), int(np.floor(by0 / sy))
    x1, y1 = min(W, int(np.ceil(bx1 / sx))), min(H, int(np.ceil(by1 / sy)))
    mask = cv2.resize(r.mask.astype(np.float32), (x1 - x0, y1 - y0), interpolation=cv2.INTER_LINEAR) > 0.5
    if valid is not None:
        mask &= valid[y0:y1, x0:x1]
    if cfg.erode_px > 0:
        k = np.ones((2 * cfg.erode_px + 1, 2 * cfg.erode_px + 1), np.uint8)
        mask = cv2.erode(mask.astype(np.uint8), k) > 0
    if not mask.any():
        return None
    # thêm viền, nhưng không vượt khỏi ảnh gốc
    px0, py0 = max(0, x0 - cfg.pad), max(0, y0 - cfg.pad)
    px1, py1 = min(W, x1 + cfg.pad), min(H, y1 + cfg.pad)
    full = np.zeros((py1 - py0, px1 - px0), np.uint8)
    full[y0 - py0:y1 - py0, x0 - px0:x1 - px0] = mask.astype(np.uint8) * 255
    alpha = cv2.GaussianBlur(full, (0, 0), 1.0)  # làm mềm mép một chút
    alpha[full == 255] = 255                       # phần lõi giữ đặc, không làm nhạt pixel trong mặt nạ
    alpha[(full == 0) & (alpha < 4)] = 0
    color = rgb[py0:py1, px0:px1].copy()
    # pixel trong suốt hẳn mang màu trung bình của phần tử, tránh quầng nền (đen hoặc men) khi thu phóng
    color[alpha == 0] = color[full == 255].mean(axis=0).astype(np.uint8)
    return np.dstack([color, alpha]), (px0, py0, px1, py1)


# ---------- Ghép lại cho một vật thể ----------

def build_object(texture_path: Path, obj_path: Optional[Path], object_id: str, out_dir: Path,
                 segment: Segmenter, cfg: Config = Config()) -> list[dict]:
    """Cắt toàn bộ phần tử của một vật thể, ghi PNG vào out_dir/object_id và trả về danh sách bản ghi."""
    rgb = read_rgb(Path(texture_path))
    valid, method, uv_cov = get_valid_mask(rgb, obj_path)
    work, vw, scale, regions = propose_regions(rgb, valid, segment, cfg)
    dens = None
    if method == "uv":  # mật độ texel chỉ có nghĩa khi texture thật sự được ánh xạ lên mô hình
        dens = texel_density_map(Path(obj_path), work.shape[1], work.shape[0])
    kept = filter_regions(work, vw, scale, regions, cfg, dens)

    folder = Path(out_dir) / object_id
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob(f"{object_id}_e*.png"):
        old.unlink()  # xóa kết quả của lần chạy trước để không lẫn phần tử cũ
    records = []
    for r, stats in kept:
        cut = to_rgba(rgb, r, scale, cfg, valid)
        if cut is None:
            continue
        rgba, box = cut
        eid = f"{object_id}_e{len(records):03d}"
        path = folder / f"{eid}.png"
        write_rgba_png(path, rgba)
        records.append({
            "element_id": eid,
            "object_id": object_id,
            "source_dataset": "LR3D-CULT2",
            "source_doi": "10.17632/jr23fnrvx2.1",
            "texture_file": Path(texture_path).name,
            "box_xyxy": list(box),
            "size_wh": [rgba.shape[1], rgba.shape[0]],
            "valid_mask_method": method,
            "uv_coverage": uv_cov,
            "candidates_before_filter": len(regions),
            **stats,
            "license_status": "unverified",
            "origin_note": "chưa xác minh vật có phải Bát Tràng hay không",
            "method_version": VERSION,
            "file": str(path).replace("\\", "/"),
        })
    return records


def update_index(path: Path, records: list[dict], object_ids: list[str]) -> list[dict]:
    """Gộp bản ghi mới vào index.json: bản ghi cũ của các vật vừa xử lý bị thay, vật khác giữ nguyên."""
    path = Path(path)
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    merged = [r for r in old if r["object_id"] not in set(object_ids)] + records
    merged.sort(key=lambda r: r["element_id"])
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
    return merged


# ---------- Bộ phân đoạn SAM (cần GPU/mô hình, không dùng trong test) ----------

class SamSegmenter:
    """Phân đoạn tự động bằng SAM (Segment Anything): rải lưới điểm trên ảnh và sinh mặt nạ cho từng điểm."""

    def __init__(self, model_id: str = "facebook/sam-vit-base", device: int = 0,
                 points_per_batch: int = 64, pred_iou_thresh: float = 0.85, stability_score_thresh: float = 0.9):
        from transformers import pipeline  # import muộn để module chạy được khi chưa cài torch
        self.pipe = pipeline("mask-generation", model=model_id, device=device)
        self.kw = dict(points_per_batch=points_per_batch, pred_iou_thresh=pred_iou_thresh,
                       stability_score_thresh=stability_score_thresh)

    def __call__(self, rgb: np.ndarray) -> list:
        from PIL import Image
        out = self.pipe(Image.fromarray(rgb), **self.kw)
        return [np.asarray(m, dtype=bool) for m in out["masks"]]
