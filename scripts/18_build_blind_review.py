"""Dựng gói đánh giá mù cho các thiết kế hiện có, kể cả thiết kế bị cổng chất lượng loại.

Nguồn thiết kế: bộ demo seed 42 (outputs/passports) cộng bộ nhiều seed nếu có (outputs/multiseed/passports, sinh bằng
`scripts/14_generate_demo_set.py --seed 43 --out outputs/multiseed`). Mỗi "ô" là một cặp (hiện vật, mức sáng tạo); mỗi ô có
một thiết kế cho mỗi seed. Mỗi người chấm chỉ thấy MỘT thiết kế của mỗi ô (6 hiện vật x 4 mức = 24 thiết kế, vẫn 25 đến 35
phút), seed nào thì xoay theo mã người chấm (CG01, CG02, CG03... lệch nhau một seed). Đủ 3 người liên tiếp là phủ hết mọi seed.

Người chấm là chuyên gia di sản và chuyên gia thiết kế, chấm theo bộ tiêu chí ER-1.0 (config/expert_rubric.json),
thang 1 đến 5, kèm quyết định Đạt / Cần chỉnh sửa / Loại. Phiếu điền ngay trên một trang HTML mở offline, xuất ra CSV.
Thiết kế bị cổng loại vẫn được đưa đi chấm để đo mức đồng thuận giữa cổng tự động và chuyên gia (hiệu chỉnh ngưỡng).

Gói gồm hai thư mục:
  GOI_GUI/    gửi cho người chấm: index.html, images/ (thiết kế, tên mã ngẫu nhiên), ref/ (ảnh hiện vật đối chiếu).
              Không có mã Passport, mức sáng tạo, điểm hay quyết định của cổng, không có tên tệp gốc.
  GIU_RIENG/  chỉ nhóm giữ: key.csv (mã đã đổi tên trỏ về Passport, mức sáng tạo, kết quả cổng), HUONG_DAN_NOI_BO.md.
Thứ tự hiện thiết kế được xáo riêng cho từng người chấm (theo mã người chấm họ nhập).

    uv run python scripts/18_build_blind_review.py                 # dựng vào outputs/blind_review/
    uv run python scripts/18_build_blind_review.py --out thư_mục   # chọn nơi dựng

Ảnh nằm trong outputs/ nên không đưa lên git (dữ liệu thô).
"""
import argparse
import csv
import html
import json
import random
import re
import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SEED = 20261120                    # seed gán mã ảnh ngẫu nhiên, cố định để dựng lại ra cùng một gói
REF_HEIGHT = 420                   # chiều cao ảnh hiện vật đối chiếu (px)


def latest_design_path(passport: dict) -> str:
    """Đường dẫn ảnh thiết kế mà giao diện web đang hiện: bản hệ thống sửa nếu là bản mới nhất, không thì bản cuối."""
    versions = passport["versions"]
    if versions and versions[-1].get("kind") == "system_repair":
        return versions[-1]["path"]
    return versions[0]["path"]


def default_passport_dirs(root: Path = ROOT) -> list[Path]:
    """Thư mục Passport mặc định: bộ demo seed 42, cộng bộ nhiều seed nếu đã sinh."""
    dirs = [root / "outputs" / "passports"]
    multi = root / "outputs" / "multiseed" / "passports"
    return dirs + ([multi] if multi.is_dir() else [])


def collect(root: Path = ROOT, passport_dirs: list[Path] | None = None) -> list[dict]:
    """Mọi thiết kế có ảnh: passport_id, hiện vật, ảnh, mức sáng tạo, seed, kết quả cổng. Sắp theo passport_id."""
    from provenance import passport as P                                 # noqa: PLC0415

    rows = []
    for d in passport_dirs if passport_dirs is not None else default_passport_dirs(root):
        for f in sorted(Path(d).glob("DP-*.json")):
            p = P.load(f)
            if not p["versions"]:
                continue
            q = p.get("quality") or {}
            g = p.get("generation") or {}
            rows.append({
                "passport_id": p["passport_id"], "run_id": p["run_id"], "heritage_id": p["heritage"]["heritage_id"],
                "image": root / latest_design_path(p),
                "intensity_level": (g.get("controlnet") or {}).get("intensity_level", ""),
                "seed": g.get("seed", ""), "layout": (g.get("layout") or {}).get("name", ""),
                "garment_seed": (g.get("garment") or {}).get("seed", ""),
                "g2": (q.get("G2_pattern") or {}).get("decision", ""), "g3": (q.get("G3_final") or {}).get("decision", ""),
                "approval": (p.get("approval") or {}).get("status", ""),
            })
    return sorted(rows, key=lambda r: r["passport_id"])


