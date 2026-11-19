"""Giải nén texture, mô hình .obj và .mtl của các vật thể đã chọn từ LR3D-CULT2.

Chạy:
    uv run --no-project --python .venv/Scripts/python.exe python scripts/08_extract_lr3d.py

Đầu vào : data/LR3D-CULT2 ... .zip (file zip ngoài, bên trong có 6 zip bình gốm lồng nhau).
Đầu ra  : data/lr3d_src/ceramic_vases_<số>/ gồm .obj, .mtl và file texture.
Dữ liệu thô, đã khai báo trong .gitignore, không commit.
"""
import argparse
import json
import re
import shutil
import zipfile
from pathlib import Path

# 14 vật lam trắng có mảng hoa văn sạch, chọn bằng mắt ngày 18/11/2026.
# Xem docs/HUONG_CAI_TIEN_V2.md mục 2.2. Đây là bước chọn nguồn, được ghi lại ở đây.
SELECTED = [15, 33, 37, 38, 47, 50, 59, 61, 78, 83, 97, 118, 119, 124]

IMAGE_EXT = (".png", ".jpg", ".jpeg")
RENDER_CAM, RENDER_FRAME = "1", 1  # ảnh render dùng làm "ảnh hiện vật": camera 1, khung 1 (góc nhìn gần chính diện)


def nested_zip_of(n: int) -> str:
    """Số vật thể -> tên zip lồng chứa nó (đã đo: zip 1 là #1 đến #20, ..., zip 6 là #101 đến #124)."""
    return f"ceramic_vases_{6 if n > 100 else (n - 1) // 20 + 1}.zip"


def pick_texture(names: list[str], folder: str, mtl_text: str) -> str:
    """Chọn file texture màu: ưu tiên dòng map_Kd trong .mtl, nếu không có thì lấy ảnh lớn nhất."""
    m = re.search(r"^\s*map_Kd\s+(.+?)\s*$", mtl_text, re.MULTILINE)
    if m:
        cand = f"{folder}/{Path(m.group(1).strip()).name}"
        if cand in names:
            return cand
    return ""  # để nơi gọi dùng phương án dự phòng


def extract(outer: Path, dest: Path, wanted: list[int]) -> None:
    if any(n <= 0 for n in wanted):
        raise SystemExit("số vật thể phải lớn hơn 0")
    tmp = dest / "_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    by_zip: dict[str, list[int]] = {}
    for n in wanted:
        by_zip.setdefault(nested_zip_of(n), []).append(n)

    try:
        _extract(outer, dest, tmp, by_zip)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)  # luôn xóa zip lồng tạm (vài GB), kể cả khi lỗi giữa chừng


def _extract(outer: Path, dest: Path, tmp: Path, by_zip: dict[str, list[int]]) -> None:
    with zipfile.ZipFile(outer) as zo:
        entries = {Path(e.filename).name: e for e in zo.infolist() if e.filename.endswith(".zip")}
        for zname, nums in sorted(by_zip.items()):
            if zname not in entries:
                raise SystemExit(f"zip ngoài không chứa {zname}")
            inner_path = tmp / zname
            # giải nén zip lồng ra file tạm (tên do mình đặt, không lấy từ zip)
            with zo.open(entries[zname]) as src, open(inner_path, "wb") as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
            with zipfile.ZipFile(inner_path) as zi:
                names = zi.namelist()
                for n in nums:
                    folder = f"ceramic_vases_{n}"
                    out = dest / folder
                    out.mkdir(parents=True, exist_ok=True)
                    top = [x for x in names if x.startswith(folder + "/") and x.count("/") == 1 and not x.endswith("/")]
                    mtl = next((x for x in top if x.lower().endswith(".mtl")), None)
                    obj = next((x for x in top if x.lower().endswith(".obj")), None)
                    mtl_text = zi.read(mtl).decode("utf-8", "ignore") if mtl else ""
                    tex = pick_texture(names, folder, mtl_text)
                    if not tex:
                        imgs = [x for x in top if x.lower().endswith(IMAGE_EXT)]
                        tex = max(imgs, key=lambda x: zi.getinfo(x).file_size)
                    for member in filter(None, [mtl, obj, tex]):
                        # ghi bằng tên file do mình tạo từ tên gốc, không dùng đường dẫn trong zip
                        with zi.open(member) as s, open(out / Path(member).name, "wb") as d:
                            shutil.copyfileobj(s, d, 1 << 20)
                    # ảnh render cả bình: camera 1, khung 1. Góc cố định, không chọn tay; tên file ra do mình đặt
                    pat = re.compile(rf"^{re.escape(folder)}/images/[^/]+_CAM{RENDER_CAM}_1\.{RENDER_FRAME:04d}\.png$")
                    render = next((x for x in names if pat.match(x)), None)
                    if render:
                        with zi.open(render) as s, open(out / "render.png", "wb") as d:
                            shutil.copyfileobj(s, d, 1 << 20)
                        (out / "render_source.json").write_text(
                            json.dumps({"member": render, "camera": RENDER_CAM, "frame": RENDER_FRAME}), encoding="utf-8")
                    print(f"#{n}: texture={Path(tex).name} obj={Path(obj).name if obj else None} render={bool(render)}")
            inner_path.unlink()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=None, help="đường dẫn zip ngoài (mặc định: file LR3D*.zip trong data/)")
    ap.add_argument("--dest", default="data/lr3d_src")
    ap.add_argument("--ids", type=int, nargs="*", default=SELECTED)
    a = ap.parse_args()
    outer = Path(a.src) if a.src else next(Path("data").glob("LR3D*.zip"))
    extract(outer, Path(a.dest), a.ids)
    print("xong")
