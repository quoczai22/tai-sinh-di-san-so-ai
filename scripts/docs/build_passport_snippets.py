"""Vẽ các đoạn của một file Design Passport (JSON) thành ảnh PNG để đưa vào báo cáo LaTeX.

Chữ trong ảnh lấy nguyên văn từ file, có số dòng thật của file và tô màu cú pháp. Dòng quá dài được ngắt xuống dòng,
không cắt bớt chữ. Đây là ảnh vẽ lại từ nội dung file, không phải ảnh chụp màn hình trình soạn thảo.

Các ảnh (mỗi ảnh trả lời một ý của yêu cầu 3 của ban tổ chức):
  passport_1_nguon_goc.png          heritage: hiện vật gốc, nguồn, giấy phép, ghi công
  passport_2_cac_buoc.png           process_steps: mọi bước ghép thành một ảnh, mỗi hàng 3 bước nhỏ; cho biết bước đó ai làm, bằng công cụ gì
  passport_3_nhan_ai.png            ai_disclosure: nhãn AI và bước nào do AI, hệ thống, người
  passport_4_quyen_theo_muc_dich.png  rights: quyền hiển thị, xuất bản, thương mại
  passport_5_kiem_toan_ven.png      kết quả chạy thật lệnh kiểm toàn vẹn chuỗi mã băm của mọi Passport
  passport_6_chat_luong.png         quality: kết quả các cổng chất lượng và kết luận chung (chia 3 đoạn, ghép ngang thành một ảnh)
  passport_7_phien_ban.png          versions: các phiên bản của thiết kế (sau khi sửa tay có thêm một phiên bản human_edit)
  passport_8_chinh_sua_duyet.png    edits, reviews, approval: lịch sử sửa tay và trạng thái duyệt
  passport_9_so_cai.png             ledger: N sự kiện cuối của sổ cái (mặc định 3, đổi bằng --so-cai N), có prev_hash và entry_hash nối nhau
  (chỉ lần 2) anh_truoc_sau.png     ảnh trước và sau khi sửa cạnh nhau; ma_bam_truoc_sau.png  tính lại SHA-256 hai tệp so với Passport

Chụp theo từng lần để so sánh (ảnh vào outputs/report_figures/passport/lan<N>/):
    uv run python scripts/docs/build_passport_snippets.py --lan 1    # sau khi tạo thiết kế, chưa sửa
    uv run python scripts/docs/build_passport_snippets.py --lan 2    # sau khi tải bản chỉnh sửa lên; in thêm phần thay đổi so với lần 1
Lần 1 lưu thêm bản sao JSON của các Passport cùng một lần chạy (lan1/snapshot/) để lần 2 so sánh đúng file đó; file đã có trong snapshot không bị ghi đè.
Không chỉ file thì lần 1 lấy Passport mới nhất, lần 2 lấy Passport mới nhất đã có bản sửa tay. Muốn chọn file:
    uv run python scripts/docs/build_passport_snippets.py --lan 1 outputs/passports/DP-HV07-20261121T160957-V2.json
Thêm --toi để vẽ nền tối. Không có --lan: ảnh vào outputs/report_figures/passport/ và không so sánh. Thư mục ảnh là thư mục sinh ra, không commit.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
PASSPORTS = ROOT / "outputs" / "passports"
OUT = ROOT / "outputs" / "report_figures" / "passport"

WRAP = 104                  # số ký tự tối đa mỗi dòng ảnh, quá thì ngắt xuống dòng
SIZE, LINE_H, PAD = 20, 28, 28
# Hai bộ màu: nền sáng (mặc định) và nền tối (--toi, cùng màu nền với ảnh kết quả kiểm toàn vẹn)
LIGHT = {"bg": (255, 255, 255), "gutter": (150, 156, 166), "edge": (214, 218, 224),
         "key": (36, 80, 138), "str": (46, 122, 100), "num": (176, 96, 0), "lit": (122, 40, 150), "other": (29, 42, 54)}
DARK = {"bg": (30, 34, 40), "gutter": (112, 120, 132), "edge": (62, 68, 78),
        "key": (121, 184, 255), "str": (126, 214, 160), "num": (255, 171, 92), "lit": (210, 160, 255), "other": (222, 226, 232)}
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


def draw(lines: list[str], first: int, last: int, theme: dict = LIGHT, wrap: int = WRAP, min_height: int = 0) -> Image.Image:
    """Vẽ các dòng từ first đến last (đánh số từ 1) thành một ảnh; dòng dài hơn wrap ký tự bị ngắt xuống dòng."""
    fnt = font()
    cw = fnt.getlength("M")
    rows: list[tuple[str, str, list[str]]] = []          # (số dòng hoặc rỗng, đoạn chữ, loại màu từng ký tự)
    for n in range(first, last + 1):
        line = lines[n - 1]                              # lines đã tách bằng splitlines nên không còn ký tự xuống dòng
        kinds = char_kinds(line)
        for k, (i, j) in enumerate(wrap_line(line, wrap)):
            rows.append((str(n) if k == 0 else "", line[i:j], kinds[i:j]))
    gut = int(cw * len(str(last))) + 24
    W = int(PAD * 2 + gut + cw * (wrap + 1))
    H = max(PAD * 2 + LINE_H * len(rows), min_height)
    img = Image.new("RGB", (W, H), theme["bg"])
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=theme["edge"])
    d.line([(PAD + gut - 10, PAD // 2), (PAD + gut - 10, H - PAD // 2)], fill=theme["edge"])
    for r, (num, part, kinds) in enumerate(rows):
        y = PAD + r * LINE_H
        d.text((PAD + gut - 20 - fnt.getlength(num), y), num, font=fnt, fill=theme["gutter"])
        for c, (ch, kind) in enumerate(zip(part, kinds)):
            d.text((PAD + gut + c * cw, y), ch, font=fnt, fill=theme[kind])
    return img


def render(lines: list[str], first: int, last: int, path: Path, theme: dict = LIGHT) -> None:
    """Vẽ các dòng từ first đến last thành ảnh PNG."""
    draw(lines, first, last, theme).save(path)


def split_ranges(lines: list[str], first: int, last: int, parts: int) -> list[tuple[int, int]]:
    """Chia các dòng first đến last thành parts đoạn liền nhau, dài gần bằng nhau.

    Chỗ cắt là dòng mở một khóa JSON (bắt đầu bằng dấu ngoặc kép), thụt vào không quá 6 chữ trống, ưu tiên khóa thụt 4 chữ
    trống (như G2_pattern, G3_final) để mỗi đoạn bắt đầu ở một mục rõ ràng."""
    def indent(n: int) -> int:
        return len(lines[n - 1]) - len(lines[n - 1].lstrip())
    cuts: list[int] = []
    for k in range(1, parts):
        target = first + (last - first + 1) * k / parts
        low = (cuts[-1] if cuts else first) + 1
        cands = [n for n in range(low, last) if indent(n) <= 6 and lines[n - 1].lstrip().startswith('"')] or [round(target)]
        cuts.append(min(cands, key=lambda n: abs(n - target) + (3 if indent(n) > 4 else 0)))
    return list(zip([first, *cuts], [c - 1 for c in cuts] + [last]))


def render_grid(lines: list[str], ranges: list[tuple[int, int]], path: Path, theme: dict = LIGHT, per_row: int = 3, wrap: int = 70) -> None:
    """Vẽ mỗi khoảng dòng trong ranges thành một ô nhỏ rồi xếp lưới, mỗi hàng per_row ô; các ô cùng hàng cao bằng nhau."""
    gap = 24
    rows = []
    for i in range(0, len(ranges), per_row):
        group = ranges[i:i + per_row]
        height = max(draw(lines, a, b, theme, wrap).height for a, b in group)
        rows.append([draw(lines, a, b, theme, wrap, height) for a, b in group])
    width = max(sum(p.width for p in r) + gap * (len(r) - 1) for r in rows)
    sheet = Image.new("RGB", (width, sum(r[0].height for r in rows) + gap * (len(rows) - 1)), theme["bg"])
    y = 0
    for r in rows:
        x = 0
        for p in r:
            sheet.paste(p, (x, y))
            x += p.width + gap
        y += r[0].height + gap
    sheet.save(path)


def render_columns(lines: list[str], first: int, last: int, path: Path, theme: dict = LIGHT, parts: int = 3, wrap: int = 62) -> list[tuple[int, int]]:
    """Chia các dòng first đến last thành parts đoạn rồi ghép thành MỘT ảnh, các đoạn đứng cạnh nhau theo chiều ngang, cao bằng nhau.

    Trả về các khoảng dòng của từng đoạn. Dòng dài hơn wrap ký tự bị ngắt (khóa quality ngắn nên cột hẹp là đủ)."""
    ranges = split_ranges(lines, first, last, parts)
    height = max(draw(lines, a, b, theme, wrap).height for a, b in ranges)
    panels = [draw(lines, a, b, theme, wrap, height) for a, b in ranges]
    gap = 24
    sheet = Image.new("RGB", (sum(p.width for p in panels) + gap * (len(panels) - 1), height), theme["bg"])
    x = 0
    for p in panels:
        sheet.paste(p, (x, 0))
        x += p.width + gap
    sheet.save(path)
    return ranges


def render_verify(path: Path) -> str:
    """Chạy thật lệnh kiểm toàn vẹn và vẽ lệnh cùng kết quả như một cửa sổ dòng lệnh. Trả về dòng kết quả."""
    res = subprocess.run([sys.executable, "-c", VERIFY], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    result = res.stdout.strip() or f"LỖI: {res.stderr.strip()[-300:]}"
    shown = ['PS> uv run python -c "' + VERIFY + '"']
    lines = [part for l in shown for part in textwrap.wrap(l, WRAP, break_long_words=True, break_on_hyphens=False)] + ["", result]
    draw_console(lines, path, {result})
    return result


def draw_console(lines: list[str], path: Path, green: set[str] = frozenset()) -> None:
    """Vẽ các dòng chữ như một cửa sổ dòng lệnh nền tối; dòng nào thuộc green thì tô xanh."""
    fnt = font()
    W = int(PAD * 2 + fnt.getlength("M") * (WRAP + 1))
    H = PAD * 2 + LINE_H * len(lines)
    img = Image.new("RGB", (W, H), (30, 34, 40))
    d = ImageDraw.Draw(img)
    for i, l in enumerate(lines):
        d.text((PAD, PAD + i * LINE_H), l, font=fnt, fill=(120, 220, 160) if l in green else (222, 226, 232))
    img.save(path)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_before_after(doc: dict, out: Path, theme: dict) -> list[str]:
    """Lần 2: ghép ảnh trước và sau sửa cạnh nhau (anh_truoc_sau.png) và vẽ kết quả tính lại SHA-256 của hai tệp so với
    before_sha256, after_sha256 của lần sửa mới nhất trong Passport (ma_bam_truoc_sau.png). Trả về các dòng kết quả."""
    edit = doc["edits"][-1]
    before_rel = next(v["path"] for v in doc["versions"] if v["sha256"] == edit["before_sha256"])
    pairs = [("Ảnh trước khi sửa", before_rel, edit["before_sha256"], "before_sha256"),
             ("Ảnh sau khi sửa", edit["after_path"], edit["after_sha256"], "after_sha256")]
    imgs = [Image.open(ROOT / p).convert("RGB") for _, p, _, _ in pairs]
    height = min(i.height for i in imgs)
    imgs = [i.resize((round(i.width * height / i.height), height)) for i in imgs]
    gap = 24
    sheet = Image.new("RGB", (sum(i.width for i in imgs) + gap, height), theme["bg"])
    sheet.paste(imgs[0], (0, 0))
    sheet.paste(imgs[1], (imgs[0].width + gap, 0))
    sheet.save(out / "anh_truoc_sau.png")
    lines, results = [f"Tính lại SHA-256 từ tệp trên đĩa, so với {edit['edit_id']} trong Passport:", ""], []
    for label, rel, recorded, key in pairs:
        real = sha256_of(ROOT / rel)
        verdict = "KHỚP" if real == recorded else "KHÔNG KHỚP"
        results.append(f"  {key}: {verdict}")
        lines += [f"{label}: {rel}", f"  tính lại từ tệp : {real}", f"  trong Passport  : {recorded}", results[-1], ""]
    lines += ["Hai mã băm khác nhau: " + ("có" if pairs[0][2] != pairs[1][2] else "KHÔNG") + " (ảnh sau sửa là một tệp khác)"]
    lines = [part for l in lines for part in (textwrap.wrap(l, WRAP, subsequent_indent="  ", break_long_words=True) or [""])]
    draw_console(lines, out / "ma_bam_truoc_sau.png", set(r for r in results if "KHỚP" in r and "KHÔNG" not in r))
    return results


def pick_passport(lan: int | None) -> Path:
    """Passport mặc định: lần 2 lấy file mới nhất đã có bản sửa tay, còn lại lấy file mới nhất (theo giờ ghi file)."""
    files = sorted(PASSPORTS.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if lan == 2:
        files = [f for f in files if json.loads(f.read_text(encoding="utf-8")).get("edits")]
    if not files:
        sys.exit("Không tìm thấy Passport" + (" nào đã có bản sửa tay." if lan == 2 else "."))
    return files[0]


def flatten(obj, prefix: str = ""):
    """Duỗi dict lồng nhau thành các cặp (đường dẫn.khóa, giá trị lá) để so sánh từng trường."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flatten(v, f"{prefix}.{k}" if prefix else k)
    else:
        yield prefix, obj


