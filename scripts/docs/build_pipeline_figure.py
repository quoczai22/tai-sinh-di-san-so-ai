"""Xuất ảnh từng bước của pipeline từ MỘT lần chạy có sẵn, KHÔNG có chữ trong ảnh (không chạy lại mô hình, không cần GPU).

Mỗi lần chạy lưu ảnh trung gian trong outputs/runs/<run_id>/ (00_reference.png, 01_canny.png, garment.png, ...).
Script gom ảnh theo bước: mỗi bước một file PNG. Bước có 4 thiết kế thì 4 ảnh xếp cạnh nhau (từ mức sáng tạo 1 đến 4).
Tên file ghi số bước và nội dung bước, ví dụ buoc05_hoa_van_sinh_ra_4_muc.png.

    uv run python scripts/docs/build_pipeline_figure.py                      # lần chạy mới nhất
    uv run python scripts/docs/build_pipeline_figure.py R20261121T160957-HV07

Kết quả: outputs/pipeline_viz/<run_id>/buoc*.png (thư mục sinh ra, không commit).
Các hàm font, fit, draw_wrapped, red_overlay và hằng màu ở đây còn được scripts/eval/print_region_mask.py dùng lại.
"""
import argparse
import json
import sys
import textwrap
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
RUNS = ROOT / "outputs" / "runs"
OUT = ROOT / "outputs" / "pipeline_viz"

# Màu và cỡ chung, dùng lại trong scripts/eval/print_region_mask.py (bảng có chữ của thí nghiệm đó)
BG, INK, MUTED, ACCENT, LINE = (250, 248, 244), (29, 42, 54), (110, 118, 128), (36, 80, 138), (200, 196, 188)
PAD = 40


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Phông Windows có đủ dấu tiếng Việt; thiếu thì thử Arial rồi phông mặc định."""
    for name in ("segoeuib.ttf" if bold else "segoeui.ttf", "arialbd.ttf" if bold else "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def latest_run() -> Path:
    runs = sorted(p for p in RUNS.iterdir() if (p / "manifest.json").is_file())
    if not runs:
        sys.exit("Không có lần chạy nào trong outputs/runs/")
    return runs[-1]


def fit(img: Image.Image, w: int, h: int) -> Image.Image:
    """Thu ảnh vừa khung w x h, giữ tỉ lệ, nền trắng."""
    img = img.convert("RGB")
    img.thumbnail((w, h), Image.LANCZOS)
    canvas = Image.new("RGB", (w, h), (255, 255, 255))
    canvas.paste(img, ((w - img.width) // 2, (h - img.height) // 2))
    return canvas


def draw_wrapped(d: ImageDraw.ImageDraw, xy, text: str, fnt, fill, width_chars: int, gap: int = 4) -> int:
    """Vẽ đoạn chữ tự xuống dòng, trả về tung độ ngay dưới đoạn."""
    x, y = xy
    for line in textwrap.wrap(text, width_chars) or [""]:
        d.text((x, y), line, font=fnt, fill=fill)
        y += fnt.size + gap
    return y


def red_overlay(base: Image.Image, mask: np.ndarray, fill_alpha: float = 0.40) -> Image.Image:
    """Tô đỏ nửa trong suốt lên vùng mask (giá trị lớn hơn 0.5 sau khi chuẩn hóa) và vẽ viền đỏ đậm quanh vùng đó."""
    img = np.asarray(base.convert("RGB")).astype(np.float32)
    inside = mask > 0.5
    img[inside] = img[inside] * (1 - fill_alpha) + np.array([255, 0, 0], np.float32) * fill_alpha
    out = np.clip(img, 0, 255).astype(np.uint8)
    contours, _ = cv2.findContours(inside.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(out, contours, -1, (255, 0, 0), 3)
    return Image.fromarray(out)


def cluster(imgs: list[Image.Image], gap: int = 24, max_side: int = 1100) -> Image.Image:
    """Xếp các ảnh thành một hàng ngang, cách nhau gap px, nền trắng, không chữ. Ảnh quá lớn được thu nhỏ."""
    fixed = []
    for im in imgs:
        im = im.convert("RGB")
        im.thumbnail((max_side, max_side), Image.LANCZOS)
        fixed.append(im)
    H = max(im.height for im in fixed)
    out = Image.new("RGB", (sum(im.width for im in fixed) + gap * (len(fixed) - 1), H), (255, 255, 255))
    x = 0
    for im in fixed:
        out.paste(im, (x, (H - im.height) // 2))
        x += im.width + gap
    return out


def step_clusters(run_dir: Path, m: dict) -> list[Path]:
    """Xuất mỗi bước một ảnh vào outputs/pipeline_viz/<run_id>/. Trả về danh sách file đã ghi."""
    from tsds.generation.garment import garment      # noqa: PLC0415  (import chậm vài giây, chỉ cần để tính vùng in)

    designs = sorted((x for x in m["designs"] if x["status"] == "completed"), key=lambda x: x["variant_index"])
    nums = [x["variant_index"] for x in designs]
    heritage = ROOT / "data" / "heritage"
    panel = heritage / "panels" / f"{m['heritage_id']}.png"
    tpl = Image.open(run_dir / "garment.png").convert("RGB")
    region = (np.asarray(Image.open(run_dir / "garment_mask.png").convert("L")) > 127).astype(np.uint8)
    # Vùng in: cùng hàm pipeline dùng khi ghép (garment._layout_mask), theo bố cục ghi trong manifest
    zones = [garment._layout_mask(tpl, garment.get_layout(x["layout"]), region) for x in designs]
    gray = [Image.fromarray((np.clip(z, 0, 1) * 255).round().astype(np.uint8)) for z in zones]

    steps: list[tuple[str, list[Image.Image]]] = [
        ("buoc01_hien_vat_goc", [Image.open(heritage / f"{m['heritage_id']}.png")]),
        ("buoc03_anh_tham_chieu", [Image.open(run_dir / "00_reference.png")]),
        ("buoc04_anh_canny_dieu_khien", [Image.open(run_dir / "01_canny.png")]),
        ("buoc05_hoa_van_sinh_ra_4_muc", [Image.open(run_dir / f"V{n}_pattern.png") for n in nums]),
        ("buoc06_ao_dai_nen_lora", [tpl]),
        ("buoc07_vung_ao_sam_to_do", [red_overlay(tpl, region)]),
        ("buoc08_mat_na_vung_in_4_bo_cuc", gray),
        ("buoc09_vung_in_to_do_4_bo_cuc", [red_overlay(tpl, z) for z in zones]),
        ("buoc10_ghep_hoa_van_len_ao_tho_4_bo_cuc", [Image.open(run_dir / f"V{n}_aodai_raw.png") for n in nums]),
        ("buoc11_ket_qua_sau_polish_4_thiet_ke", [Image.open(run_dir / f"V{n}_aodai.png") for n in nums]),
    ]
    if panel.is_file() and designs and designs[0]["source_element"] == "panel":
        steps.insert(1, ("buoc02_panel_texture_trai_phang", [Image.open(panel)]))
    out_dir = OUT / m["run_id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, imgs in steps:
        path = out_dir / f"{name}.png"
        cluster(imgs).save(path)
        paths.append(path)
    return paths


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Xuất ảnh từng bước pipeline (không chữ) từ một lần chạy có sẵn")
    ap.add_argument("run", nargs="?", help="mã lần chạy trong outputs/runs/ (bỏ trống là lần chạy mới nhất)")
    args = ap.parse_args(argv)
    run_dir = RUNS / args.run if args.run else latest_run()
    m = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    for p in step_clusters(run_dir, m):
        print(p.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
