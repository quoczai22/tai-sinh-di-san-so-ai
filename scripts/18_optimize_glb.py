# -*- coding: utf-8 -*-
"""Nén mô hình 3D bình gốm (web_ui/assets/models/*.glb) cho web, không cần thư viện ngoài.

Chỉ dùng numpy + Pillow (không cần trimesh/pymeshlab, không cần dữ liệu nguồn LR3D):
  1. Ảnh vân: thu về tối đa TEX_SIZE px, lưu JPEG chất lượng JPEG_QUALITY.
  2. Lượng tử hoá đỉnh theo KHR_mesh_quantization (GLTFLoader của three.js đọc sẵn, không cần bộ giải mã):
       POSITION   float32 vec3 -> int16 normalized; node con mang translation/scale để toạ độ hiển thị giữ nguyên.
       TEXCOORD_n float32 vec2 -> uint16 normalized (khi UV nằm trong [0, 1]; ngoài khoảng thì giữ float).
  3. Chỉ số: uint16 khi số đỉnh < 65 536.
  Không giảm số tam giác (cần pymeshlab).
Sau khi ghi, đọc lại và so với bản gốc (sai số vị trí so với chiều cao bình, sai số UV, chỉ số).

Chạy:
    python scripts/18_optimize_glb.py                 # mọi file trong web_ui/assets/models/
    python scripts/18_optimize_glb.py LR3D_61         # chọn hiện vật
Chạy lại trên file đã nén thì bỏ qua (đã có KHR_mesh_quantization).
"""
from __future__ import annotations

import io
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "web_ui" / "assets" / "models"
TEX_SIZE = 1024
JPEG_QUALITY = 85
EXT = "KHR_mesh_quantization"

CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


# ------------------------------------------------------------------------------------- GLB I/O --
def read_glb(data: bytes) -> tuple[dict, bytes]:
    magic, version, _ = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67 or version != 2:
        raise ValueError("Không phải GLB 2.0")
    jlen, jtype = struct.unpack_from("<II", data, 12)
    if jtype != 0x4E4F534A:
        raise ValueError("Chunk đầu không phải JSON")
    gltf = json.loads(data[20:20 + jlen])
    off = 20 + jlen
    blen, btype = struct.unpack_from("<II", data, off)
    if btype != 0x004E4942:
        raise ValueError("Chunk thứ hai không phải BIN")
    return gltf, data[off + 8: off + 8 + blen]


