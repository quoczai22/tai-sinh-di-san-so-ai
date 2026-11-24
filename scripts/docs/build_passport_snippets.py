"""Vẽ các đoạn của một file Design Passport (JSON) thành ảnh PNG để đưa vào báo cáo LaTeX.

Chữ trong ảnh lấy nguyên văn từ file, có số dòng thật của file và tô màu cú pháp. Dòng quá dài được ngắt xuống dòng,
không cắt bớt chữ. Đây là ảnh vẽ lại từ nội dung file, không phải ảnh chụp màn hình trình soạn thảo.

Các ảnh (mỗi ảnh trả lời một ý của yêu cầu 3 của ban tổ chức):
  passport_1_nguon_goc.png          heritage: hiện vật gốc, nguồn, giấy phép, ghi công
  passport_2a_chuoi_buoc_1_5.png    process_steps, nửa đầu (bước 1 đến 5): chuỗi truy vết, mỗi bước ai làm
  passport_2b_chuoi_buoc_6_9.png    process_steps, nửa sau (tên file ghi số bước thật: Passport mức 1 có 10 bước nên là 6_10)
  passport_3_nhan_ai.png            ai_disclosure: nhãn AI và bước nào do AI, hệ thống, người
  passport_4_quyen_theo_muc_dich.png  rights: quyền hiển thị, xuất bản, thương mại
  passport_5_kiem_toan_ven.png      kết quả chạy thật lệnh kiểm toàn vẹn chuỗi mã băm của mọi Passport

    uv run python scripts/docs/build_passport_snippets.py
    uv run python scripts/docs/build_passport_snippets.py outputs/passports/DP-HV07-20261121T160957-V2.json

Kết quả: outputs/report_figures/passport/ (thư mục sinh ra, không commit).
"""
import argparse
import re
import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "outputs" / "passports" / "DP-HV07-20261121T160957-V2.json"
OUT = ROOT / "outputs" / "report_figures" / "passport"

WRAP = 104                  # số ký tự tối đa mỗi dòng ảnh, quá thì ngắt xuống dòng
SIZE, LINE_H, PAD = 20, 28, 28
BG, GUTTER, EDGE = (255, 255, 255), (150, 156, 166), (214, 218, 224)
COLORS = {"key": (36, 80, 138), "str": (46, 122, 100), "num": (176, 96, 0), "lit": (122, 40, 150), "other": (29, 42, 54)}
TOKEN = re.compile(r'(?P<key>"(?:[^"\\]|\\.)*"(?=\s*:))|(?P<str>"(?:[^"\\]|\\.)*")'
                   r'|(?P<num>-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)|(?P<lit>true|false|null)|(?P<other>.)', re.S)
# Lệnh kiểm toàn vẹn giống mục "Cách tự kiểm tra" trong docs/evidence/README.md
VERIFY = ("import glob, json; from pathlib import Path; from tsds.provenance import passport as P; "
          "fs = sorted(glob.glob('outputs/passports/*.json')); "
          "ok = sum(bool(P.verify(json.load(open(f, encoding='utf-8')), Path('.'))['ok']) for f in fs); "
          "print(ok, '/', len(fs), 'Passport toàn vẹn')")


