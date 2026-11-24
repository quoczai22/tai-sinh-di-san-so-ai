"""Dựng gói tạo Google Form chấm mù cho một thí nghiệm (mặc định EXP-A).

Google Form không cho nhúng ảnh qua tệp, nên gói này gồm:
  images/        mỗi thiết kế một ảnh ghép, tên mã ngẫu nhiên (B1234.jpg). Ảnh ghép đi theo chuỗi:
                 mảng hoa văn ép phẳng (đầu vào)  ->  hoa văn AI sinh ra  ->  áo dài kết quả. Ảnh bình gốm đi kèm
                 chỉ là hiện vật tham chiếu (khung nét đứt, không nối mũi tên), không phải đầu vào.
  Code.gs        mã Google Apps Script: đọc ảnh từ thư mục Drive rồi TỰ TẠO các Google Form (mỗi bản một form).
  key.csv        khóa giải mã (mã ảnh -> hiện vật, trọng số, seed, bản form). CHỈ NHÓM GIỮ, đừng gửi người chấm.
  form_spec.json nội dung đã nhúng trong Code.gs (để kiểm tra).
  HUONG_DAN.md   các bước đưa lên Google và thu kết quả.

Mặc định dựng MỘT form chứa mọi thiết kế của mọi seed đã chọn (mỗi ô hiện vật x giá trị biến độc lập có một thiết kế
cho mỗi seed), thứ tự xáo ngẫu nhiên cố định. Cả nhóm điền chung một link.
Với --rotate thì chia thành nhiều "bản" (A, B, C...): mỗi bản một thiết kế cho mỗi ô, seed xoay theo bản; số bản mặc định
bằng số seed, nên mọi thiết kế xuất hiện đúng một lần trong một bản. Mỗi người chỉ nhận MỘT link, không biết có bản khác.

    uv run python scripts/eval/build_google_form.py                       # EXP-A, seed 42 và 7: 1 form, 48 ảnh
    uv run python scripts/eval/build_google_form.py --seeds 42,7,123      # thêm seed: thêm 24 ảnh vào form
    uv run python scripts/eval/build_google_form.py --rotate              # nhiều form, mỗi form 24 ảnh
    uv run python scripts/eval/build_google_form.py --audience expert --single   # MỘT phiếu cho MỘT người, đủ tiêu chí, không có quyết định
    uv run python scripts/eval/build_google_form.py --audience expert     # phiếu chuyên gia: 12 ảnh (seed 42, trọng số 0.85 và 0.25),
                                                                          # hai form (di sản, thiết kế), có quyết định và nhận xét,
                                                                          # kèm 2 file Word trong docx/ (build_expert_docx.py)
    uv run python scripts/eval/build_google_form.py --out thư_mục

Ảnh nằm trong outputs/ (đã bỏ qua khỏi git) vì là dữ liệu thô.
"""
import argparse
import csv
import importlib.util
import json
import random
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SEED = 20261122                       # seed gán mã ảnh và thứ tự, cố định để dựng lại ra cùng một gói
FONT_CANDIDATES = ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/Library/Fonts/Arial.ttf"]
FONT_BOLD_CANDIDATES = ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf",
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/Library/Fonts/Arial Bold.ttf"]
SCALE_LABELS = ["1 - Rất kém", "2 - Kém", "3 - Chấp nhận được", "4 - Tốt", "5 - Rất tốt"]
ROLES = ["Làm trong lĩnh vực di sản, bảo tàng, gốm sứ", "Làm trong lĩnh vực thiết kế, thời trang",
         "Người quan tâm, không làm chuyên môn"]