def plain_name(name: str) -> str:
    """Tên hiện vật hiển thị cho người chấm: bỏ mã bộ dữ liệu ở cuối, giống giao diện web."""
    name = re.sub(r"\s*\(LR3D-CULT2 #\d+\)\s*$", "", name or "")
    name = re.sub(r"^Hiện vật men lam:\s*", "", name)
    return name[:1].upper() + name[1:]


def role_criteria(rubric: dict) -> dict:
    """Tiêu chí hiện cho từng vai (theo trường owner trong bộ tiêu chí)."""
    return {"heritage": [c["key"] for c in rubric["criteria"] if c["owner"] == "heritage"],
            "design": [c["key"] for c in rubric["criteria"] if c["owner"] == "design"],
            "both": [c["key"] for c in rubric["criteria"]]}


def build(out: Path, root: Path = ROOT, designs: list[dict] | None = None) -> dict:
    from api.main import ui_items                                        # noqa: PLC0415

    rubric = json.loads((root / "config" / "expert_rubric.json").read_text(encoding="utf-8"))
    designs = designs if designs is not None else collect(root)
    names = {i["id"]: plain_name(i["name"]) for i in ui_items(include_retired=True)}
    if out.exists():
        shutil.rmtree(out)
    send, keep = out / "GOI_GUI", out / "GIU_RIENG"
    (send / "images").mkdir(parents=True)
    (send / "ref").mkdir()
    keep.mkdir()

    rng = random.Random(SEED)
    # Mỗi ô (hiện vật, mức sáng tạo) có một thiết kế cho mỗi seed; đặt các thiết kế cùng ô liền nhau, seed tăng dần
    designs = sorted(designs, key=lambda d: (d["heritage_id"], str(d["intensity_level"]), str(d["seed"]), d["passport_id"]))
    cell_keys = list(dict.fromkeys((d["heritage_id"], str(d["intensity_level"])) for d in designs))
    cell_ids = {k: f"k{n:02d}" for n, k in zip(rng.sample(range(1, len(cell_keys) + 1), len(cell_keys)), cell_keys)}
    codes = rng.sample(range(1000, 9999), len(designs))
    heritage_ids = sorted({d["heritage_id"] for d in designs})
    ref_names = {}
    for n, hid in enumerate(heritage_ids, start=1):                      # ảnh hiện vật: tách nền, tên trung tính ref_<n>
        src = root / "data" / "heritage" / "cutouts" / f"{hid}.png"
        if not src.exists():
            raise FileNotFoundError(f"thiếu ảnh hiện vật tách nền {src} (chạy scripts/15_cutout_heritage.py)")
        im = Image.open(src).convert("RGBA")
        im = im.resize((max(1, round(im.width * REF_HEIGHT / im.height)), REF_HEIGHT), Image.LANCZOS)
        bg = Image.new("RGBA", im.size, (244, 240, 230, 255))
        bg.alpha_composite(im)
        ref_names[hid] = f"ref_{n}.png"
        bg.convert("RGB").save(send / "ref" / ref_names[hid], optimize=True)

    items, key_rows = [], []
    for code, d in zip(codes, designs):
        name = f"B{code}"
        Image.open(d["image"]).convert("RGB").save(send / "images" / f"{name}.png", optimize=True)   # lưu lại để bỏ siêu dữ liệu
        cell = cell_ids[(d["heritage_id"], str(d["intensity_level"]))]
        items.append({"code": name, "cell": cell, "img": f"images/{name}.png", "ref": f"ref/{ref_names[d['heritage_id']]}",
                      "heritage_ref": d["heritage_id"], "heritage_name": names.get(d["heritage_id"], "")})
        key_rows.append({"code": name, "cell": cell,
                         **{k: d[k] for k in ("passport_id", "run_id", "heritage_id", "intensity_level", "seed", "garment_seed",
                                              "layout", "g2", "g3", "approval")}})
    with (keep / "key.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(key_rows[0]))
        w.writeheader()
        w.writerows(key_rows)

    data = {"items": items, "criteria": rubric["criteria"], "scale": rubric["scale"], "decision": rubric["decision"],
            "roles": role_criteria(rubric)}
    per_rater = len(cell_keys)                                           # mỗi người chấm thấy một thiết kế của mỗi ô
    page = PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__TOTAL__", str(per_rater))
    (send / "index.html").write_text(page, encoding="utf-8")
    (keep / "HUONG_DAN_NOI_BO.md").write_text(INTERNAL_GUIDE.format(total=len(items), per_rater=per_rater, seeds=len({d["seed"] for d in designs})), encoding="utf-8")
    archive = shutil.make_archive(str(out / "GOI_GUI"), "zip", send)
    return {"out": out, "total": len(items), "per_rater": per_rater, "zip": Path(archive), "key": keep / "key.csv"}


INTERNAL_GUIDE = """# Hướng dẫn nội bộ: gửi và thu phiếu chấm mù

Thư mục `GIU_RIENG/` chỉ nhóm giữ. **Không gửi** `key.csv` cho người chấm.

## Gửi
1. Gửi tệp `GOI_GUI.zip` (hoặc cả thư mục `GOI_GUI/`) cho từng người chấm. Họ giải nén và mở `index.html` bằng trình duyệt, không cần mạng.
2. Mỗi người có một mã riêng, **số cuối liên tiếp** (ví dụ `CG01`, `CG02`, `CG03`, `CG04`...). Chọn đúng vai: chuyên gia di sản chấm 2 tiêu chí, chuyên gia thiết kế chấm 3 tiêu chí, người am hiểu cả hai chấm đủ 5.
3. Gói có {total} thiết kế sinh từ {seeds} seed. Một "ô" là một cặp (hiện vật, mức sáng tạo); mỗi ô có một thiết kế cho mỗi seed. **Mỗi người chỉ thấy {per_rater} thiết kế: một thiết kế của mỗi ô**, seed nào thì do trang xoay theo số cuối của mã người chấm. Cứ {seeds} người có mã liên tiếp thì phủ hết mọi seed đúng một lần. Muốn mỗi thiết kế có ít nhất 2 phiếu thì cần ít nhất 2 x {seeds} người chấm.
4. Mục tiêu: ít nhất 1 chuyên gia di sản và 1 chuyên gia thiết kế cho mỗi nhóm seed, tổng cộng từ 30 phiếu trở lên (mỗi thiết kế của một người là một phiếu, một người cho {per_rater} phiếu).
5. Mỗi người mất khoảng 25 đến 35 phút cho {per_rater} thiết kế. Trang tự lưu nháp trong trình duyệt, có thể chấm dở rồi quay lại trên cùng máy.

## Thu
Người chấm bấm "Xuất phiếu (CSV)" và gửi lại tệp `ratings_<mã>.csv`. Cột: `rater_id`, `role`, `code`, `heritage_reference`, 5 cột tiêu chí (bỏ trống tiêu chí không thuộc vai), `decision` (approve, revise, reject), `comment`.

## Giải mã sau khi thu đủ
Ghép phiếu với `key.csv` qua cột `code` để biết mỗi mã là thiết kế nào, mức sáng tạo nào, seed nào (cột `seed`, `run_id`, `cell`), cổng G2 và G3 báo gì. Việc cần làm với kết quả:
- Đo độ ổn định theo seed: so điểm của các thiết kế cùng ô (`cell`) nhưng khác `seed`. Lưu ý mỗi người chỉ chấm một seed của mỗi ô, nên chênh lệch giữa seed lẫn với chênh lệch giữa người chấm; chỉ kết luận khi có nhiều người chấm cho mỗi seed.
- So quyết định của chuyên gia với kết quả cổng (đồng thuận giữa người và cổng tự động), từ đó hiệu chỉnh ngưỡng trong `config/quality_gate.json` (xem `docs/finals/05_QUALITY_ASSURANCE.md`).
- Tính quy tắc "Đạt" của bộ tiêu chí: không tiêu chí nào dưới 3 và "Phù hợp văn hoá" từ 4.
- Ghi phiếu vào Passport qua `POST /passports/<id>/reviews` nếu muốn lưu thẩm định chính thức.

Chưa có công cụ tự động tổng hợp phiếu. Cần thì làm thêm.

## Lưu ý để giữ tính "mù"
- Người chấm chỉ thấy mã ảnh, tên hiện vật và ảnh hiện vật. Không nói trước thiết kế nào do mức sáng tạo nào, thiết kế nào bị cổng loại.
- Gói có cả thiết kế mà cổng chất lượng đã loại, nhằm đo xem chuyên gia có đồng ý với cổng không. Đừng loại chúng ra khỏi gói.
- Thứ tự thiết kế xáo riêng theo mã người chấm, nên hai người thấy hai thứ tự khác nhau.
- Đừng nói với người chấm rằng gói có nhiều seed, và đừng gửi cùng một người hai mã khác nhau (sẽ thấy cả hai seed của một ô).
"""

PAGE = """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Phiếu chấm thiết kế áo dài</title>
<style>
:root { --paper:#F4F0E6; --card:#FBF8F1; --ink:#1D2A36; --ink3:#5C6770; --gold:#D4B47A; --line:#D9D2C2; --lam:#1E3F7A; }
* { box-sizing: border-box; }
[hidden] { display: none !important; }
body { margin:0; background:var(--paper); color:var(--ink); font:16px/1.55 "Noto Serif", "Times New Roman", Cambria, "Segoe UI", serif; }
header, main, .bar { max-width: 960px; margin: 0 auto; padding: 0 20px; }
h1 { font-weight: 500; font-size: 28px; margin: 28px 0 8px; }
h2 { font-weight: 500; font-size: 19px; margin: 22px 0 6px; }
p, li { color: var(--ink3); }
ul { padding-left: 20px; }
.panel { background:var(--card); border:1px solid var(--line); padding:18px 20px; margin:16px 0; }
label { display:block; font-weight:600; margin:10px 0 4px; color:var(--ink); }
input[type=text], select, textarea { width:100%; padding:9px 11px; font:inherit; border:1px solid var(--line); background:#fff; color:var(--ink); }
button { font:inherit; font-weight:600; letter-spacing:.06em; text-transform:uppercase; font-size:13px; padding:12px 22px; border:1px solid transparent; background:var(--gold); color:var(--ink); cursor:pointer; }
button.ghost { background:transparent; border-color:var(--ink3); }
button:disabled { opacity:.5; cursor:default; }
.card { background:var(--card); border:1px solid var(--line); margin:18px 0; padding:18px 20px; }
.card h3 { margin:0 0 12px; font-weight:500; font-size:18px; }
.pair { display:grid; grid-template-columns: minmax(0,1fr) minmax(0,2fr); gap:18px; align-items:start; }
.pair figure { margin:0; text-align:center; }
.pair img { max-width:100%; max-height:520px; display:block; margin:0 auto; cursor:zoom-in; }
.pair figcaption { font-size:14px; color:var(--ink3); margin-top:6px; }
.crit { margin:16px 0 4px; }
.crit .q { font-weight:600; }
.crit .hint { font-size:14px; color:var(--ink3); }
.scale { display:flex; gap:8px; margin-top:6px; flex-wrap:wrap; }
.scale label { display:flex; align-items:center; gap:6px; margin:0; font-weight:400; padding:6px 12px; border:1px solid var(--line); background:#fff; cursor:pointer; }
.scale input:checked + span { font-weight:700; }
.scale label:has(input:checked) { border-color:var(--ink); background:#EFE7D6; }
.end { display:flex; justify-content:space-between; font-size:13px; color:var(--ink3); max-width:460px; }
.bar { position:sticky; bottom:0; background:var(--paper); border-top:1px solid var(--line); padding-top:12px; padding-bottom:12px; display:flex; gap:16px; align-items:center; flex-wrap:wrap; }
.progress { flex:1; min-width:180px; }
.progress div { height:8px; background:#E4DDCD; } .progress span { display:block; height:100%; background:var(--lam); width:0; transition:width .3s; }
#zoom { position:fixed; inset:0; background:rgba(8,21,42,.85); display:none; place-items:center; z-index:9; cursor:zoom-out; }
#zoom img { max-width:92vw; max-height:92vh; }
@media (max-width: 640px) { .pair { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<header>
  <h1>Phiếu chấm thiết kế áo dài từ hoa văn gốm Bát Tràng</h1>
  <p>Cảm ơn bạn đã dành thời gian. Bạn sẽ xem __TOTAL__ thiết kế áo dài do trí tuệ nhân tạo tạo ra từ hoa văn trên gốm Bát Tràng, mỗi thiết kế đi kèm ảnh hiện vật gốm làm nguồn. Bạn chấm điểm từng thiết kế theo vài tiêu chí. Khoảng 25 đến 35 phút.</p>
  <div class="panel">
    <h2>Cách chấm</h2>
    <ul>
      <li>Thang điểm 1 đến 5: <span id="scale-text"></span>.</li>
      <li>Bạn không được cho biết thiết kế nào tạo ra bằng cách nào. Hãy chấm theo những gì bạn thấy, không đoán. Mỗi thiết kế chấm độc lập, không so với thiết kế khác.</li>
      <li>Chỉ chấm các tiêu chí thuộc chuyên môn của bạn (theo vai bạn chọn bên dưới). Không chắc thì chọn điểm thấp nhất phù hợp và ghi lý do vào ô nhận xét.</li>
      <li>Quyết định cuối cho mỗi thiết kế: Đạt, Cần chỉnh sửa, hoặc Loại. Nên ghi lý do nếu chọn Cần chỉnh sửa hoặc Loại.</li>
      <li>Trang tự lưu nháp trên máy này. Chấm xong bấm "Xuất phiếu (CSV)" ở thanh dưới cùng và gửi tệp lại cho nhóm.</li>
    </ul>
  </div>
  <div class="panel" id="setup">
    <label for="rater">Mã người chấm (nhóm đã cấp cho bạn, ví dụ CG01)</label>
    <input type="text" id="rater" autocomplete="off" placeholder="CG01">
    <label for="role">Vai của bạn</label>
    <select id="role">
      <option value="heritage">Chuyên gia di sản (chấm 2 tiêu chí)</option>
      <option value="design">Chuyên gia thiết kế (chấm 3 tiêu chí)</option>
      <option value="both">Am hiểu cả hai (chấm đủ 5 tiêu chí)</option>
    </select>
    <p id="err" style="color:#9C2B2B;display:none"></p>
    <p><button id="start">Bắt đầu chấm</button></p>
  </div>
</header>
<main id="cards" hidden></main>
<div class="bar" id="bar" hidden>
  <div class="progress"><div><span id="pbar"></span></div><small id="ptext"></small></div>
  <button class="ghost" id="export">Xuất phiếu (CSV)</button>
</div>
<div id="zoom"><img alt=""></div>
<script>
const DATA = __DATA__;
const $ = (s) => document.querySelector(s);
const state = { rater: '', role: 'heritage', order: [], answers: {} };

document.getElementById('scale-text').textContent = Object.entries(DATA.scale.labels).map(([k, v]) => k + ' = ' + v).join(', ');

// Xáo thứ tự riêng cho từng người chấm: cùng mã người chấm thì luôn ra cùng thứ tự
function seedFrom(text) { let h = 1779033703; for (const c of text) { h = Math.imul(h ^ c.charCodeAt(0), 3432918353); h = (h << 13) | (h >>> 19); } return h >>> 0; }
function rng(seed) { return () => { seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
function shuffled(list, seed) { const a = list.slice(), r = rng(seed); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }

// --- chọn thiết kế cho người chấm: mỗi ô (cell) một thiết kế, seed xoay theo số cuối của mã ---
function raterShift(id) { const m = id.match(/(\\d+)$/); return m ? parseInt(m[1], 10) : seedFrom(id); }
function pickForRater(items, id) {
  const cells = [], groups = {};
  for (const it of items) { if (!groups[it.cell]) { groups[it.cell] = []; cells.push(it.cell); } groups[it.cell].push(it); }
  const shift = raterShift(id);
  return cells.map((c, i) => groups[c][(shift + i) % groups[c].length]);
}
// --- hết khối chọn thiết kế ---

const storeKey = () => 'phieu-cham-' + state.rater;
function load() { try { return JSON.parse(localStorage.getItem(storeKey()) || '{}'); } catch { return {}; } }
function save() { try { localStorage.setItem(storeKey(), JSON.stringify({ role: state.role, answers: state.answers })); } catch { /* trình duyệt chặn lưu: vẫn chấm được */ } }

const needed = () => DATA.criteria.filter((c) => DATA.roles[state.role].includes(c.key));
const isDone = (code) => { const a = state.answers[code] || {}; return needed().every((c) => a[c.key]) && a.decision; };

function progress() {
  const done = state.order.filter((it) => isDone(it.code)).length;
  $('#ptext').textContent = 'Đã chấm ' + done + ' / ' + state.order.length + ' thiết kế';
  $('#pbar').style.width = (100 * done / state.order.length) + '%';
}

function el(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) { if (k === 'class') e.className = v; else if (k.startsWith('on')) e.addEventListener(k.slice(2), v); else e.setAttribute(k, v); }
  for (const kid of kids) e.append(kid);
  return e;
}

function radios(code, key, options) {
  const wrap = el('div', { class: 'scale' });
  for (const [value, label] of options) {
    const input = el('input', { type: 'radio', name: code + '-' + key, value });
    if ((state.answers[code] || {})[key] === value) input.checked = true;
    input.addEventListener('change', () => { (state.answers[code] = state.answers[code] || {})[key] = value; save(); progress(); });
    wrap.append(el('label', {}, input, el('span', {}, label)));
  }
  return wrap;
}

function card(it, n) {
  const c = el('section', { class: 'card' }, el('h3', {}, 'Thiết kế ' + n + ' / ' + state.order.length));
  const zoomable = (src, alt) => el('img', { src, alt, onclick: () => { $('#zoom img').src = src; $('#zoom').style.display = 'grid'; } });
  c.append(el('div', { class: 'pair' },
    el('figure', {}, zoomable(it.ref, 'Hiện vật ' + it.heritage_name), el('figcaption', {}, 'Hiện vật gốm: ' + it.heritage_name)),
    el('figure', {}, zoomable(it.img, 'Thiết kế áo dài'), el('figcaption', {}, 'Thiết kế áo dài (bấm vào ảnh để phóng to)'))));
  const scale = Object.entries(DATA.scale.labels).map(([k, v]) => [k, k + ' ' + v]);
  for (const crit of needed()) {
    c.append(el('div', { class: 'crit' }, el('div', { class: 'q' }, crit.label), el('div', { class: 'hint' }, crit.question), radios(it.code, crit.key, scale)));
  }
  c.append(el('div', { class: 'crit' }, el('div', { class: 'q' }, 'Quyết định cho thiết kế này'),
    radios(it.code, 'decision', Object.entries(DATA.decision).map(([k, v]) => [k, v]))));
  const note = el('textarea', { rows: '2', placeholder: 'Nhận xét hoặc lý do (không bắt buộc)' });
  note.value = (state.answers[it.code] || {}).comment || '';
  note.addEventListener('input', () => { (state.answers[it.code] = state.answers[it.code] || {}).comment = note.value; save(); });
  c.append(el('div', { class: 'crit' }, el('div', { class: 'q' }, 'Nhận xét'), note));
  return c;
}

function csvCell(v) { v = (v == null ? '' : String(v)); return /[",\\n\\r]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }
function exportCsv() {
  const keys = DATA.criteria.map((c) => c.key);
  const rows = [['rater_id', 'role', 'code', 'heritage_reference', ...keys, 'decision', 'comment']];
  for (const it of state.order) {
    const a = state.answers[it.code] || {};
    rows.push([state.rater, state.role, it.code, it.heritage_ref, ...keys.map((k) => a[k] || ''), a.decision || '', a.comment || '']);
  }
  const text = '\\ufeff' + rows.map((r) => r.map(csvCell).join(',')).join('\\r\\n');
  const a = el('a', { href: URL.createObjectURL(new Blob([text], { type: 'text/csv;charset=utf-8' })), download: 'ratings_' + state.rater + '.csv' });
  document.body.append(a); a.click(); a.remove();
  const done = state.order.filter((it) => isDone(it.code)).length;
  if (done < state.order.length) alert('Đã xuất phiếu. Còn ' + (state.order.length - done) + ' thiết kế chưa chấm đủ, các ô trống sẽ để trống trong tệp.');
}

$('#start').addEventListener('click', () => {
  const id = $('#rater').value.trim();
  const err = $('#err');
  if (!/^[A-Za-z0-9_-]{2,20}$/.test(id)) { err.textContent = 'Mã người chấm gồm 2 đến 20 chữ cái, chữ số, gạch dưới hoặc gạch nối.'; err.style.display = 'block'; return; }
  err.style.display = 'none';
  state.rater = id;
  const saved = load();
  state.role = saved.role || $('#role').value;
  state.answers = saved.answers || {};
  $('#role').value = state.role;
  state.order = shuffled(pickForRater(DATA.items, id), seedFrom(id));
  const main = $('#cards');
  main.replaceChildren(...state.order.map((it, i) => card(it, i + 1)));
  main.hidden = false; $('#bar').hidden = false; $('#setup').querySelectorAll('input,select,button').forEach((e) => { e.disabled = true; });
  progress();
  main.scrollIntoView();
});
$('#export').addEventListener('click', exportCsv);
$('#zoom').addEventListener('click', () => { $('#zoom').style.display = 'none'; });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') $('#zoom').style.display = 'none'; });
</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "outputs" / "blind_review"))
    args = ap.parse_args()
    r = build(Path(args.out))
    print(f"Đã dựng gói chấm mù {r['total']} thiết kế tại {r['out']}\n  gửi người chấm: {r['zip']}\n  nhóm giữ riêng: {r['key']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