def item_label(x) -> str:
    """Tên ngắn của một phần tử mới trong danh sách Passport (bước, phiên bản, lần sửa, sự kiện sổ cái, tệp)."""
    if not isinstance(x, dict):
        return str(x)
    if "seq" in x:
        return f"#{x['seq']} {x.get('event')}"
    return str(x.get("edit_id") or x.get("step") or (f"v{x['version']} {x.get('kind')}" if "version" in x else None) or x.get("path") or "?")


def describe_diff(old: dict, new: dict) -> list[str]:
    """Liệt kê thay đổi giữa hai trạng thái của cùng một Passport: danh sách dài thêm mục nào, quality và approval đổi trường nào."""
    out = []
    lists = ("artifacts", "process_steps", "versions", "edits", "reviews", "ledger")
    for key in lists:
        a, b = old.get(key, []), new.get(key, [])
        if len(a) != len(b):
            out.append(f"{key}: {len(a)} thành {len(b)} mục, mục mới: " + ", ".join(item_label(x) for x in b[len(a):]))
        elif a != b:
            out.append(f"{key}: số mục giữ nguyên nhưng nội dung đã đổi")
    for key in ("quality", "approval"):
        fo, fn = dict(flatten(old.get(key, {}), key)), dict(flatten(new.get(key, {}), key))
        out += [f"{p}: {fo.get(p)!r} thành {fn.get(p)!r}" for p in sorted(set(fo) | set(fn)) if fo.get(p) != fn.get(p)]
    rest = [k for k in new if k not in lists + ("quality", "approval") and old.get(k) != new[k]]
    if rest:
        out.append("khóa khác có đổi: " + ", ".join(rest))
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Vẽ các đoạn của file Design Passport thành ảnh cho báo cáo")
    ap.add_argument("passport", nargs="?", type=Path, help="file Passport JSON (mặc định: xem đầu file)")
    ap.add_argument("--toi", action="store_true", help="nền tối (mặc định nền sáng)")
    ap.add_argument("--so-cai", type=int, default=3, help="số sự kiện cuối của sổ cái (ledger) đưa vào ảnh (mặc định 3)")
    ap.add_argument("--lan", type=int, choices=(1, 2), help="lần chụp: 1 = trước khi sửa tay, 2 = sau khi tải bản sửa lên")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")        # cửa sổ dòng lệnh Windows mặc định không in được tiếng Việt
    sys.stderr.reconfigure(encoding="utf-8")
    passport = args.passport or pick_passport(args.lan)
    lines = passport.read_text(encoding="utf-8").splitlines()
    out = OUT / f"lan{args.lan}" if args.lan else OUT
    rng = top_level_ranges(lines)
    out.mkdir(parents=True, exist_ok=True)
    steps = item_ranges(lines, *rng["process_steps"])
    for old in out.glob("passport_2*.png"):       # xóa ảnh các bước của lần chạy trước (số bước có thể khác)
        old.unlink()

    jobs = [("passport_1_nguon_goc.png", *rng["heritage"]),
            ("passport_2_cac_buoc.png", *rng["process_steps"]),
            ("passport_3_nhan_ai.png", *rng["ai_disclosure"]),
            ("passport_4_quyen_theo_muc_dich.png", *rng["rights"]),
            ("passport_6_chat_luong.png", *rng["quality"]),
            ("passport_7_phien_ban.png", *rng["versions"]),
            ("passport_8_chinh_sua_duyet.png", rng["edits"][0], rng["approval"][1]),      # edits, reviews, approval nằm liền nhau
            ("passport_9_so_cai.png", *rng["ledger"])]
    theme = DARK if args.toi else LIGHT
    for name, first, last in jobs:
        if name == "passport_9_so_cai.png":               # chỉ N sự kiện cuối, xếp lưới như các bước
            tail = item_ranges(lines, first, last)[-args.so_cai:]
            render_grid(lines, tail, out / name, theme)
            print(f"{name}: {len(tail)} sự kiện cuối, dòng {tail[0][0]} đến {tail[-1][1]} của {passport.name}")
            continue
        if name == "passport_2_cac_buoc.png":             # mỗi bước một ô nhỏ, ghép lưới 3 ô một hàng
            render_grid(lines, steps, out / name, theme)
            print(f"{name}: {len(steps)} bước ghép lưới, dòng {first} đến {last} của {passport.name}")
            continue
        if name == "passport_6_chat_luong.png":           # quality dài: chia 3 đoạn, ghép ngang thành một ảnh
            parts = render_columns(lines, first, last, out / name, theme)
            print(f"{name}: dòng {first} đến {last} của {passport.name}, chia 3 đoạn " + ", ".join(f"{a}-{b}" for a, b in parts))
            continue
        render(lines, first, last, out / name, theme)
        print(f"{name}: dòng {first} đến {last} của {passport.name}")
    print("passport_5_kiem_toan_ven.png:", render_verify(out / "passport_5_kiem_toan_ven.png"))
    new = json.loads("\n".join(lines))
    if args.lan == 1:                      # lưu bản sao các Passport cùng lần chạy để lần 2 có cái so sánh
        snap = out / "snapshot"
        snap.mkdir(exist_ok=True)
        for f in PASSPORTS.glob("*.json"):
            # Không ghi đè bản đã lưu: nó là bản GỐC trước khi sửa, chạy lại --lan 1 sau khi sửa tay không được làm mất nó
            if json.loads(f.read_text(encoding="utf-8")).get("run_id") == new.get("run_id") and not (snap / f.name).exists():
                shutil.copy2(f, snap / f.name)
        print(f"Đã lưu bản sao Passport của lần chạy {new.get('run_id')} vào {snap}")
    elif args.lan == 2:
        before = OUT / "lan1" / "snapshot" / passport.name
        if not before.exists():
            print(f"Chưa có bản lần 1 của {passport.name} (chạy --lan 1 trước khi sửa), nên không so sánh được.")
        else:
            print(f"Thay đổi của {passport.name} so với lần 1:")
            for line in describe_diff(json.loads(before.read_text(encoding="utf-8")), new):
                print("  -", line)
    if args.lan == 2 and new.get("edits"):                 # ảnh trước/sau và mã băm chỉ có nghĩa khi Passport đã có bản sửa
        for line in render_before_after(new, out, theme):
            print("  ", line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
