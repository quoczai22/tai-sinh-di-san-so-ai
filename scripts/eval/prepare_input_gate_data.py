# -*- coding: utf-8 -*-
"""Gom tập thử có nhãn cho cổng kiểm tra ảnh đầu vào (docs/CONG_ANH_DAU_VAO.md).

Bốn nhóm, ảnh nằm ở data/eval/input_filter/images/<nhóm>/ (không commit), nhãn ở data/eval/input_filter/labels.csv:
  A  ảnh hợp lệ đã biết: 6 ảnh hiện vật trong data/heritage/ và 24 phần tử cắt trong data/elements/ (3 mỗi bình)
  B  ảnh hợp lệ chưa từng thấy: ảnh render của 20 bình chưa dùng, lấy từ bộ LR3D-CULT2 trong data/raw/
  C  bản biến dạng của A (đổi sáng, nén JPEG, xoay, cắt lệch, đổi nền, thu nhỏ)
  D  ảnh lạc đề vô hại do nhóm tự thu thập, bỏ vào images/D/ (script không tự chép ảnh nào vào nhóm này)

Chạy: uv run python scripts/eval/prepare_input_gate_data.py --step all   (hoặc từng bước a, b, c, d, labels)
Mọi lựa chọn ngẫu nhiên dùng seed cố định nên chạy lại ra đúng tập cũ (bước B không giải nén lại ảnh đã có; bước a, c, d ghi đè bằng đúng nội dung cũ).
Thêm hay bớt ảnh trong images/D/ thì phải chạy lại --step labels để labels.csv khớp.
Ảnh D do nhóm thêm: bỏ vào images/D/ và (nếu muốn ghi nguồn) tạo images/D/sources.csv gồm cột file,source,license,category.
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import io
import json
import random
import re
import shutil
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageEnhance

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))       # chạy từ thư mục gốc repo vẫn import được tsds
from tsds.core.paths import ROOT

EVAL = ROOT / "data" / "eval" / "input_filter"
IMG = EVAL / "images"
SEED = 42
USED_VASES = {15, 33, 37, 38, 50, 61, 97, 124}      # 8 bình đã dùng cho kho phần tử, không đưa vào nhóm B
N_ELEMENTS_PER_VASE = 3
N_B = 20
N_C_EXTRA = 10                                       # thêm bản biến dạng thứ hai cho một số ảnh A, để C đủ 40
LICENSE_LR3D = "CC BY 4.0 (LR3D-CULT2, chưa xác minh riêng từng vật)"
COLUMNS = ["file", "group", "label_expected", "object_id", "parent_file", "source", "license", "split", "note"]


def _save_meta(group: str, rows: list[dict]) -> None:
    EVAL.mkdir(parents=True, exist_ok=True)
    (EVAL / f"meta_{group}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


def _load_meta(group: str) -> list[dict]:
    p = EVAL / f"meta_{group}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


# ------------------------------------------------------------------ nhóm A --
def step_a() -> None:
    out = IMG / "A"
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    rows = []
    crops = json.loads((ROOT / "data" / "heritage" / "lr3d_crops.json").read_text(encoding="utf-8"))
    for hid, info in sorted(crops.items()):
        src = ROOT / "data" / "heritage" / f"{hid}.png"
        if not src.is_file():
            continue
        name = f"A/H_{hid}.png"
        Image.open(src).save(IMG / name)
        rows.append({"file": name, "object_id": info["object_id"], "source": f"data/heritage/{hid}.png",
                     "license": LICENSE_LR3D, "note": "ảnh hiện vật"})
    index = json.loads((ROOT / "data" / "elements" / "index.json").read_text(encoding="utf-8"))
    by_obj: dict[str, list[dict]] = {}
    for r in index:
        if (ROOT / r["file"]).is_file():
            by_obj.setdefault(r["object_id"], []).append(r)
    for obj in sorted(by_obj):
        for r in rng.sample(sorted(by_obj[obj], key=lambda x: x["element_id"]), N_ELEMENTS_PER_VASE):
            name = f"A/E_{r['element_id']}.png"
            shutil.copyfile(ROOT / r["file"], IMG / name)
            rows.append({"file": name, "object_id": obj, "source": r["file"], "license": LICENSE_LR3D,
                         "note": "phần tử cắt, nền trong suốt"})
    _save_meta("A", rows)
    print(f"A: {len(rows)} ảnh")


# ------------------------------------------------------------------ nhóm B --
def _outer_zip() -> zipfile.ZipFile:
    return zipfile.ZipFile(glob.glob(str(ROOT / "data" / "raw" / "LR3D-CULT2*"))[0])


def step_b() -> None:
    out = IMG / "B"
    out.mkdir(parents=True, exist_ok=True)
    cache = EVAL / "b_candidates.json"
    outer = _outer_zip()
    members = [i for i in outer.infolist() if "ceramic_vases_" in i.filename]
    if cache.exists():
        cand = json.loads(cache.read_text(encoding="utf-8"))
    else:
        cand = {}                                    # số bình -> tên gói con chứa nó
        for info in members:
            with outer.open(info) as f:
                for n in zipfile.ZipFile(f).namelist():
                    m = re.search(r"ceramic_vases_(\d+)/", n)
                    if m:
                        cand[m.group(1)] = info.filename
        cache.write_text(json.dumps(cand, indent=1), encoding="utf-8")
    free = sorted((int(k) for k in cand if int(k) not in USED_VASES))
    chosen = sorted(random.Random(SEED).sample(free, N_B))
    print(f"B: {len(free)} bình chưa dùng, chọn {len(chosen)}: {chosen}")
    rows = []
    for info in members:
        mine = [v for v in chosen if cand[str(v)] == info.filename]
        if not mine:
            continue
        with outer.open(info) as f:
            inner = zipfile.ZipFile(f)
            names = inner.namelist()
            picks = []
            for v in mine:
                pat = re.compile(rf"(^|/)ceramic_vases_{v}/images/[^/]*CAM1_1\.0001\.png$")
                hit = next((n for n in names if pat.search(n)), None)
                note = "render camera 1, khung 1"
                if hit is None:                      # thiếu góc chuẩn thì lấy ảnh render đầu tiên
                    hit = next(n for n in sorted(names) if f"ceramic_vases_{v}/images/" in n and n.endswith(".png"))
                    note = "render đầu tiên (không có camera 1, khung 1)"
                picks.append((inner.getinfo(hit).header_offset, v, hit, note))
            for _, v, hit, note in sorted(picks):    # đọc theo thứ tự vị trí để không phải tua lại gói nén
                name = f"B/ceramic_vases_{v}.png"
                if not (IMG / name).exists():
                    (IMG / name).write_bytes(inner.read(hit))
                rows.append({"file": name, "object_id": f"ceramic_vases_{v}", "source": f"{info.filename.rsplit('/', 1)[-1]}:{hit}",
                             "license": LICENSE_LR3D, "note": note})
    _save_meta("B", sorted(rows, key=lambda r: r["file"]))
    print(f"B: {len(rows)} ảnh")


# ------------------------------------------------------------------ nhóm C --
def _flatten(img: Image.Image, color=(255, 255, 255)) -> Image.Image:
    """RGBA đặt lên một màu nền; ảnh RGB giữ nguyên."""
    if img.mode != "RGBA":
        return img.convert("RGB")
    bg = Image.new("RGB", img.size, color)
    bg.paste(img, mask=img.split()[3])
    return bg


def _t_sang(img, rng):
    f = rng.choice([rng.uniform(0.55, 0.8), rng.uniform(1.25, 1.5)])
    rgb = ImageEnhance.Brightness(_flatten(img)).enhance(f)
    return rgb, f"đổi sáng x{f:.2f}"


def _t_jpeg(img, rng):
    q = rng.randint(12, 30)
    buf = io.BytesIO()
    _flatten(img).save(buf, "JPEG", quality=q)
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB"), f"nén JPEG chất lượng {q}"


def _t_xoay(img, rng):
    a = rng.uniform(-12, 12)
    rgb = _flatten(img).rotate(a, expand=True, fillcolor=(255, 255, 255))
    return rgb, f"xoay {a:.1f} độ"


def _t_cat(img, rng):
    w, h = img.size
    k = rng.uniform(0.8, 0.92)
    cw, ch = int(w * k), int(h * k)
    x, y = rng.randint(0, w - cw), rng.randint(0, h - ch)
    return _flatten(img).crop((x, y, x + cw, y + ch)), f"cắt lệch giữ {k:.0%}"


def _t_nen(img, rng):
    if img.mode != "RGBA":
        return _t_sang(img, rng)
    color = rng.choice([(128, 128, 128), (0, 0, 0), (235, 225, 200)])
    return _flatten(img, color), f"đổi nền {color}"


def _t_nho(img, rng):
    rgb = _flatten(img)
    s = 160 / max(rgb.size)
    return rgb.resize((max(1, int(rgb.width * s)), max(1, int(rgb.height * s)))), "thu nhỏ về cạnh dài 160 px"


TRANSFORMS = {"sang": _t_sang, "jpeg": _t_jpeg, "xoay": _t_xoay, "cat": _t_cat, "nen": _t_nen, "nho": _t_nho}


def step_c() -> None:
    out = IMG / "C"
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED + 3)
    a_rows = _load_meta("A")
    if not a_rows:
        raise SystemExit("Chưa có nhóm A: chạy --step a trước.")
    jobs = [(r, None) for r in a_rows]                                  # mỗi ảnh A một bản
    jobs += [(r, "extra") for r in rng.sample(a_rows, N_C_EXTRA)]       # thêm bản thứ hai cho vài ảnh
    rows = []
    for i, (r, _) in enumerate(jobs):
        kind = rng.choice(sorted(TRANSFORMS))
        img, desc = TRANSFORMS[kind](Image.open(IMG / r["file"]), rng)
        name = f"C/{Path(r['file']).stem}__{kind}{i:02d}.png"
        img.save(IMG / name)
        rows.append({"file": name, "object_id": r["object_id"], "parent_file": r["file"],
                     "source": "tự tạo từ nhóm A", "license": r["license"], "note": desc})
    _save_meta("C", rows)
    print(f"C: {len(rows)} ảnh")


# ------------------------------------------------------------------ nhóm D --
def step_d() -> None:
    """Nhóm D do nhóm tự thu thập (ví dụ từ Roboflow Universe), script không tự chép ảnh nào."""
    out = IMG / "D"
    out.mkdir(parents=True, exist_ok=True)
    n = sum(p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} for p in out.iterdir())
    print(f"D: hiện có {n} ảnh trong {out}. Tự thêm ảnh lạc đề và sources.csv vào đó (cần 30 đến 40 ảnh).")


def _d_rows() -> list[dict]:
    """Mọi ảnh trong images/D/, nguồn lấy từ sources.csv nếu có."""
    meta = {}
    src_csv = IMG / "D" / "sources.csv"
    if src_csv.exists():
        with open(src_csv, encoding="utf-8", newline="") as f:
            meta = {r["file"]: r for r in csv.DictReader(f)}
    rows = []
    for p in sorted((IMG / "D").iterdir()):
        if p.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        m = meta.get(p.name, {})
        rows.append({"file": f"D/{p.name}", "object_id": "", "source": m.get("source", "nhóm tự thu thập"),
                     "license": m.get("license", "chưa ghi"), "note": m.get("category", "")})
    return rows


# ------------------------------------------------------------------ labels --
def _split_by_vase(vases: list[str]) -> dict[str, str]:
    """Chia bình thành tune và test xen kẽ theo thứ tự băm, nên ổn định và gần cân bằng."""
    order = sorted(vases, key=lambda v: hashlib.sha256(f"{SEED}:{v}".encode()).hexdigest())
    return {v: ("tune" if i % 2 == 0 else "test") for i, v in enumerate(order)}


def step_labels() -> None:
    a, b, c = _load_meta("A"), _load_meta("B"), _load_meta("C")
    d = _d_rows()
    vases_a = sorted({r["object_id"] for r in a})
    vases_b = sorted({r["object_id"] for r in b})
    split_a, split_b = _split_by_vase(vases_a), _split_by_vase(vases_b)
    out = []
    for group, rows in (("A", a), ("B", b), ("C", c), ("D", d)):
        for r in rows:
            if group in ("A", "C"):
                split = split_a[r["object_id"]]
            elif group == "B":
                split = split_b[r["object_id"]]
            else:                                    # D: chia theo băm tên tệp để thêm ảnh sau không làm đảo tệp cũ
                split = "tune" if int(hashlib.sha256(r["file"].encode()).hexdigest(), 16) % 2 == 0 else "test"
            out.append({"file": r["file"], "group": group, "label_expected": "block" if group == "D" else "pass",
                        "object_id": r.get("object_id", ""), "parent_file": r.get("parent_file", ""),
                        "source": r.get("source", ""), "license": r.get("license", ""), "split": split,
                        "note": r.get("note", "")})
    with open(EVAL / "labels.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(out)
    cnt: dict[tuple, int] = {}
    for r in out:
        cnt[(r["group"], r["split"])] = cnt.get((r["group"], r["split"]), 0) + 1
    print("labels.csv:", len(out), "ảnh;", {f"{g}/{s}": n for (g, s), n in sorted(cnt.items())})


STEPS = {"a": step_a, "b": step_b, "c": step_c, "d": step_d, "labels": step_labels}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--step", default="all", choices=["all", *STEPS])
    ap.add_argument("--skip-b", action="store_true", help="bỏ qua bước B (chậm vì đọc gói nén 8 GB)")
    args = ap.parse_args()
    for name in (STEPS if args.step == "all" else [args.step]):
        if name == "b" and args.skip_b:
            continue
        STEPS[name]()


if __name__ == "__main__":
    main()
