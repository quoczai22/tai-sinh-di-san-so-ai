"""Chọn phần tử họa tiết từ kho (data/elements/) làm ảnh nét đầu vào cho ControlNet.

Kho do scripts/data_prep/build_elements.py dựng ngoại tuyến (SAM chỉ chạy lúc đó). Lúc sinh ảnh,
module này chỉ đọc index.json và chọn vài phần tử theo một quy tắc cố định, không chạy SAM.

Quy tắc chọn (tự động, tất định):
1. Điểm của một phần tử = cạnh ngắn của ảnh (pixel) × tỉ lệ nét mực × min(1, mật độ texel tương đối).
   Phần tử to, nhiều nét, không bị kéo giãn thì điểm cao.
2. Chỉ xét phần tử có cạnh ngắn từ MIN_SIDE pixel trở lên. Nếu không đủ k phần tử thì hạ điều kiện này.
3. Xét theo điểm giảm dần, bỏ phần tử gần trùng với phần tử đã chọn (so lỏng hơn lúc dựng kho),
   để bốn biến thể không dùng cùng một họa tiết lặp.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from tsds.generation.pattern import elements as el

from tsds.core.paths import DATA_DIR, HERITAGE_DIR, PANELS_DIR, ROOT
INDEX_PATH = DATA_DIR / "elements" / "index.json"
CROPS_PATH = HERITAGE_DIR / "lr3d_crops.json"
MIN_SIDE = 200  # pixel, dưới mức này phần tử quá nhỏ để cho Canny đủ nét ở khung 512

# So lỏng hơn lúc dựng kho: ở đây chỉ cần bốn phần tử khác nhau, nên gộp cả bản "na ná"
RELAXED = el.Config(dup_iou=0.6, dup_color=0.3, dup_ncc=0.2)


def object_of(heritage_id: str, crops_path: Path = CROPS_PATH) -> Optional[str]:
    """Mã vật thể trong kho tương ứng với mã hiện vật (đọc lr3d_crops.json). None nếu không có."""
    if not Path(crops_path).exists():
        return None
    crops = json.loads(Path(crops_path).read_text(encoding="utf-8"))
    return crops.get(heritage_id, {}).get("object_id")


def score(rec: dict) -> float:
    """Điểm xếp hạng của một phần tử (xem quy tắc ở đầu file)."""
    dens = rec.get("texel_density_rel")
    return float(min(rec["size_wh"])) * float(rec.get("ink_frac", 0.0)) * min(1.0, dens if dens else 1.0)


SOURCES = ("render", "panel", "elements")


def variant_inputs(heritage_id: str, source: str = "render", root: Path = ROOT, panels_dir: Path = PANELS_DIR,
                   index_path: Path = INDEX_PATH, crops_path: Path = CROPS_PATH) -> list[tuple[str, Optional[Path]]]:
    """Ảnh nạp cho 4 biến thể: danh sách 4 cặp (nhãn nguồn, đường dẫn ảnh).

    Đường dẫn None nghĩa là dùng ảnh hiện vật mặc định trong data/heritage/ (với LR3D là ảnh render cả bình).
    Thiếu nguồn được yêu cầu thì quay về bậc thấp hơn: elements, panel, rồi ảnh hiện vật.
    """
    if source not in SOURCES:
        raise ValueError(f"source phải là một trong {SOURCES}, nhận {source!r}")
    if source == "elements":
        picked = pick(heritage_id, 4, root=root, index_path=index_path, crops_path=crops_path)
        if picked:  # thiếu phần tử thì quay vòng cho đủ 4 biến thể
            return [(picked[i % len(picked)]["element_id"], Path(root) / picked[i % len(picked)]["file"])
                    for i in range(4)]
        source = "panel"
    if source == "panel":
        panel = Path(panels_dir) / f"{heritage_id}.png"
        if panel.is_file():
            return [("panel", panel)] * 4
    return [("hien_vat", None)] * 4


def pick(heritage_id: str, k: int = 4, root: Path = ROOT, index_path: Path = INDEX_PATH,
         crops_path: Path = CROPS_PATH) -> list[dict]:
    """Trả về tối đa k bản ghi phần tử đã chọn cho hiện vật. Danh sách rỗng nếu kho chưa có vật đó."""
    obj = object_of(heritage_id, crops_path)
    if obj is None or not Path(index_path).exists():
        return []
    recs = [r for r in json.loads(Path(index_path).read_text(encoding="utf-8"))
            if r["object_id"] == obj and (Path(root) / r["file"]).is_file()]
    big = [r for r in recs if min(r["size_wh"]) >= MIN_SIDE]
    ordered = sorted(big, key=score, reverse=True)
    ordered += sorted([r for r in recs if r not in big], key=score, reverse=True)  # hạ điều kiện nếu thiếu

    chosen: list[dict] = []
    chosen_rots: list[list] = []
    for rec in ordered:
        if len(chosen) >= k:
            break
        try:
            rgba = el.read_rgba(Path(root) / rec["file"])
        except (OSError, ValueError):
            continue  # file hỏng thì bỏ qua phần tử này
        canon = el._canonical(rgba, RELAXED.thumb_size)
        if any(el.is_near_duplicate(canon, rots, RELAXED) for rots in chosen_rots):
            continue
        chosen.append(rec)
        chosen_rots.append(el._rotations(canon[0], canon[1], RELAXED.rot_step))
    return chosen