def font() -> ImageFont.FreeTypeFont:
    """Phông đơn cách có đủ dấu tiếng Việt; thiếu thì thử Courier rồi phông mặc định."""
    for name in ("consola.ttf", "cour.ttf", "DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(name, SIZE)
        except OSError:
            continue
    return ImageFont.load_default()


def top_level_ranges(lines: list[str]) -> dict[str, tuple[int, int]]:
    """Khóa cấp cao nhất của file JSON thụt 2 dòng: trả về {khóa: (dòng đầu, dòng cuối)}, số dòng tính từ 1."""
    starts = [(m.group(1), i) for i, l in enumerate(lines, 1) if (m := re.match(r'^  "([^"]+)":', l))]
    out = {}
    for n, (key, first) in enumerate(starts):
        last = (starts[n + 1][1] - 1) if n + 1 < len(starts) else len(lines) - 1   # dòng cuối của file là dấu }
        out[key] = (first, last)
    return out


def item_ranges(lines: list[str], first: int, last: int) -> list[tuple[int, int]]:
    """Các phần tử của một mảng cấp cao nhất (mỗi phần tử mở bằng dòng '    {' và đóng bằng '    }'), số dòng tính từ 1."""
    out, start = [], None
    for i in range(first, last + 1):
        l = lines[i - 1].rstrip(",")
        if l == "    {":
            start = i
        elif l == "    }" and start is not None:
            out.append((start, i))
            start = None
    return out


def wrap_line(line: str, width: int = WRAP) -> list[tuple[int, int]]:
    """Chia một dòng dài thành các đoạn (đầu, cuối) không quá width ký tự, ưu tiên ngắt sau khoảng trắng.

    Ghép các đoạn lại đúng bằng dòng gốc, không mất hay thêm ký tự nào."""
    cuts, start = [], 0
    while len(line) - start > width:
        window = line[start:start + width]
        sp = window.rfind(" ")
        end = start + (sp + 1 if sp > width // 2 else width)
        cuts.append((start, end))
        start = end
    cuts.append((start, len(line)))
    return cuts


def char_kinds(line: str) -> list[str]:
    """Loại tô màu của từng ký tự, tính trên cả dòng để chuỗi dài bị ngắt vẫn giữ màu chuỗi."""
    kinds: list[str] = []
    for m in TOKEN.finditer(line):
        kinds += [m.lastgroup] * len(m.group())
    return kinds


def render(lines: list[str], first: int, last: int, path: Path) -> None:
    """Vẽ các dòng từ first đến last (đánh số từ 1) thành ảnh PNG."""
    fnt = font()
    cw = fnt.getlength("M")
    rows: list[tuple[str, str, list[str]]] = []          # (số dòng hoặc rỗng, đoạn chữ, loại màu từng ký tự)
    for n in range(first, last + 1):
        line = lines[n - 1]                              # lines đã tách bằng splitlines nên không còn ký tự xuống dòng
        kinds = char_kinds(line)
        for k, (i, j) in enumerate(wrap_line(line)):
            rows.append((str(n) if k == 0 else "", line[i:j], kinds[i:j]))
    gut = int(cw * len(str(last))) + 24
    W = int(PAD * 2 + gut + cw * (WRAP + 1))
    H = PAD * 2 + LINE_H * len(rows)
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=EDGE)
    d.line([(PAD + gut - 10, PAD // 2), (PAD + gut - 10, H - PAD // 2)], fill=EDGE)
    for r, (num, part, kinds) in enumerate(rows):
        y = PAD + r * LINE_H
        d.text((PAD + gut - 20 - fnt.getlength(num), y), num, font=fnt, fill=GUTTER)
        for c, (ch, kind) in enumerate(zip(part, kinds)):
            d.text((PAD + gut + c * cw, y), ch, font=fnt, fill=COLORS[kind])
    img.save(path)


def render_verify(path: Path) -> str:
    """Chạy thật lệnh kiểm toàn vẹn và vẽ lệnh cùng kết quả như một cửa sổ dòng lệnh. Trả về dòng kết quả."""
    res = subprocess.run([sys.executable, "-c", VERIFY], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    result = res.stdout.strip() or f"LỖI: {res.stderr.strip()[-300:]}"
    shown = ['PS> uv run python -c "' + VERIFY + '"']
    lines = [part for l in shown for part in textwrap.wrap(l, WRAP, break_long_words=True, break_on_hyphens=False)] + ["", result]
    fnt = font()
    W = int(PAD * 2 + fnt.getlength("M") * (WRAP + 1))
    H = PAD * 2 + LINE_H * len(lines)
    img = Image.new("RGB", (W, H), (30, 34, 40))
    d = ImageDraw.Draw(img)
    for i, l in enumerate(lines):
        d.text((PAD, PAD + i * LINE_H), l, font=fnt, fill=(120, 220, 160) if l == result else (222, 226, 232))
    img.save(path)
    return result


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Vẽ các đoạn của file Design Passport thành ảnh cho báo cáo")
    ap.add_argument("passport", nargs="?", type=Path, default=DEFAULT, help="file Passport JSON")
    args = ap.parse_args(argv)
    lines = args.passport.read_text(encoding="utf-8").splitlines()
    rng = top_level_ranges(lines)
    OUT.mkdir(parents=True, exist_ok=True)
    steps = item_ranges(lines, *rng["process_steps"])
    half = (len(steps) + 1) // 2
    jobs = [("passport_1_nguon_goc.png", *rng["heritage"]),
            (f"passport_2a_chuoi_buoc_1_{half}.png", rng["process_steps"][0], steps[half - 1][1]),
            (f"passport_2b_chuoi_buoc_{half + 1}_{len(steps)}.png", steps[half][0], rng["process_steps"][1]),
            ("passport_3_nhan_ai.png", *rng["ai_disclosure"]),
            ("passport_4_quyen_theo_muc_dich.png", *rng["rights"])]
    for name, first, last in jobs:
        render(lines, first, last, OUT / name)
        print(f"{name}: dòng {first} đến {last} của {args.passport.name}")
    print("passport_5_kiem_toan_ven.png:", render_verify(OUT / "passport_5_kiem_toan_ven.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