def write_glb(gltf: dict, binary: bytes) -> bytes:
    j = json.dumps(gltf, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    j += b" " * (-len(j) % 4)
    binary += b"\0" * (-len(binary) % 4)
    total = 12 + 8 + len(j) + 8 + len(binary)
    return (struct.pack("<III", 0x46546C67, 2, total)
            + struct.pack("<II", len(j), 0x4E4F534A) + j
            + struct.pack("<II", len(binary), 0x004E4942) + binary)


def read_accessor(gltf: dict, binary: bytes, idx: int) -> np.ndarray:
    acc = gltf["accessors"][idx]
    bv = gltf["bufferViews"][acc["bufferView"]]
    dtype = np.dtype(CT[acc["componentType"]])
    n, count = NC[acc["type"]], acc["count"]
    start = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = bv.get("byteStride") or dtype.itemsize * n
    raw = np.frombuffer(binary, dtype=np.uint8, count=stride * (count - 1) + dtype.itemsize * n, offset=start)
    rows = np.lib.stride_tricks.as_strided(raw, shape=(count, dtype.itemsize * n), strides=(stride, 1))
    out = np.ascontiguousarray(rows).view(dtype).reshape(count, n)
    if acc.get("normalized"):
        info = np.iinfo(dtype)
        out = np.maximum(out.astype(np.float64) / info.max, -1.0) if info.min < 0 else out.astype(np.float64) / info.max
    return out


def image_bytes(gltf: dict, binary: bytes, img: dict) -> bytes:
    bv = gltf["bufferViews"][img["bufferView"]]
    o = bv.get("byteOffset", 0)
    return binary[o:o + bv["byteLength"]]


# ---------------------------------------------------------------------------------- Builder --
class Builder:
    def __init__(self) -> None:
        self.buf = bytearray()
        self.views: list[dict] = []

    def add(self, payload: bytes, target: int | None = None, stride: int | None = None) -> int:
        self.buf += b"\0" * (-len(self.buf) % 4)
        view = {"buffer": 0, "byteOffset": len(self.buf), "byteLength": len(payload)}
        if target:
            view["target"] = target
        if stride:
            view["byteStride"] = stride
        self.buf += payload
        self.views.append(view)
        return len(self.views) - 1


def node_trs_matrix(node: dict) -> np.ndarray:
    if "matrix" in node:
        return np.array(node["matrix"], dtype=np.float64).reshape(4, 4).T
    t = np.array(node.get("translation", [0, 0, 0]), dtype=np.float64)
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    s = np.array(node.get("scale", [1, 1, 1]), dtype=np.float64)
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    m = np.eye(4)
    m[:3, :3] = r * s
    m[:3, 3] = t
    return m


def optimize(src: bytes) -> tuple[bytes, dict]:
    gltf, binary = read_glb(src)
    if EXT in gltf.get("extensionsUsed", []):
        raise RuntimeError("đã nén trước đó")
    b = Builder()
    new_acc: list[dict | None] = [None] * len(gltf["accessors"])
    mesh_dequant: dict[int, tuple[list, list]] = {}

    # Vai trò của từng accessor theo cách các primitive dùng nó
    roles: dict[int, str] = {}
    for m in gltf["meshes"]:
        for p in m["primitives"]:
            for name, a in p["attributes"].items():
                roles[a] = name
            if "indices" in p:
                roles[p["indices"]] = "INDICES"

    # POSITION: một cặp (tâm, nửa kích thước) chung cho cả mesh để node con giải lượng tử được
    for mi, m in enumerate(gltf["meshes"]):
        pos = np.concatenate([read_accessor(gltf, binary, p["attributes"]["POSITION"]) for p in m["primitives"]])
        lo, hi = pos.min(0), pos.max(0)
        center = (lo + hi) / 2
        half = np.maximum((hi - lo) / 2, 1e-9)
        mesh_dequant[mi] = (center.tolist(), half.tolist())
        for p in m["primitives"]:
            a = p["attributes"]["POSITION"]
            if new_acc[a] is not None:
                continue
            v = read_accessor(gltf, binary, a)
            q = np.clip(np.round((v - center) / half * 32767), -32767, 32767).astype(np.int16)
            padded = np.zeros((len(q), 4), dtype=np.int16)          # vec3 short + 2 byte đệm: stride 8 (bội số 4)
            padded[:, :3] = q
            view = b.add(padded.tobytes(), target=34962, stride=8)
            new_acc[a] = {"bufferView": view, "componentType": 5122, "normalized": True, "count": len(q),
                          "type": "VEC3", "min": q.min(0).tolist(), "max": q.max(0).tolist()}

    for a, acc in enumerate(gltf["accessors"]):
        if new_acc[a] is not None:
            continue
        role = roles.get(a, "")
        v = read_accessor(gltf, binary, a)
        if role.startswith("TEXCOORD_") and v.min() >= 0.0 and v.max() <= 1.0:
            q = np.round(v * 65535).astype(np.uint16)
            view = b.add(q.tobytes(), target=34962)
            new_acc[a] = {"bufferView": view, "componentType": 5123, "normalized": True, "count": len(q), "type": "VEC2"}
        elif role == "INDICES":
            idx = v.reshape(-1).astype(np.int64)
            small = idx.max() < 65536
            data = idx.astype(np.uint16 if small else np.uint32)
            view = b.add(data.tobytes(), target=34963)
            new_acc[a] = {"bufferView": view, "componentType": 5123 if small else 5125, "count": len(data), "type": "SCALAR"}
        else:                                                       # thuộc tính khác: giữ float, chép lại
            arr = v.astype(np.float32)
            view = b.add(arr.tobytes(), target=34962 if role else None)
            new_acc[a] = {"bufferView": view, "componentType": 5126, "count": len(arr), "type": acc["type"]}
            for k in ("min", "max"):
                if k in acc:
                    new_acc[a][k] = acc[k]

    # Ảnh vân: thu nhỏ + JPEG
    tex_info = []
    for img in gltf.get("images", []):
        im = Image.open(io.BytesIO(image_bytes(gltf, binary, img)))
        before = im.size
        im = im.convert("RGB")
        if max(im.size) > TEX_SIZE:
            k = TEX_SIZE / max(im.size)
            im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        out = io.BytesIO()
        im.save(out, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=False)
        img["bufferView"] = b.add(out.getvalue())
        img["mimeType"] = "image/jpeg"
        tex_info.append(f"{before[0]}x{before[1]} -> {im.width}x{im.height}")

    # Node chứa mesh: chuyển mesh sang node con mang translation/scale giải lượng tử
    for node in list(gltf["nodes"]):
        if "mesh" not in node:
            continue
        center, half = mesh_dequant[node["mesh"]]
        child = {"mesh": node.pop("mesh"), "translation": center, "scale": half}
        gltf["nodes"].append(child)
        node.setdefault("children", []).append(len(gltf["nodes"]) - 1)

    gltf["accessors"] = new_acc
    gltf["bufferViews"] = b.views
    gltf["buffers"] = [{"byteLength": len(b.buf)}]
    for key in ("extensionsUsed", "extensionsRequired"):
        gltf[key] = sorted(set(gltf.get(key, [])) | {EXT})
    return write_glb(gltf, bytes(b.buf)), {"textures": tex_info}


# ------------------------------------------------------------------------------------ Verify --
def world_positions(gltf: dict, binary: bytes) -> list[np.ndarray]:
    """Toạ độ đỉnh sau khi áp transform của các node (để so bản gốc và bản nén)."""
    parents = {c: i for i, n in enumerate(gltf["nodes"]) for c in n.get("children", [])}

    def world(i: int) -> np.ndarray:
        m = node_trs_matrix(gltf["nodes"][i])
        return world(parents[i]) @ m if i in parents else m

    out = []
    for i, n in enumerate(gltf["nodes"]):
        if "mesh" not in n:
            continue
        w = world(i)
        for p in gltf["meshes"][n["mesh"]]["primitives"]:
            v = read_accessor(gltf, binary, p["attributes"]["POSITION"]).astype(np.float64)
            out.append((np.c_[v, np.ones(len(v))] @ w.T)[:, :3])
    return out


def verify(src: bytes, dst: bytes) -> dict:
    g0, b0 = read_glb(src)
    g1, b1 = read_glb(dst)
    p0, p1 = world_positions(g0, b0), world_positions(g1, b1)
    height = max(float(p[:, 1].max() - p[:, 1].min()) for p in p0)
    pos_err = max(float(np.abs(a - c).max()) for a, c in zip(p0, p1)) / height
    uv_err, idx_same, tris = 0.0, True, 0
    for m0, m1 in zip(g0["meshes"], g1["meshes"]):
        for q0, q1 in zip(m0["primitives"], m1["primitives"]):
            for name, a in q0["attributes"].items():
                if name.startswith("TEXCOORD_"):
                    uv_err = max(uv_err, float(np.abs(read_accessor(g0, b0, a) - read_accessor(g1, b1, q1["attributes"][name])).max()))
            i0 = read_accessor(g0, b0, q0["indices"]).reshape(-1)
            i1 = read_accessor(g1, b1, q1["indices"]).reshape(-1)
            idx_same &= np.array_equal(i0.astype(np.int64), i1.astype(np.int64))
            tris += len(i1) // 3
    imgs = [Image.open(io.BytesIO(image_bytes(g1, b1, im))) for im in g1.get("images", [])]
    return {"pos_err_rel": pos_err, "uv_err": uv_err, "indices_equal": bool(idx_same), "tris": tris,
            "images": [f"{im.format} {im.width}x{im.height}" for im in imgs]}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    names = sys.argv[1:]
    files = [MODELS / f"{n}.glb" for n in names] if names else sorted(MODELS.glob("*.glb"))
    ok, total0, total1 = True, 0, 0
    print(f"{'File':14} {'Trước':>9} {'Sau':>9} {'Giảm':>6}  sai số vị trí  sai số UV  chỉ số  tam giác  ảnh")
    for f in files:
        src = f.read_bytes()
        try:
            dst, info = optimize(src)
        except RuntimeError as e:
            print(f"{f.name:14} bỏ qua: {e}")
            continue
        r = verify(src, dst)
        good = r["pos_err_rel"] < 5e-4 and r["uv_err"] < 1 / 4096 and r["indices_equal"]
        ok &= good
        total0 += len(src)
        total1 += len(dst)
        print(f"{f.name:14} {len(src)/1e6:8.2f}M {len(dst)/1e6:8.2f}M {100*(1-len(dst)/len(src)):5.1f}%  "
              f"{r['pos_err_rel']:.6f}       {r['uv_err']:.6f}   {'giống' if r['indices_equal'] else 'KHÁC'}   "
              f"{r['tris']:>7}  {', '.join(info['textures'])}  {'OK' if good else 'LỖI'}")
        if good:
            f.write_bytes(dst)
    if total0:
        print(f"{'Tổng':14} {total0/1e6:8.2f}M {total1/1e6:8.2f}M {100*(1-total1/total0):5.1f}%")
    print("Tự kiểm:", "ĐẠT" if ok else "CÓ LỖI (file lỗi không bị ghi đè)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
