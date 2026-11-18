# -*- coding: utf-8 -*-
"""Tiếp nhận ảnh hiện vật mới vào danh mục (luồng L-2 trong docs/finals/02_APQC.md).

Dùng cho ảnh CC0 của bảo tàng tra ở data/heritage/sources/commons_candidates_*.json.
Mỗi bước để lại dấu vết kiểm tra được:

  1. Kiểm SHA-1 tệp tải về khớp mã Commons công bố (sai là dừng).
  2. Lưu bản gốc vào data/heritage/sources/originals/ (không commit, xem .gitignore).
  3. Tách nền bằng GrabCut khởi tạo bằng mặt nạ (grabcut_mask_v2; khung cách mép
     --margin, hoặc --rect tự chọn — ngoài --rect chắc chắn là nền), giữ phần nối với
     tâm khung, cắt sát, thu về cạnh dài ≤ 1600 px, lưu PNG RGBA.
  4. Ghi lại mọi phép biến đổi + băm bản gốc và bản dẫn xuất (derived_from).
  5. Chạy tiêu chí C1–C4; ảnh xem trước để người kiểm tra mặt nạ tách nền.
  6. Ghi mục danh mục ở trạng thái `pending_ingest` — CHƯA dùng cho sản phẩm cho
     tới khi người rà soát mặt nạ, viết prompt và chạy lại với --activate.

Ví dụ:
  python scripts/09_ingest_heritage_image.py --file TSDS_DSC05640.jpg --candidate DSC05640 \\
      --heritage-id BT_Chum_GiaLong --name "Chum vẽ sơn thuỷ và linh vật" --dry-run
  python scripts/09_ingest_heritage_image.py ... --name-en "Bat Trang landscape jar" \\
      --description-en "Cobalt blue landscape with mountains, pavilions and mythical animals."
  python scripts/09_ingest_heritage_image.py --heritage-id BT_Chum_GiaLong --activate
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

META = ROOT / "data" / "heritage" / "metadata.json"
TERMS = ROOT / "data" / "prompt_terms.json"
SOURCES = ROOT / "data" / "heritage" / "sources"
ORIGINALS = SOURCES / "originals"
PREVIEW = ROOT / "docs" / "evidence" / "ingest"
MAX_SIDE = 1600


def sha(path: Path, algo: str) -> str:
    h = hashlib.new(algo)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def find_candidate(cid: str, candidates: Path | None) -> tuple[dict, Path]:
    files = [candidates] if candidates else sorted(SOURCES.glob("commons_candidates_*.json"))
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        for c in data["candidates"]:
            if c["id"] == cid:
                return c, f
    raise SystemExit(f"Không có ứng viên {cid} trong {', '.join(str(f) for f in files)}")


def _border_band(h: int, w: int) -> np.ndarray:
    band = max(6, round(0.02 * max(h, w)))
    edge = np.zeros((h, w), bool)
    edge[:band], edge[-band:], edge[:, :band], edge[:, -band:] = True, True, True, True
    return edge


def background_like(rgb: np.ndarray) -> tuple[np.ndarray, dict]:
    """Gợi ý nền (CHỈ là gợi ý cho GrabCut, không trừ thẳng khỏi mặt nạ).

    Pixel "giống nền" khi bề mặt mịn VÀ (a) gần mặt bậc hai khớp bền vững trên dải viền
    (nền loang màu do đèn chiếu) hoặc (b) gần một cụm màu chiếm ≥ 5% dải viền (tường, kệ
    khác màu nhau). Làm trong CIELAB. Điều kiện "mịn" giữ lại men rạn và nét vẽ: men trắng
    ngà có thể cùng màu tường nhưng có kết cấu, tường thì không.
    """
    h, w = rgb.shape[:2]
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    edge = _border_band(h, w)
    L = lab[..., 0]
    mu = cv2.blur(L, (7, 7))
    tex = np.sqrt(np.maximum(cv2.blur(L * L, (7, 7)) - mu * mu, 0))
    yy, xx = np.mgrid[0:h, 0:w]
    x, y = xx / w, yy / h
    A = np.stack([np.ones_like(x), x, y, x * x, y * y, x * y], -1)
    # Khớp bền vững: bỏ dần 40% điểm viền lệch nhất (vật chạm mép, nhãn, kệ)
    use, pred = edge.copy(), np.zeros_like(lab)
    for _ in range(3):
        for c in range(3):
            coef, *_ = np.linalg.lstsq(A[use], lab[..., c][use], rcond=None)
            pred[..., c] = A @ coef
        d = np.sqrt(((lab - pred) ** 2).sum(-1))
        use = edge & (d <= max(float(np.percentile(d[edge], 60)), 1e-3))
    d = np.sqrt(((lab - pred) ** 2).sum(-1))
    sd = float(np.median(d[use])) * 1.4826 + 1e-3
    tol = max(6.0, 4.0 * sd)
    smooth = tex < float(np.percentile(tex[edge], 90)) + 1.0
    k = 6
    cv2.setRNGSeed(0)
    _, lbl, cen = cv2.kmeans(lab[edge].reshape(-1, 3), k, None,
                             (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5), 3, cv2.KMEANS_PP_CENTERS)
    share = np.bincount(lbl.ravel(), minlength=k) / len(lbl)
    cen = cen[share >= 0.05]
    dc = np.min(np.linalg.norm(lab[..., None, :] - cen[None, None], axis=-1), axis=-1)
    bglike = (((d < tol) | (dc < tol)) & smooth).astype(np.uint8)
    # Chỉ giữ vùng giống nền NỐI LIỀN với dải viền: mảng men trơn bên trong vành đĩa/thân
    # bình có thể cùng màu tường (DSC05637) nhưng bị vành hoặc nét vẽ ngăn cách khỏi nền.
    n, labels = cv2.connectedComponents(bglike, connectivity=4)
    touching = np.unique(labels[edge & (bglike > 0)])
    bglike = np.isin(labels, touching[touching > 0]).astype(np.uint8)
    return bglike, {"type": "robust_quadratic_lab+border_kmeans", "tolerance_lab": round(tol, 1),
                                     "border_residual_sd": round(sd, 2), "border_clusters": int(len(cen)),
                                     "hint_pct": round(float(bglike.mean() * 100), 1)}


def _keep_seeded(fg: np.ndarray, seed: np.ndarray) -> np.ndarray:
    """Giữ các thành phần liên thông chạm hạt giống trung tâm (dự phòng: thành phần lớn nhất)."""
    n, labels, stats, _ = cv2.connectedComponentsWithStats(fg, 8)
    keep = set(np.unique(labels[(seed > 0) & (fg > 0)]).tolist()) - {0}
    if not keep and n > 1:
        keep = {1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))}
    return np.isin(labels, list(keep)).astype(np.uint8)


def segment(img: Image.Image, margin: float, rect: tuple[int, int, int, int] | None) -> tuple[np.ndarray, dict]:
    """Mặt nạ hiện vật bằng GrabCut khởi tạo bằng mặt nạ (v2), phóng lại kích thước gốc.

    v1 (grabcut_rect_v1) khởi tạo bằng khung rồi TRỪ thẳng vùng "giống nền": với hiện vật
    men trắng ngà đặt trước tường be, nửa trên bị trừ mất và chỉ giữ thành phần lớn nhất
    (xem DSC05640). v2: gợi ý nền chỉ đặt nhãn "có thể là nền" để GrabCut tự cân nhắc;
    dải viền giống nền là nền chắc chắn; hình elip giữa khung là hiện vật chắc chắn;
    cắt cầu nối mảnh (gờ kệ, nhãn) rồi giữ phần nối với tâm.
    """
    rgb = np.asarray(img.convert("RGB"))
    h, w = rgb.shape[:2]
    scale = min(1.0, 900 / max(h, w))
    small = cv2.resize(rgb, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    sh, sw = small.shape[:2]
    if rect:
        x0, y0, x1, y1 = (round(v * scale) for v in rect)
    else:
        x0, y0, x1, y1 = round(sw * margin), round(sh * margin), round(sw * (1 - margin)), round(sh * (1 - margin))
    bglike, bg_fit = background_like(small)
    bg_fit["connected_to_border"] = True
    mask = np.full((sh, sw), cv2.GC_PR_FGD, np.uint8)
    mask[bglike > 0] = cv2.GC_PR_BGD
    outside = np.ones((sh, sw), bool)
    outside[y0:y1, x0:x1] = False
    mask[outside] = cv2.GC_BGD if rect else cv2.GC_PR_BGD   # --rect do người chọn: ngoài khung chắc chắn là nền
    mask[_border_band(sh, sw) & (bglike > 0)] = cv2.GC_BGD
    seed = np.zeros((sh, sw), np.uint8)
    cv2.ellipse(seed, ((x0 + x1) // 2, (y0 + y1) // 2), (max(2, (x1 - x0) // 8), max(2, (y1 - y0) // 8)),
                0, 0, 360, 1, -1)
    mask[seed > 0] = cv2.GC_FGD
    # GrabCut khởi tạo GMM bằng k-means ngẫu nhiên: cùng ảnh có thể lệch vài % diện tích
    # (DSC05637: 63–69,5%). Cố định seed để tái lập và biểu quyết đa số 3 lần chạy để ổn định.
    iters, rng_seeds = 8, (0, 1, 2)
    bgr = cv2.cvtColor(small, cv2.COLOR_RGB2BGR)
    votes = np.zeros((sh, sw), np.uint8)
    for s in rng_seeds:
        cv2.setRNGSeed(s)
        m = mask.copy()
        bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
        cv2.grabCut(bgr, m, None, bgd, fgd, iters, cv2.GC_INIT_WITH_MASK)
        votes += np.isin(m, (cv2.GC_FGD, cv2.GC_PR_FGD)).astype(np.uint8)
    fg = (votes * 2 > len(rng_seeds)).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    # Cắt cầu nối mảnh hơn ~2,5% cạnh dài (gờ kệ, dây treo, nhãn dính sát) rồi khôi phục biên
    kb = max(5, round(0.025 * max(sh, sw)) | 1)
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kb, kb))
    core = _keep_seeded(cv2.morphologyEx(fg, cv2.MORPH_OPEN, ker), seed)
    fg = _keep_seeded(fg & cv2.dilate(core, ker), seed)
    # Lấp lỗ bên trong (họa tiết trắng trên thân bình hay bị GrabCut coi là nền)
    flood = np.pad(fg, 1)
    cv2.floodFill(flood, None, (0, 0), 1)
    fg = fg | (1 - flood[1:-1, 1:-1])
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    full = cv2.resize(fg * 255, (w, h), interpolation=cv2.INTER_LINEAR)
    full = cv2.GaussianBlur(full, (0, 0), 1.2)
    info = {"method": "grabcut_mask_v2", "init_rect": [round(v / scale) for v in (x0, y0, x1, y1)],
            "rect_source": "user" if rect else "margin", "work_scale": round(scale, 4), "iterations": iters,
            "rng_seeds": list(rng_seeds), "vote": "majority",
            "background_model": bg_fit, "center_seed": "ellipse 1/4 khung", "bridge_cut_px": kb,
            "keep": "components_touching_seed", "fill_holes": True,
            "foreground_pct": round(float((full > 127).mean() * 100), 2)}
    return full, info


def derive(img: Image.Image, alpha: np.ndarray, pad: int = 16) -> tuple[Image.Image, dict]:
    ys, xs = np.where(alpha > 127)
    if not len(xs):
        raise SystemExit("Mặt nạ rỗng — thử --rect hoặc --margin khác.")
    x0, y0 = max(int(xs.min()) - pad, 0), max(int(ys.min()) - pad, 0)
    x1, y1 = min(int(xs.max()) + pad + 1, img.width), min(int(ys.max()) + pad + 1, img.height)
    rgba = img.convert("RGB").copy()
    rgba.putalpha(Image.fromarray(alpha))
    rgba = rgba.crop((x0, y0, x1, y1))
    resized = None
    if max(rgba.size) > MAX_SIDE:
        k = MAX_SIDE / max(rgba.size)
        resized = (round(rgba.width * k), round(rgba.height * k))
        rgba = rgba.resize(resized, Image.LANCZOS)
    return rgba, {"crop_box": [x0, y0, x1, y1], "resize_to": resized, "resample": "LANCZOS" if resized else None}


def preview(original: Image.Image, alpha: np.ndarray, derived: Image.Image, out: Path) -> None:
    th = 520
    def fit(im):
        k = th / im.height
        return im.resize((max(1, round(im.width * k)), th))
    over = np.asarray(original.convert("RGB")).copy()
    edge = cv2.Canny((alpha > 127).astype(np.uint8) * 255, 50, 150)
    edge = cv2.dilate(edge, np.ones((max(3, original.width // 300),) * 2, np.uint8))
    over[edge > 0] = (220, 30, 30)
    white = Image.new("RGB", derived.size, "white")
    white.paste(derived, mask=derived.split()[3])
    tiles = [fit(original.convert("RGB")), fit(Image.fromarray(over)), fit(white)]
    sheet = Image.new("RGB", (sum(t.width for t in tiles) + 40, th + 20), "white")
    x = 10
    for t in tiles:
        sheet.paste(t, (x, 10))
        x += t.width + 10
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=88)


def next_code(items: dict) -> str:
    nums = [int(i["code"][2:]) for i in items.values() if str(i.get("code", "")).startswith("HV")]
    return f"HV{max(nums, default=0) + 1:02d}"


def ingest(args) -> int:
    from provenance.registry import assess_selection

    src = Path(args.file).expanduser()
    if not src.is_file():
        raise SystemExit(f"Không thấy tệp {src}")
    cand, cand_file = find_candidate(args.candidate, Path(args.candidates) if args.candidates else None)
    sha1 = sha(src, "sha1")
    if sha1 != cand["sha1"]:
        raise SystemExit(f"SHA-1 không khớp Commons: tệp {sha1} ≠ công bố {cand['sha1']}. Tải lại bản gốc.")
    meta = json.loads(META.read_text(encoding="utf-8"))
    hid = args.heritage_id
    if hid in meta["items"] and not args.force:
        raise SystemExit(f"{hid} đã có trong danh mục (dùng --force để làm lại).")

    with Image.open(src) as im:
        original = ImageOps.exif_transpose(im).convert("RGB")
    rect = tuple(int(v) for v in args.rect.split(",")) if args.rect else None
    alpha, seg = segment(original, args.margin, rect)
    derived, geo = derive(original, alpha)
    out_png = ROOT / "data" / "heritage" / f"{hid}.png"
    out_png.parent.mkdir(parents=True, exist_ok=True)
    derived.save(out_png)
    preview(original, alpha, derived, PREVIEW / f"{hid}.jpg")

    item = {
        "heritage_id": hid, "name": args.name, "image_path": f"data/heritage/{hid}.png",
        "license": "CC0-1.0", "license_note": "Ảnh CC0 1.0 (Wikimedia Commons); hiện vật thuộc phạm vi công cộng.",
        "conditioning_mode": "whole_object",
        "code": meta["items"].get(hid, {}).get("code") or next_code(meta["items"]),
        "status": "pending_ingest", "replaces": args.replaces,
        "visual_summary": None, "visual_summary_origin": None, "team_description": "",
        "provenance": {
            "source_title": cand["title_en"], "source_url": cand["page"], "source_type": "museum_collection_photo",
            "holder": cand["museum"], "holder_type": "museum", "author": f"{cand['author']} (Wikimedia Commons)",
            "rights_status": "public_domain", "license": "CC0 1.0 (ảnh); hiện vật thuộc phạm vi công cộng",
            "attribution": f"Ảnh: {cand['author']} / Wikimedia Commons, CC0 1.0. Hiện vật: {cand['museum']}.",
            "collected_on": date.today().isoformat(), "collected_before": None,
            "data_version": f"orig-sha256:{sha(src, 'sha256')[:12]}",
            "image_sha256": sha(out_png, "sha256"), "image_bytes": out_png.stat().st_size,
            "image_size": list(derived.size), "image_mode": "RGBA",
            "derived_from": {"file": src.name, "sha1_commons": sha1, "sha256": sha(src, "sha256"),
                             "size": list(original.size), "photo_date": cand.get("photo_date"),
                             "transforms": [{"step": "exif_transpose"}, {"step": "segment", **seg},
                                            {"step": "crop_resize", **geo}], "tool": "scripts/09_ingest_heritage_image.py"},
            "dating": args.dating, "dating_source": "Nhãn hiện vật của bảo tàng, theo trang mô tả Wikimedia Commons" if args.dating else None,
            "description_origin": None,
            "permission_request": {"status": "not_needed", "sent_on": None, "channel": None, "response": None},
            "review_flags": [
                {"field": "segmentation", "issue": f"Kiểm tra mặt nạ tách nền ở docs/evidence/ingest/{hid}.jpg", "status": "open",
                 "opened_on": date.today().isoformat()},
                {"field": "prompt_terms", "issue": "Mô tả tiếng Anh cho mô hình do nhóm viết, cần chuyên gia rà soát biểu tượng",
                 "status": "open", "opened_on": date.today().isoformat()},
            ],
        },
    }
    selection = assess_selection(item, ROOT)
    item["selection_at_ingest"] = {k: v for k, v in selection.items() if k != "heritage_id"}
    print(json.dumps({"heritage_id": hid, "sha1_ok": True, "segmentation": seg, "geometry": geo,
                      "selection": item["selection_at_ingest"]}, ensure_ascii=False, indent=2))
    if args.dry_run:
        out_png.unlink(missing_ok=True)
        print(f"Chạy thử: không ghi danh mục. Ảnh xem trước: {PREVIEW / f'{hid}.jpg'}")
        return 0
    if selection["technical_overall"] == "fail":
        out_png.unlink(missing_ok=True)
        raise SystemExit("Ảnh không đạt C1/C2 — không nạp vào danh mục.")

    ORIGINALS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, ORIGINALS / f"{hid}{src.suffix.lower()}")
    meta["items"][hid] = item
    meta["_meta"].setdefault("history", []).append(
        {"date": date.today().isoformat(), "event": f"Tiếp nhận {hid} từ {cand['id']} (CC0), trạng thái pending_ingest."})
    atomic_json(META, meta)
    if args.name_en and args.description_en:
        terms = json.loads(TERMS.read_text(encoding="utf-8"))
        terms["terms"][hid] = {"name_en": args.name_en, "base_description": args.description_en, "source": "human",
                               "generated_on": date.today().isoformat(), "reviewed_by_human": False}
        atomic_json(TERMS, terms)
    cands = json.loads(cand_file.read_text(encoding="utf-8"))
    for c in cands["candidates"]:
        if c["id"] == cand["id"]:
            c["ingested_as"] = hid
    atomic_json(cand_file, cands)
    print(f"Đã nạp {hid} ({item['code']}) ở trạng thái pending_ingest.")
    return 0


def activate(args) -> int:
    meta = json.loads(META.read_text(encoding="utf-8"))
    item = meta["items"].get(args.heritage_id)
    if item is None:
        raise SystemExit(f"Không có {args.heritage_id}")
    terms = json.loads(TERMS.read_text(encoding="utf-8"))["terms"]
    problems = []
    if args.heritage_id not in terms:
        problems.append("chưa có prompt_terms (--name-en, --description-en)")
    if not item.get("visual_summary"):
        problems.append("chưa có visual_summary do nhóm viết")
    open_flags = [f["field"] for f in item["provenance"].get("review_flags", []) if f.get("status") == "open"]
    if open_flags:
        problems.append(f"còn cờ rà soát mở: {open_flags}")
    if problems:
        raise SystemExit("Chưa kích hoạt được: " + "; ".join(problems))
    item["status"] = "active"
    meta["_meta"].setdefault("history", []).append({"date": date.today().isoformat(), "event": f"Kích hoạt {args.heritage_id}."})
    atomic_json(META, meta)
    print(f"{args.heritage_id} đã ở trạng thái active. Chạy pipeline trên máy GPU để có thiết kế.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--heritage-id", required=True, help="Mã tệp/khóa danh mục, chỉ chữ, số, _ và -")
    ap.add_argument("--activate", action="store_true", help="Chuyển mục pending_ingest sang active sau khi rà soát")
    ap.add_argument("--file")
    ap.add_argument("--candidate", help="Mã ứng viên, ví dụ DSC05640")
    ap.add_argument("--candidates", help="Tệp danh sách ứng viên (mặc định: data/heritage/sources/commons_candidates_*.json)")
    ap.add_argument("--name", help="Tên hiện vật tiếng Việt")
    ap.add_argument("--dating", help="Niên đại theo nhãn bảo tàng")
    ap.add_argument("--replaces", help="heritage_id của hiện vật được thay")
    ap.add_argument("--name-en")
    ap.add_argument("--description-en", help="≤ 21 token; không dùng từ chỉ hình dáng vật chứa")
    ap.add_argument("--margin", type=float, default=0.04, help="Khung GrabCut cách mép (tỉ lệ)")
    ap.add_argument("--rect", help="Khung GrabCut tự chọn x0,y0,x1,y1 (pixel ảnh gốc)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    if not args.heritage_id.replace("_", "").replace("-", "").isalnum():
        raise SystemExit("heritage-id chỉ gồm chữ, số, _ và -")
    if args.activate:
        return activate(args)
    if not (args.file and args.candidate and args.name):
        ap.error("cần --file, --candidate, --name")
    return ingest(args)


if __name__ == "__main__":
    sys.exit(main())