def load_blind_review():
    """Nạp scripts/eval/build_blind_review.py để dùng lại cách đọc results.csv của thí nghiệm."""
    spec = importlib.util.spec_from_file_location("blind_review", ROOT / "scripts" / "eval" / "build_blind_review.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT))
    spec.loader.exec_module(mod)
    return mod


def pattern_path(final_image: Path) -> Path:
    """Ảnh ô hoa văn AI sinh ra, nằm cạnh ảnh áo cuối (đuôi __final.png đổi thành __pattern.png)."""
    if not final_image.name.endswith("__final.png"):
        raise ValueError(f"tên ảnh áo không có đuôi __final.png, không suy ra được ảnh hoa văn: {final_image}")
    return final_image.with_name(final_image.name[: -len("__final.png")] + "__pattern.png")


def pick_for_version(designs: list[dict], version: int) -> list[dict]:
    """Chọn một thiết kế cho mỗi ô. Mỗi ô có độ lệch seed ngẫu nhiên cố định, bản v lấy seed thứ (lệch + v).

    Độ lệch ngẫu nhiên (không dùng số thứ tự ô) để seed không gắn chặt với chẵn lẻ của giá trị biến độc lập.
    Số bản không được vượt số seed của ô, không thì một thiết kế lặp ở nhiều bản và có ô thiếu thiết kế."""
    groups: dict[tuple, list[dict]] = {}
    for d in sorted(designs, key=lambda d: (d["heritage_id"], str(d["intensity_level"]), int(d["seed"]))):
        groups.setdefault((d["heritage_id"], str(d["intensity_level"])), []).append(d)
    rng = random.Random(SEED)
    picks = []
    for cell, g in groups.items():
        offset = rng.randrange(len(g))
        if version >= len(g):
            raise ValueError(f"ô {cell} chỉ có {len(g)} seed hoàn tất, không đủ cho bản thứ {version + 1}")
        picks.append(g[(offset + version) % len(g)])
    return picks


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for p in (FONT_BOLD_CANDIDATES if bold else FONT_CANDIDATES):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    raise FileNotFoundError("không tìm thấy phông Arial hoặc DejaVu để vẽ chữ tiếng Việt lên ảnh ghép")


def fit(im: Image.Image, w: int, h: int) -> Image.Image:
    """Co ảnh vừa khung w x h, giữ tỉ lệ."""
    s = min(w / im.width, h / im.height)
    return im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)


def label(draw: ImageDraw.ImageDraw, xy: tuple, text: str, width: int) -> None:
    """Vẽ nhãn in đậm, tự giảm cỡ chữ cho vừa bề rộng."""
    size = 26
    while size > 14 and get_font(size, True).getlength(text) > width:
        size -= 1
    draw.text(xy, text, font=get_font(size, True), fill=(29, 42, 54))


