"""Dựng kho phần tử họa tiết từ các vật thể LR3D-CULT2 đã giải nén ở data/lr3d_src/.

Chạy (sau khi chạy scripts/08_extract_lr3d.py):
    uv run --no-project --python .venv/Scripts/python.exe python scripts/09_build_elements.py
    uv run --no-project --python .venv/Scripts/python.exe python scripts/09_build_elements.py --ids 61 83

Đầu ra trong data/elements/ (không commit):
- <object_id>/<element_id>.png : phần tử RGBA
- <object_id>/_sheet.png       : bảng ảnh thu nhỏ để xem bằng mắt
- index.json                   : metadata mọi phần tử (nguồn, giấy phép, phương pháp).
                                 Chạy một phần (--ids) chỉ thay bản ghi của các vật đó, vật khác giữ nguyên.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generation.elements import Config, SamSegmenter, build_object, postfilter, update_index  # noqa: E402

IMAGE_EXT = (".png", ".jpg", ".jpeg")


def find_texture(folder: Path) -> Path:
    """Chọn texture: ưu tiên đúng tên ghi ở dòng map_Kd trong .mtl, nếu không có thì lấy ảnh lớn nhất."""
    imgs = [p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXT]
    mtl = next(folder.glob("*.mtl"), None)
    if mtl:
        m = re.search(r"^\s*map_Kd\s+(.+?)\s*$", mtl.read_text(errors="ignore"), re.MULTILINE)
        if m:
            named = [p for p in imgs if p.name == Path(m.group(1)).name]
            if named:
                return named[0]
    return max(imgs, key=lambda p: p.stat().st_size)


def make_sheet(records: list[dict], path: Path, cell: int = 180, cols: int = 8, limit: int = 48) -> None:
    """Ghép các phần tử lên nền ô vuông xám để thấy rõ kênh trong suốt. Không có phần tử thì xóa bảng cũ."""
    recs = records[:limit]
    if not recs:
        path.unlink(missing_ok=True)
        return
    rows = (len(recs) + cols - 1) // cols
    sheet = np.zeros((rows * cell, cols * cell, 3), np.uint8)
    yy, xx = np.mgrid[0:cell, 0:cell]
    checker = np.where(((yy // 12 + xx // 12) % 2)[..., None] == 0, 200, 150).astype(np.float32).repeat(3, axis=2)
    for i, r in enumerate(recs):
        img = cv2.imdecode(np.fromfile(r["file"], dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        h, w = img.shape[:2]
        k = (cell - 10) / max(h, w)
        img = cv2.resize(img, (max(1, int(w * k)), max(1, int(h * k))), interpolation=cv2.INTER_AREA)
        a = img[..., 3:4].astype(np.float32) / 255
        rgb = img[..., :3][..., ::-1].astype(np.float32)
        tile = checker.copy()
        oy, ox = (cell - img.shape[0]) // 2, (cell - img.shape[1]) // 2
        tile[oy:oy + img.shape[0], ox:ox + img.shape[1]] = a * rgb + (1 - a) * tile[oy:oy + img.shape[0], ox:ox + img.shape[1]]
        tile = np.ascontiguousarray(tile.astype(np.uint8))
        cv2.putText(tile, str(i), (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 0), 1)
        sheet[(i // cols) * cell:(i // cols + 1) * cell, (i % cols) * cell:(i % cols + 1) * cell] = tile
    ok, buf = cv2.imencode(".png", cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR))
    path.write_bytes(buf.tobytes())


def apply_postfilter(recs: list[dict], cfg: Config) -> tuple[list[dict], list[str]]:
    """Bỏ mảnh mỏng và bản gần trùng. Trả về (bản ghi giữ lại, danh sách file PNG cần xóa).

    Việc xóa file làm sau khi ghi index (trong main) để tiến trình chết giữa chừng không để lại index trỏ tới file đã xóa.
    """
    kept, dropped = postfilter(recs, cfg)
    why: dict[str, int] = {}
    for _, w in dropped:
        why[w] = why.get(w, 0) + 1
    print(f"  lọc sau khi xuất: giữ {len(kept)}, bỏ {why or 0}", flush=True)
    return kept, [rec["file"] for rec, _ in dropped]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default="data/lr3d_src")
    ap.add_argument("--out", default="data/elements")
    ap.add_argument("--ids", type=int, nargs="*", help="chỉ xử lý các số vật thể này")
    ap.add_argument("--min-blue", type=float, default=0.15,
                    help="tỉ lệ pixel thiên xanh lam tối thiểu của phần tử (kho lam trắng). Đặt 0 để không lọc màu")
    ap.add_argument("--refilter", action="store_true",
                    help="không chạy SAM, chỉ lọc lại các phần tử đã xuất của --ids (đọc từ index.json)")
    a = ap.parse_args()
    cfg = Config(min_blue_frac=a.min_blue)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    index = out / "index.json"
    if a.refilter:
        # chế độ lọc lại lấy danh sách vật từ index.json, không cần thư mục nguồn
        old = json.loads(index.read_text(encoding="utf-8")) if index.exists() else []
        names = sorted({r["object_id"] for r in old}, key=lambda n: int(n.rsplit("_", 1)[1]))
        if a.ids:
            names = [n for n in names if int(n.rsplit("_", 1)[1]) in a.ids]
        if not names:
            sys.exit("index.json không có vật nào cần lọc lại")
        folders = [Path(a.src) / n for n in names]
    else:
        folders = [f for f in Path(a.src).glob("ceramic_vases_*") if re.fullmatch(r"ceramic_vases_\d+", f.name)]
        folders.sort(key=lambda p: int(p.name.rsplit("_", 1)[1]))
        if a.ids:
            folders = [f for f in folders if int(f.name.rsplit("_", 1)[1]) in a.ids]
        if not folders:
            sys.exit(f"không tìm thấy vật thể nào trong {a.src} (ids: {a.ids})")

    segment = None if a.refilter else SamSegmenter()
    for f in folders:
        if a.refilter:
            recs, to_delete = apply_postfilter([r for r in old if r["object_id"] == f.name], cfg)
        else:
            tex = find_texture(f)
            obj = next(iter(sorted(p for p in f.iterdir() if p.suffix.lower() == ".obj")), None)
            recs, to_delete = apply_postfilter(build_object(tex, obj, f.name, out, segment, cfg), cfg)
        make_sheet(recs, out / f.name / "_sheet.png")
        merged = update_index(index, recs, [f.name])  # ghi ngay sau mỗi vật để lỗi giữa chừng không mất kết quả
        for p in to_delete:
            Path(p).unlink(missing_ok=True)  # chỉ xóa file bị loại sau khi index đã ghi xong
        m = recs[0]["valid_mask_method"] if recs else "-"
        print(f"{f.name}: {len(recs)} phần tử (mặt nạ hợp lệ: {m}), index có {len(merged)} bản ghi", flush=True)


if __name__ == "__main__":
    main()
