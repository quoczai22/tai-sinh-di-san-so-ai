"""Nén mô hình 3D của hiện vật thành file GLB nhẹ để trang Studio cho xoay 360 độ bằng chuột.

Nguồn: data/raw/lr3d_src/ceramic_vases_<số>/ (OBJ + ảnh vân, bộ LR3D-CULT2, CC BY 4.0), nặng tới hàng trăm MB.
Mỗi hiện vật:
  1. Đọc OBJ cùng ảnh vân (file .mtl ghi sai tên ảnh nên script tự tìm ảnh vân trong thư mục).
  2. Giảm số mặt về gần MAX_FACES bằng PyMeshLab (quadric edge collapse có tính toạ độ ảnh vân,
     nên hoa văn không bị lệch). Mô hình đã nhẹ thì giữ nguyên.
  3. Thu ảnh vân về tối đa TEX_SIZE px, lưu JPEG.
  4. Đưa chân bình về y = 0, tâm về gốc, chuẩn hoá chiều cao = 1, xuất GLB.

    uv run python scripts/web/export_heritage_glb.py            # 6 hiện vật đang dùng
    uv run python scripts/web/export_heritage_glb.py LR3D_61    # chọn hiện vật

Ra: web_ui/assets/models/<mã hiện vật>.glb
Thư viện chỉ dùng cho script này: trimesh, pymeshlab (cài bằng uv pip install, ghi trong requirements.txt).
"""
import io
import re
import sys
import tempfile
from pathlib import Path

import numpy as np
import pymeshlab
import trimesh
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
SRC = ROOT / "data" / "raw" / "lr3d_src"
OUT = ROOT / "web_ui" / "assets" / "models"
MAX_FACES = 30000      # số mặt mong muốn sau khi giảm (có thể còn nhiều hơn, xem decimate)
TEX_SIZE = 2048        # cạnh dài tối đa của ảnh vân (px)
TEX_QUALITY = 88       # chất lượng JPEG


def find_texture(folder: Path) -> Path:
    """Ảnh vân: ảnh lớn nhất trong thư mục, bỏ ảnh render.png (ảnh chụp xem trước)."""
    imgs = [p for p in folder.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg") and p.stem != "render"]
    if not imgs:
        raise FileNotFoundError(f"không có ảnh vân trong {folder}")
    return max(imgs, key=lambda p: p.stat().st_size)


def decimate(obj: Path, texture: Path, max_faces: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Đọc OBJ, giảm số mặt nếu vượt max_faces. Trả về (đỉnh, mặt, uv theo đỉnh) sau khi gộp đỉnh trùng toạ độ và uv."""
    with tempfile.TemporaryDirectory() as tmp:
        # PyMeshLab cần mtl trỏ đúng ảnh vân: viết lại mtl tạm cạnh OBJ đã sao chép
        tmp = Path(tmp)
        mtl = tmp / "m.mtl"
        mtl.write_text(f"newmtl m\nKd 1 1 1\nmap_Kd {texture.name}\n", encoding="utf-8")
        ms = pymeshlab.MeshSet()
        obj_tmp = tmp / "m.obj"
        # Ghi lại OBJ với dòng mtllib/usemtl mới. Đọc theo dòng để không nạp cả file 200 MB vào bộ nhớ một lần.
        with obj.open("r", encoding="utf-8", errors="ignore") as fi, obj_tmp.open("w", encoding="utf-8") as fo:
            fo.write("mtllib m.mtl\nusemtl m\n")
            for line in fi:
                if not line.startswith(("mtllib", "usemtl", "o ", "g ", "s ")):
                    fo.write(line)
        Image.new("RGB", (1, 1)).save(tmp / texture.name, "PNG")        # ảnh giả 1 px: PyMeshLab chỉ cần thấy file tồn tại, toạ độ uv không đổi
        ms.load_new_mesh(str(obj_tmp))
        # Chỉ giảm mặt khi giữ nguyên biên các mảng ảnh vân (preserveboundary). Cho phép gộp cả cạnh biên
        # thì mô hình nhiều mảnh nhỏ bị vỡ thành các tam giác lớn sai ảnh vân (đã gặp ở LR3D_33), nên không dùng.
        # Hệ quả: mô hình nhiều mảnh có thể còn nhiều hơn max_faces sau khi giảm (LR3D_38 còn khoảng 208 nghìn mặt).
        if ms.current_mesh().face_number() > max_faces:
            ms.meshing_decimation_quadric_edge_collapse_with_texture(
                targetfacenum=max_faces, qualitythr=0.5, extratcoordw=1.0, preserveboundary=True, optimalplacement=True)
        m = ms.current_mesh()
        v, f = m.vertex_matrix(), m.face_matrix()
        wedge = m.wedge_tex_coord_matrix().reshape(-1, 2)               # uv theo từng góc mặt (3 góc mỗi mặt)
    # Chuyển uv theo góc mặt thành uv theo đỉnh: mỗi góc mặt thành một đỉnh riêng rồi gộp các đỉnh giống nhau
    verts = v[f.reshape(-1)]
    key = np.hstack([np.round(verts, 6), np.round(wedge, 6)])
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    return verts[first], inv.reshape(-1, 3), wedge[first]


def export(hid: str, max_faces: int = MAX_FACES) -> Path:
    num = re.search(r"(\d+)$", hid).group(1)
    folder = SRC / f"ceramic_vases_{num}"
    obj = next(folder.glob("*.obj"))
    texture = find_texture(folder)
    verts, faces, uv = decimate(obj, texture, max_faces)

    # Chân bình về y = 0, tâm ngang về gốc, cao đúng 1 đơn vị
    verts = verts - np.array([(verts[:, 0].min() + verts[:, 0].max()) / 2, verts[:, 1].min(),
                              (verts[:, 2].min() + verts[:, 2].max()) / 2])
    verts = verts / verts[:, 1].max()

    img = Image.open(texture).convert("RGB")
    img.thumbnail((TEX_SIZE, TEX_SIZE), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=TEX_QUALITY, optimize=True)
    img = Image.open(io.BytesIO(buf.getvalue()))

    material = trimesh.visual.material.PBRMaterial(baseColorTexture=img, metallicFactor=0.0, roughnessFactor=0.35)
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False,
                           visual=trimesh.visual.TextureVisuals(uv=uv, material=material))
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{hid}.glb"
    path.write_bytes(trimesh.exchange.gltf.export_glb(trimesh.Scene(mesh)))
    print(f"{hid}: {len(faces)} mặt, ảnh vân {img.size}, {path.stat().st_size / 1e6:.1f} MB")
    return path


def main(argv: list[str]) -> int:
    from provenance.registry import all_items                          # noqa: PLC0415
    ids = argv or [it["heritage_id"] for it in all_items(ROOT) if it.get("status", "active") == "active"]
    for hid in ids:
        export(hid)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