def compose(vessel: Path, panel: Path, pattern: Path, final: Path) -> Image.Image:
    """Ảnh ghép một thiết kế: hàng trên là đầu vào (hiện vật, mảng phẳng), hàng dưới là hoa văn sinh ra và áo dài."""
    W, M, TW, G = 1200, 40, 540, 40
    bg, box = (251, 248, 241), (244, 240, 230)
    canvas = Image.new("RGB", (W, 1300), bg)
    d = ImageDraw.Draw(canvas)
    xl, xr = M, M + TW + G                                         # cột trái, cột phải

    def tile(im: Image.Image, x: int, y: int, h: int) -> None:
        d.rectangle([x, y, x + TW, y + h], fill=box)
        im = fit(im, TW - 8, h - 8)
        canvas.paste(im, (x + (TW - im.width) // 2, y + (h - im.height) // 2), im if im.mode == "RGBA" else None)

    label(d, (xl, 30), "Đầu vào: mảng hoa văn đã ép phẳng", TW)
    label(d, (xr, 30), "Tham chiếu: Hiện vật gốm", TW)
    tile(Image.open(panel).convert("RGBA"), xl, 76, 420)            # mảng phẳng có vùng trong suốt: phải giữ alpha, không thì nền ra đen
    tile(Image.open(vessel).convert("RGBA"), xr, 76, 420)
    for x in range(xr, xr + TW, 24):                                # khung nét đứt quanh bình: chỉ để đối chiếu, không nối mũi tên
        for y in (76, 496):
            d.line([(x, y), (min(x + 12, xr + TW), y)], fill=(120, 120, 120), width=2)
    for y in range(76, 496, 24):
        for x in (xr, xr + TW):
            d.line([(x, y), (x, min(y + 12, 496))], fill=(120, 120, 120), width=2)
    d.polygon([(xl + TW // 2 - 40, 510), (xl + TW // 2 + 40, 510), (xl + TW // 2, 570)], fill=(30, 63, 122))    # mũi tên xuống
    d.text((xl + TW // 2 + 60, 524), "AI sinh ra", font=get_font(24, True), fill=(30, 63, 122))
    label(d, (xl, 586), "Hoa văn do AI sinh", TW)
    label(d, (xr, 586), "Kết quả: Áo dài do AI sinh", TW)
    tile(Image.open(pattern).convert("RGB"), xl, 632, 640)
    tile(Image.open(final).convert("RGB"), xr, 632, 640)
    d.polygon([(xl + TW + 2, 920), (xl + TW + 2, 980), (xr - 2, 950)], fill=(30, 63, 122))                      # mũi tên phải
    return canvas


def build(exp_dir: Path, out: Path, seeds: list[int], versions: int | None = None, root: Path = ROOT,
          one_form: bool = False, per_page: int | None = None, audience: str = "community",
          levels: list[float] | None = None, single: bool = False) -> dict:
    """Dựng gói. one_form=True: MỘT form chứa mọi thiết kế của mọi seed đã chọn (mỗi người chấm hết).
    one_form=False: nhiều form, mỗi form một thiết kế cho mỗi ô, seed xoay theo form.
    per_page: số thiết kế mỗi trang của form (0 = cả form một trang; mặc định 4 cho cộng đồng, 2 cho chuyên gia).
    levels: chỉ giữ các giá trị biến độc lập này (ví dụ trọng số 0.85 và 0.25), None = giữ hết.
    audience="expert": hai form dùng chung ảnh, một cho chuyên gia di sản và một cho chuyên gia thiết kế; mỗi form chỉ hiện
    tiêu chí thuộc vai, kèm quyết định Đạt/Cần chỉnh sửa/Loại, ô nhận xét và thông tin người thẩm định.
    single=True (chỉ với expert): MỘT phiếu cho MỘT người, chấm đủ mọi tiêu chí, không có hàng quyết định Đạt/Loại."""
    if audience not in ("community", "expert"):
        raise ValueError("audience phải là community hoặc expert")
    expert = audience == "expert"
    if single and not expert:
        raise ValueError("single chỉ dùng với audience=expert")
    if per_page is None:
        per_page = 2 if expert else 4
    if per_page < 0:
        raise ValueError("per_page không được âm")
    br = load_blind_review()
    designs, criteria_keys = br.collect_experiment(exp_dir, seeds)
    if levels:
        designs = [d for d in designs if float(d["intensity_level"]) in {float(x) for x in levels}]
    if not designs:
        raise ValueError(f"{exp_dir}: không có thiết kế nào thuộc các seed {seeds} và mức {levels}")
    rubric = json.loads((root / "config" / "expert_rubric.json").read_text(encoding="utf-8"))
    criteria = [c for c in rubric["criteria"] if c["key"] in criteria_keys]
    if not criteria:
        raise ValueError(f"không tiêu chí nào trong {criteria_keys} có trong config/expert_rubric.json")

    if expert:                                                              # mỗi vai một form, cùng một danh sách thiết kế
        by_role = br.role_criteria({"criteria": criteria})
        if single:                                                          # một người chấm đủ mọi tiêu chí
            roles = [("both", None, criteria)]
        else:
            roles = [(r, lbl, [c for c in criteria if c["key"] in by_role[r]]) for r, lbl in (("heritage", "di sản"), ("design", "thiết kế"))]
            roles = [x for x in roles if x[2]]
        picks = [list(designs) for _ in roles]
        versions = len(roles)
    else:
        roles = [(None, None, criteria)] * (1 if one_form else (versions or len({d["seed"] for d in designs})))
        picks = [list(designs)] if one_form else [pick_for_version(designs, v) for v in range(len(roles))]
        versions = len(roles)
    if versions > 26:
        raise ValueError("tối đa 26 bản (đặt tên A đến Z)")
    used = {d["passport_id"]: d for p in picks for d in p}                 # chỉ dựng ảnh cho thiết kế có dùng
    sources = {}                                                           # kiểm đủ ảnh đầu vào trước khi xóa thư mục đích
    for pid, d in used.items():
        hid = d["heritage_id"]
        sources[pid] = (root / "data" / "heritage" / "panels" / f"{hid}.png", root / "data" / "heritage" / "cutouts" / f"{hid}.png",
                        pattern_path(Path(d["image"])), Path(d["image"]))
    missing = sorted({str(p) for s in sources.values() for p in s if not p.exists()})
    if missing:
        raise FileNotFoundError("thiếu ảnh nguồn: " + ", ".join(missing))

    if out.exists():
        if any(out.iterdir()) and not (out / "Code.gs").exists():          # chỉ xóa thư mục do chính công cụ này dựng
            raise ValueError(f"{out} không rỗng và không phải gói Google Form cũ, từ chối xóa. Chọn --out khác.")
        shutil.rmtree(out)
    (out / "images").mkdir(parents=True)

    rng = random.Random(SEED)
    codes = dict(zip(sorted(used), rng.sample(range(1000, 9999), len(used))))
    for pid, (panel, vessel, pattern, final) in sources.items():
        img = compose(vessel, panel, pattern, final)
        img.save(out / "images" / f"B{codes[pid]}.jpg", quality=88, optimize=True)   # lưu mới nên không mang siêu dữ liệu

    n_items = len(picks[0])
    minutes = max(10, round(n_items * (1.6 if expert else 0.9)))           # chuyên gia còn viết nhận xét nên lâu hơn
    spec_versions, key_rows = [], []
    for v, pick in enumerate(picks):
        name = chr(ord("A") + v)
        role, role_label, role_criteria_ = roles[v]
        order = random.Random(SEED + v + 1).sample(pick, len(pick))        # thứ tự xáo riêng từng bản
        items = []
        for d in order:
            code = f"B{codes[d['passport_id']]}"
            items.append({"code": code, "file": f"{code}.jpg"})
            key_rows.append({"version": name, "role": role or "", "position": len(items), "code": code, "heritage_id": d["heritage_id"],
                             "controlnet_weight": d["intensity_level"], "seed": d["seed"], "run_key": d["passport_id"]})
        spec_versions.append({
            "name": name, "label": ("chuyên gia" + (f" {role_label}" if role_label else "")) if expert else f"bản {name}", "items": items,
            "criteria": role_criteria_, "criteriaHelp": "\n".join(f"• {c['label']}: {c['question']}" for c in role_criteria_),
            "intro": (EXPERT_SINGLE_INTRO if single else EXPERT_INTRO if expert else COMMUNITY_INTRO).format(
                n=n_items, minutes=minutes, role=role_label or ""),
        })

    spec = {
        "mode": audience,
        "title": ("Phiếu thẩm định chuyên gia: thiết kế áo dài từ hoa văn gốm Bát Tràng" if expert
                  else "Phiếu chấm thiết kế áo dài từ hoa văn gốm Bát Tràng"),
        "intro": spec_versions[0]["intro"],
        "roleQuestion": "Bạn là", "roles": ROLES, "criteria": criteria, "criteriaHelp": spec_versions[0]["criteriaHelp"],
        "scale": SCALE_LABELS, "imageWidth": 740, "perPage": per_page, "versions": spec_versions,
        "thanks": "Cảm ơn bạn đã thẩm định. Nhóm sẽ dùng nhận xét để cải tiến." if expert else "Cảm ơn bạn đã chấm. Phiếu đã được ghi nhận.",
    }
    if expert:
        spec.update({"profile": EXPERT_PROFILE, "decisions": [] if single else DECISIONS, "closing": EXPERT_CLOSING,
                     "commentHelp": SINGLE_COMMENT_HELP if single else COMMENT_HELP})
    (out / "form_spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "Code.gs").write_text(APPS_SCRIPT.replace("__SPEC__", json.dumps(spec, ensure_ascii=False, indent=2)), encoding="utf-8")
    with (out / "key.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(key_rows[0]))
        w.writeheader()
        w.writerows(key_rows)
    share = SHARE_EXPERT_SINGLE if single else SHARE_EXPERT if expert else (SHARE_ONE if versions == 1 else SHARE_MANY)
    (out / "HUONG_DAN.md").write_text(GUIDE.format(n_images=len(used), n_versions=versions, per=n_items, minutes=minutes, share=share),
                                      encoding="utf-8")
    return {"out": out, "images": len(used), "versions": versions, "per_version": n_items, "spec": spec}


# Lời mở đầu form. {n} số thiết kế, {minutes} số phút, {role} vai chuyên gia (chỉ bản chuyên gia dùng)
COMMUNITY_INTRO = ("Cảm ơn bạn đã tham gia. Bạn sẽ xem {n} thiết kế áo dài do trí tuệ nhân tạo (AI) tạo ra từ hoa văn trên gốm Bát Tràng. "
                   "Mỗi thiết kế là một ảnh gồm 3 phần theo chuỗi: (1) đầu vào là mảng hoa văn đã ép phẳng từ hiện vật gốm, "
                   "(2) hoa văn do AI sinh ra từ mảng đó, (3) áo dài kết quả. Ảnh hiện vật gốm đi kèm chỉ để bạn đối chiếu, AI không dùng nó làm đầu vào. "
                   "Bạn chấm điểm từng thiết kế theo các tiêu chí, thang 1 đến 5. "
                   "Mất khoảng {minutes} phút. Chấm theo những gì bạn thấy, mỗi thiết kế chấm độc lập, không cần so với thiết kế khác. "
                   "Biểu mẫu không thu tên hay email.")
EXPERT_INTRO = ("Cảm ơn bạn đã nhận thẩm định. Phiếu này dành cho chuyên gia {role}. Bạn sẽ xem {n} thiết kế áo dài do trí tuệ nhân tạo (AI) "
                "tạo ra từ hoa văn trên gốm Bát Tràng. Mỗi thiết kế là một ảnh gồm 3 phần theo chuỗi: (1) đầu vào là mảng hoa văn đã ép phẳng "
                "từ hiện vật gốm, (2) hoa văn do AI sinh ra từ mảng đó, (3) áo dài kết quả. Ảnh hiện vật gốm đi kèm chỉ để bạn đối chiếu, "
                "AI không dùng nó làm đầu vào. Với mỗi thiết kế, bạn chấm các tiêu chí thuộc chuyên môn của bạn (thang 1 đến 5), "
                "chọn quyết định Đạt, Cần chỉnh sửa hoặc Loại, và ghi nhận xét. Mất khoảng {minutes} phút. "
                "Biểu mẫu có thu họ tên, đơn vị và email để nhóm ghi nhận người thẩm định; bạn chọn có đồng ý ghi tên trong hồ sơ hay không.")
EXPERT_SINGLE_INTRO = ("Cảm ơn bạn đã nhận thẩm định. Bạn sẽ xem {n} thiết kế áo dài do trí tuệ nhân tạo (AI) tạo ra từ hoa văn trên gốm "
                       "Bát Tràng. Mỗi thiết kế là một ảnh gồm 3 phần theo chuỗi: (1) đầu vào là mảng hoa văn đã ép phẳng từ hiện vật gốm, "
                       "(2) hoa văn do AI sinh ra từ mảng đó, (3) áo dài kết quả. Ảnh hiện vật gốm đi kèm chỉ để bạn đối chiếu, "
                       "AI không dùng nó làm đầu vào. Với mỗi thiết kế, bạn chấm các tiêu chí (thang 1 đến 5) và ghi nhận xét. "
                       "Bạn không cần quyết định giữ hay loại thiết kế. Mất khoảng {minutes} phút. "
                       "Biểu mẫu có thu họ tên, đơn vị và email để nhóm ghi nhận người thẩm định; bạn chọn có đồng ý ghi tên trong hồ sơ hay không.")
COMMENT_HELP = "Ghi rõ lý do nếu chọn Cần chỉnh sửa hoặc Loại: họa tiết nào sai, đặt sai chỗ, hoặc cần làm lại bước nào."
SINGLE_COMMENT_HELP = "Ghi nhận xét của bạn: họa tiết nào đúng hoặc sai so với hiện vật, đặt sai chỗ, hoặc chỗ nào cần cải thiện."
# Thông tin người thẩm định (chỉ bản chuyên gia). type: text hoặc choice
EXPERT_PROFILE = [
    {"title": "Họ và tên", "type": "text", "required": True},
    {"title": "Đơn vị và chức danh", "type": "text", "required": True},
    {"title": "Email liên hệ (không bắt buộc)", "type": "text", "required": False},
    {"title": "Bạn có đồng ý để nhóm ghi họ tên và chức danh trong hồ sơ dự thi không?", "type": "choice", "required": True,
     "choices": ["Đồng ý ghi họ tên và chức danh", "Chỉ dùng nhận xét, không công bố tên"]},
]
DECISIONS = ["Đạt", "Cần chỉnh sửa (ghi lý do ở ô nhận xét)", "Loại (ghi lý do ở ô nhận xét)"]
EXPERT_CLOSING = ["Biểu tượng hoặc họa tiết nào không nên dùng hoặc không nên đặt ở vị trí đó trên áo dài? Vì sao? (không bắt buộc)",
                  "Góp ý chung cho nhóm (không bắt buộc)"]


APPS_SCRIPT = """// Tạo Google Form chấm mù từ ảnh đã tải lên Drive. Sinh tự động bởi scripts/eval/build_google_form.py.
// Cách dùng: dán ID thư mục Drive chứa ảnh vào FOLDER_ID, chọn hàm createForms rồi bấm Chạy.

// ID thư mục Drive chứa các ảnh B*.jpg (phần cuối của link thư mục: drive.google.com/drive/folders/<ID>)
const FOLDER_ID = 'DAN_ID_THU_MUC_VAO_DAY';

// Để trống = tạo mọi bản. Nếu lần chạy trước hết giờ giữa chừng, xóa form dở rồi đặt tên bản cần tạo lại ở đây, ví dụ 'B'.
const ONLY_VERSION = '';

// Nội dung form (câu hỏi, thang điểm, thứ tự ảnh từng bản)
const SPEC = __SPEC__;

function createForms() {
  if (FOLDER_ID.indexOf('DAN_ID') === 0) throw new Error('Chưa dán FOLDER_ID ở đầu tệp.');
  const files = {};
  const it = DriveApp.getFolderById(FOLDER_ID).getFiles();
  while (it.hasNext()) { const f = it.next(); files[f.getName()] = f; }

  // Kiểm tra đủ ảnh trước khi tạo, để khỏi tạo form dở dang
  const missing = [];
  SPEC.versions.forEach(function (v) { v.items.forEach(function (x) { if (!files[x.file]) missing.push(x.file); }); });
  if (missing.length) throw new Error('Thiếu ảnh trong thư mục Drive: ' + missing.join(', '));

  SPEC.versions.forEach(function (v) {
    if (ONLY_VERSION && v.name !== ONLY_VERSION) return;
    const form = buildForm(v, files);
    Logger.log('Bản %s | gửi người chấm: %s | sửa: %s', v.name, form.getPublishedUrl(), form.getEditUrl());
  });
}

function buildForm(v, files) {
  const form = FormApp.create(SPEC.title);                                   // tiêu đề người chấm thấy: không ghi bản nào
  DriveApp.getFileById(form.getId()).setName(SPEC.title + ' [' + v.label + ']');   // chỉ tên tệp trong Drive của bạn mang tên bản
  form.setDescription(v.intro);
  form.setProgressBar(true);
  form.setCollectEmail(false);
  form.setShowLinkToRespondAgain(false);
  form.setConfirmationMessage(SPEC.thanks);

  if (SPEC.mode === 'expert') {
    // Thông tin người thẩm định: văn bản ngắn hoặc trắc nghiệm
    SPEC.profile.forEach(function (q) {
      if (q.type === 'choice') form.addMultipleChoiceItem().setTitle(q.title).setChoiceValues(q.choices).setRequired(q.required);
      else form.addTextItem().setTitle(q.title).setRequired(q.required);
    });
  } else {
    form.addMultipleChoiceItem().setTitle(SPEC.roleQuestion).setChoiceValues(SPEC.roles).setRequired(true);
  }

  const rows = v.criteria.map(function (c) { return c.label; });
  v.items.forEach(function (it, i) {
    const n = (i + 1) + ' / ' + v.items.length;
    if (SPEC.perPage > 0 && i > 0 && i % SPEC.perPage === 0) {                // ngắt trang sau mỗi perPage thiết kế (0 = không ngắt)
      const last = Math.min(i + SPEC.perPage, v.items.length);
      form.addPageBreakItem().setTitle('Thiết kế ' + (i + 1) + ' đến ' + last + ' / ' + v.items.length);
    }
    form.addImageItem().setTitle('Thiết kế ' + n).setImage(files[it.file].getBlob()).setWidth(SPEC.imageWidth).setAlignment(FormApp.Alignment.CENTER);
    form.addGridItem()
      .setTitle('Chấm điểm thiết kế ' + n + ' (mã ' + it.code + ')')
      .setHelpText(v.criteriaHelp)
      .setRows(rows).setColumns(SPEC.scale).setRequired(true);
    if (SPEC.mode === 'expert') {
      if (SPEC.decisions.length) form.addMultipleChoiceItem().setTitle('Quyết định thiết kế ' + n + ' (mã ' + it.code + ')').setChoiceValues(SPEC.decisions).setRequired(true);
      form.addParagraphTextItem().setTitle('Nhận xét thiết kế ' + n + ' (mã ' + it.code + ')').setHelpText(SPEC.commentHelp);
    }
  });
  if (SPEC.mode === 'expert') {
    SPEC.closing.forEach(function (t) { form.addParagraphTextItem().setTitle(t); });
  } else {
    form.addParagraphTextItem().setTitle('Góp ý thêm (không bắt buộc)');
  }
  return form;
}
"""

COMMON_SHARE = ("- Mỗi thiết kế cần ít nhất 3 phiếu (đặc tả EXP-A), nên cần từ 3 người chấm trở lên cho mỗi form.\n"
                "- Đừng nói thiết kế nào ứng với trọng số ControlNet nào. Người chấm không biết điều đó.")
SHARE_ONE = "- Gửi cùng **một** link cho mọi người.\n" + COMMON_SHARE
SHARE_MANY = ("- Mỗi người chỉ nhận **một** link, chia đều các bản (ví dụ người 1 bản A, người 2 bản B, người 3 bản A...). "
              "Đừng gửi cùng một người hai bản.\n" + COMMON_SHARE)
SHARE_EXPERT_SINGLE = ("- Đây là phiếu cho **một người** (ví dụ một giảng viên), đủ mọi tiêu chí, không có quyết định Đạt hoặc Loại. "
                       "Gửi file Word trong thư mục `docx/` cho người đó; họ bấm ô tích, gõ nhận xét, lưu và gửi lại. Có thể dùng Google Form thay file Word.\n"
                       "- Đây là phiếu nhận xét chuyên gia, không phải điểm cộng đồng. Không gộp hai lượt khảo sát vào cùng một thống kê.\n"
                       "- Form thu họ tên, đơn vị và email. Giữ tệp kết quả trong thư mục `outputs/` (git bỏ qua), không đăng công khai.\n"
                       "- Đừng nói thiết kế nào ứng với trọng số ControlNet nào, và đừng nói cổng chất lượng đã loại hay cảnh báo ảnh nào.")
SHARE_EXPERT = ("- Có hai cách thu: Google Form (các bước 1 đến 2 và các link bên dưới), hoặc **file Word** trong thư mục `docx/` (gửi file cho chuyên gia, họ bấm ô tích, gõ nhận xét, lưu và gửi lại; không cần các bước 1 đến 2).\n"
                "- Có hai form dùng chung ảnh: bản **chuyên gia di sản** gửi cho người am hiểu di sản, gốm sứ, văn hóa; "
                "bản **chuyên gia thiết kế** gửi cho người am hiểu thiết kế, thời trang. Cần ít nhất 1 người mỗi vai. "
                "Người am hiểu cả hai có thể làm cả hai form, nhưng nên làm cách nhau một ngày.\n"
                "- Đây là phiếu nhận xét chuyên gia, không phải điểm cộng đồng. Không gộp hai lượt khảo sát vào cùng một thống kê.\n"
                "- Form thu họ tên, đơn vị và email. Giữ tệp kết quả trong thư mục `outputs/` (git bỏ qua), không đăng công khai.\n"
                "- Đừng nói thiết kế nào ứng với trọng số ControlNet nào, và đừng nói cổng chất lượng đã loại hay cảnh báo ảnh nào.")

GUIDE = """# Tạo Google Form chấm mù

Gói này có {n_images} ảnh ghép và {n_versions} bản form, mỗi bản {per} thiết kế (mỗi bản mất khoảng {minutes} phút).

## Bước 1. Tải ảnh lên Drive
1. Vào drive.google.com, tạo thư mục mới, ví dụ `cham_mu_exp_a`.
2. Kéo toàn bộ ảnh trong thư mục `images/` (các tệp `B*.jpg`) vào thư mục đó. Chỉ tải ảnh, **không tải `key.csv`**.
3. Mở thư mục, copy phần ID cuối link: `drive.google.com/drive/folders/<ID>`.

## Bước 2. Chạy mã tạo form
1. Vào script.google.com, bấm Dự án mới.
2. Xóa mã mẫu, dán toàn bộ nội dung `Code.gs`.
3. Ở dòng `const FOLDER_ID = '...'` dán ID thư mục.
4. Chọn hàm `createForms`, bấm Chạy, cấp quyền Drive và Forms cho tài khoản của bạn.
5. Mở Nhật ký thực thi: mỗi bản form in ra hai link, link "gửi người chấm" và link "sửa".

## Bước 3. Gửi người chấm
{share}

## Bước 4. Thu kết quả
Trong từng form, tab Câu trả lời, bấm biểu tượng Google Sheets để xuất ra bảng tính. Tiêu đề mỗi cột có mã ảnh (ví dụ `mã B2904`).
Giải mã: ghép mã ảnh với `key.csv` để biết hiện vật, trọng số ControlNet và seed. Khi có nhiều form dùng chung ảnh (bản chuyên gia), mỗi mã có một dòng cho mỗi form, nên ghép theo **cả cột `version` lẫn `code`**, không chỉ `code`, kẻo nhân đôi hàng. **Giữ `key.csv` riêng.**

## Lưu ý
- Nếu bước 2 báo hết thời gian (Apps Script giới hạn 6 phút mỗi lần chạy): vào Drive xóa form dở dang, rồi đặt `ONLY_VERSION` thành tên bản cần tạo (ví dụ `'B'`) và chạy lại. Chạy từng bản một cũng được.
- Tên tệp form trong Drive của bạn có ghi nhãn bản (ví dụ `[bản A]` hoặc `[chuyên gia di sản]`), người chấm không thấy. Tiêu đề họ thấy không ghi bản.
- Hàng nào của bảng chấm cũng phải có đáp án: tôi chưa kiểm trên Google thật xem `setRequired(true)` có bắt buộc từng hàng không. Mở thử link form, bấm Tiếp mà bỏ trống một hàng để xem. Nếu không bắt buộc, vào Chỉnh sửa, mở câu hỏi dạng lưới, bật "Yêu cầu trả lời ở mỗi hàng".
- Google Form không tự xáo thứ tự ảnh theo từng người, nên thứ tự xáo cố định theo bản. Dùng nhiều bản để cân bằng.
"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")                          # console Windows mặc định cp1252 không in được tiếng Việt
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", default="outputs/experiments/EXP-A", help="thư mục thí nghiệm (có spec.json và results.csv)")
    ap.add_argument("--audience", choices=["community", "expert"], default="community",
                    help="community: chấm điểm cho cộng đồng; expert: phiếu nhận xét chuyên gia (hai form: di sản, thiết kế)")
    ap.add_argument("--seeds", default=None, help="các seed đưa vào form, cách nhau bằng dấu phẩy (mặc định 42,7; chuyên gia: 42)")
    ap.add_argument("--single", action="store_true",
                    help="với --audience expert: MỘT phiếu cho MỘT người, đủ mọi tiêu chí, không có quyết định Đạt hoặc Loại")
    ap.add_argument("--levels", default=None,
                    help="chỉ giữ các giá trị biến độc lập này, cách nhau bằng dấu phẩy (chuyên gia mặc định 0.85,0.25: hai mức cực đoan)")
    ap.add_argument("--rotate", action="store_true",
                    help="chia thành nhiều form, mỗi form một thiết kế cho mỗi ô (mặc định: MỘT form chứa mọi thiết kế)")
    ap.add_argument("--versions", type=int, default=None, help="với --rotate: số form (mặc định bằng số seed)")
    ap.add_argument("--per-page", type=int, default=None,
                    help="số thiết kế mỗi trang của form (mặc định 4, chuyên gia 2; 0 = cả form một trang)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    expert = args.audience == "expert"
    if expert and (args.rotate or args.versions):
        ap.error("--rotate và --versions không dùng với --audience expert (luôn hai form theo vai)")
    if args.single and not expert:
        ap.error("--single chỉ dùng với --audience expert")
    seeds = args.seeds or ("42" if expert else "42,7")
    levels = args.levels or ("0.85,0.25" if expert else None)
    exp = Path(args.experiment) if Path(args.experiment).is_absolute() else ROOT / args.experiment
    out = Path(args.out) if args.out else ROOT / "outputs" / "review" / f"google_form_{exp.name}{('_expert_single' if args.single else '_expert') if expert else ''}"
    r = build(exp, out, [int(x) for x in seeds.split(",")], args.versions, one_form=not args.rotate, per_page=args.per_page,
              audience=args.audience, levels=[float(x) for x in levels.split(",")] if levels else None, single=args.single)
    print(f"Đã dựng {r['images']} ảnh, {r['versions']} bản form x {r['per_version']} thiết kế tại {r['out']}")
    if expert:                                                            # phiếu chuyên gia xuất thêm file Word để điền trực tiếp
        spec_ = importlib.util.spec_from_file_location("expert_docx", ROOT / "scripts" / "eval" / "build_expert_docx.py")
        docx_mod = importlib.util.module_from_spec(spec_)
        spec_.loader.exec_module(docx_mod)
        for path in docx_mod.write_docx(r["spec"], out / "images", out / "docx"):
            print(f"  Phiếu Word: {path}")
    print(f"  Đọc {out / 'HUONG_DAN.md'} để đưa lên Google. Giữ riêng {out / 'key.csv'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
