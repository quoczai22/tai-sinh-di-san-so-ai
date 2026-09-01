from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import unicodedata as ud
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path

import pdfplumber

# Console Windows mặc định cp1252, không in được tiếng Việt.
for _stream in (sys.stdout, sys.stderr):
    if getattr(_stream, "encoding", "").lower().replace("-", "") != "utf8":
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

logging.getLogger("pdfminer").setLevel(logging.ERROR)

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "data" / "documents"
SOURCES_JSON = ROOT / "data" / "sources.json"
RULE_BASE_JSON = ROOT / "data" / "rule_base.json"
OUT_DIR = ROOT / "data" / "corpus"

# Tham số các tầng lọc 
BAND_TOP = 0.08           # dải trên trang, tính theo tỉ lệ chiều cao
BAND_BOTTOM = 0.92        # dải dưới trang
BOILER_PAGE_RATIO = 0.60  # dòng phải lặp trên ngần này tỉ lệ số trang mới bị coi là boilerplate

LINK_WINDOW = 8           # cửa sổ trượt đo mật độ liên kết
LINK_DENSITY = 0.50       # đo được: thân bài 0.10-0.11, khối điều hướng 0.70-0.73
NAV_MIN_START_RATIO = 0.30  # chỉ tìm phần đuôi sau mốc này (đo được: nav bắt đầu ở 56-70%)
REPEAT_THRESHOLD = 0.40     # đo được: thân bài 0.00-0.17, text chồng nhau 0.44-0.77
BODY_END_MARGIN = 3         # giữ thêm vài dòng sau dòng văn xuôi cuối (câu kết của đoạn)

BODY_WIDTH_PCT = 0.90     # phân vị lấy bề rộng dòng đặc trưng của tài liệu
BODY_WIDTH_RATIO = 0.75   # dòng dài >= tỉ lệ này so với bề rộng đó = văn xuôi
BODY_MAX_SCAN_RATIO = 0.25  # chỉ tìm điểm bắt đầu trong phần đầu tài liệu

MIN_PARAGRAPH_CHARS = 80  # đoạn ngắn hơn được gộp vào đoạn liền trước

MIN_CLEAN_CHARS = 500     # dưới ngưỡng này coi như PDF không có lớp text

# T1 — chỉ mô tả HÌNH DẠNG, tuyệt đối không chứa từ vựng của bất kỳ website nào.
FORMAT_PATTERNS = [
    r"^\d{1,2}/\d{1,2}/\d{2},?\s*\d{1,2}:\d{2}\s*(AM|PM)",     # dấu thời gian in
    r"^\d+\s*/\s*\d+$",                                         # số trang "3/17"
    r"^\d+$",                                                   # số trang trần
    r"^https?://",                                              # URL trần
    r"\(/\w+\)|/\w+/Articles/|\.html",                          # cú pháp liên kết
    r"^\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}\s+\d+\s*$",        # ngày giờ lượt xem
    r"^\s*E-?mail\s*:\s*\S+@\S+",                               # dòng địa chỉ email
]
FORMAT_RE = [re.compile(p) for p in FORMAT_PATTERNS]

# T3 — dấu hiệu một dòng có chứa liên kết (dùng đo mật độ, không dùng để xoá).
LINK_RE = re.compile(r"\(/\w+|https?://|\.html|/Articles/")

# Ký tự vùng Private Use Area: glyph icon-font (lịch, sao đánh giá, mắt lượt xem).
# Không mang nghĩa nhưng làm hỏng mọi neo '^' trong regex.
PUA_RE = re.compile("[\uE000-\uF8FF]")


@dataclass
class Paragraph:
    text: str
    page: int


@dataclass
class CleanDoc:
    src_id: str
    title: str
    kind: str
    n_pages: int
    chars_raw: int
    chars_clean: int
    n_paragraphs: int
    dropped: dict
    paragraphs: list

    def full_text(self) -> str:
        return "\n\n".join(p["text"] if isinstance(p, dict) else p.text
                           for p in self.paragraphs)


def nfc(s: str) -> str:
    """Chuẩn hoá NFC — bắt buộc theo spec mục 8.4. SRC006 dùng Unicode tổ hợp."""
    return PUA_RE.sub(" ", ud.normalize("NFC", s))


def squash(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def percentile(values: list[int], q: float) -> float:
    if not values:
        return 0.0
    v = sorted(values)
    k = (len(v) - 1) * q
    f = int(k)
    return float(v[f]) if f + 1 >= len(v) else v[f] + (v[f + 1] - v[f]) * (k - f)


def load_manifest() -> dict:
    with open(SOURCES_JSON, encoding="utf-8") as f:
        return json.load(f)["sources"]



# Trích text kèm toạ độ dọc (cần cho T2)

def extract_lines(pdf_path: Path) -> tuple[list[tuple[int, str, float]], int]:
    """Trả về [(số trang, nội dung dòng, vị trí dọc 0..1)], và tổng số trang."""
    out: list[tuple[int, str, float]] = []
    with pdfplumber.open(pdf_path) as pdf:
        n_pages = len(pdf.pages)
        for pno, page in enumerate(pdf.pages, start=1):
            height = page.height or 1
            # Dùng extract_text_lines() chứ KHÔNG tự gom extract_words() theo toạ
            # độ dọc: các từ cùng một dòng hình ảnh có thể lệch `top` vài điểm
            # (dấu thanh tiếng Việt làm thay đổi hộp bao), khiến việc gom thủ công
            # chẻ một dòng thành hai nhóm xen kẽ và đảo lộn trật tự từ.
            # Hàm này của pdfplumber có sẵn dung sai dọc và trả kèm toạ độ.
            for line in page.extract_text_lines():
                text = squash(nfc(line["text"]))
                if text:
                    out.append((pno, text, line["top"] / height))
    return out, n_pages



# T3 — mật độ liên kết: cắt khối "bài liên quan" ở cuối

def ngram_repetition(s: str, n: int = 4) -> float:
    """Tỉ lệ n-gram trùng lặp trong một dòng.

    Nút chia sẻ mạng xã hội render text chồng lên nhau, khi trích ra thành
    chuỗi kiểu 'tap-tap-tap-tap-'. Đo được: thân bài 0.00-0.17, khối rác này
    0.44-0.77 — tách bạch rất rõ. Đây là hiện tượng của kỹ thuật render PDF,
    không phụ thuộc ngôn ngữ hay website nào.
    """
    grams = [s[i:i + n] for i in range(len(s) - n + 1)]
    return 1 - len(set(grams)) / len(grams) if grams else 0.0


def find_back_matter(lines: list[str]) -> tuple[int, str]:
    """Tìm điểm bắt đầu phần đuôi (điều hướng / footer / bài liên quan).

    Gộp ba tín hiệu cấu trúc, lấy điểm cắt SỚM NHẤT. Cả ba đều tự vô hiệu
    trên tài liệu không phải web, nên không cần rẽ nhánh theo loại tài liệu.
    """
    n = len(lines)
    if n < LINK_WINDOW * 3:
        return n, "tai lieu qua ngan"
    cuts: list[tuple[int, str]] = []

    # (a) Mật độ liên kết cao — khối danh sách bài liên quan.
    floor = int(n * NAV_MIN_START_RATIO)
    for i in range(floor, n - LINK_WINDOW + 1):
        window = lines[i:i + LINK_WINDOW]
        if sum(1 for l in window if LINK_RE.search(l)) / len(window) >= LINK_DENSITY:
            cuts.append((i, "mat do lien ket"))
            break

    # (b) Text chồng nhau của nút chia sẻ.
    for i in range(floor, n):
        if len(lines[i]) >= 12 and ngram_repetition(lines[i]) >= REPEAT_THRESHOLD:
            cuts.append((i, "text chong nhau"))
            break

    if not cuts:
        return n, "khong thay phan duoi"
    return min(cuts)


def find_body_end(lines: list[str]) -> int:
    """T5 — đối xứng với T4: thân bài kết thúc ở dòng văn xuôi CUỐI cùng.

    Bắt phần đuôi gồm toàn dòng ngắn (footer nhiều cột, danh sách bài liên quan
    không có liên kết) mà tín hiệu mật độ liên kết và text chồng nhau không thấy.

    Phải chạy SAU T1+T2 giống T4: nếu chạy trên dòng thô, các dòng rác dài
    (URL, dòng bản quyền) sẽ bị tính là văn xuôi và phần đuôi thoát lưới.
    """
    if not lines:
        return 0
    width = percentile([len(l) for l in lines], BODY_WIDTH_PCT)
    threshold = BODY_WIDTH_RATIO * width
    last = max((i for i, l in enumerate(lines) if len(l) >= threshold),
               default=len(lines) - 1)
    return min(len(lines), last + BODY_END_MARGIN)



# T2 — vị trí hình học: header/footer chạy

def find_boilerplate(rows: list[tuple[int, str, float]], n_pages: int) -> set[str]:
    """Dòng nằm ở dải trên/dưới trang VÀ lặp trên phần lớn số trang.

    Đo được: bắt 17/17 trang ở tài liệu web in ra, 0/11 ở bài tạp chí —
    cơ chế tự nhận biết tài liệu nào có boilerplate mà không cần khai báo.
    """
    seen: dict[str, set[int]] = defaultdict(set)
    for pno, text, ratio in rows:
        if ratio < BAND_TOP or ratio > BAND_BOTTOM:
            seen[text].add(pno)
    need = max(2, BOILER_PAGE_RATIO * n_pages)
    return {t for t, pages in seen.items() if len(pages) >= need}



# T4 — bề rộng dòng: cắt khối bìa/tiêu đề đầu tài liệu

def find_body_start(lines: list[str]) -> int:
    """Thân bài bắt đầu ở dòng văn xuôi đầu tiên.

    Ngưỡng lấy TƯƠNG ĐỐI theo bề rộng dòng của chính tài liệu đó. Một ngưỡng
    tuyệt đối là bất khả: đo được tài liệu web cần >114 ký tự để bỏ qua dòng
    tiêu đề, còn bài tạp chí cần <=97 để giữ phần Tóm tắt.
    """
    if not lines:
        return 0
    width = percentile([len(l) for l in lines], BODY_WIDTH_PCT)
    threshold = BODY_WIDTH_RATIO * width
    limit = max(1, int(len(lines) * BODY_MAX_SCAN_RATIO))
    for i, line in enumerate(lines[:limit]):
        if len(line) >= threshold:
            return i
    return 0



# Nối dòng gãy thành đoạn, gộp đoạn quá ngắn

def reflow(page_lines: list[tuple[int, str]]) -> list[Paragraph]:
    """PDF ngắt dòng theo layout chứ không theo câu."""
    paras: list[Paragraph] = []
    buf, buf_page = "", None

    def flush():
        nonlocal buf, buf_page
        t = squash(buf)
        if t:
            paras.append(Paragraph(text=t, page=buf_page))
        buf, buf_page = "", None

    for page, line in page_lines:
        s = squash(line)
        if not s:
            flush()
            continue
        if buf_page is None:
            buf_page = page
        buf = f"{buf} {s}" if buf else s
        # Chỉ ngắt đoạn khi dòng kết thúc bằng dấu câu, cho phép kèm ngoặc kép
        # đóng phía sau. KHÔNG ngắt khi dòng chỉ kết thúc bằng ngoặc kép trần:
        # đó thường là cụm trích dẫn giữa câu, ví dụ dòng kết thúc bằng
        # 'cụm từ "bầu rượu, túi thơ"' rồi câu còn tiếp ở dòng sau.
        if re.search(r'[.!?…:]["”\'»]?$', s):
            flush()
    flush()

    # Chú thích ảnh mang thông tin niên đại nên KHÔNG xoá, nhưng đứng một mình
    # thì embedding vô nghĩa — gộp vào đoạn liền trước.
    merged: list[Paragraph] = []
    for p in paras:
        if merged and len(p.text) < MIN_PARAGRAPH_CHARS:
            merged[-1] = Paragraph(text=f"{merged[-1].text} {p.text}",
                                   page=merged[-1].page)
        else:
            merged.append(p)
    return merged



# Đối chiếu danh tính (spec mục 19.1)

def verify_identity(meta: dict, raw_text: str) -> tuple[bool, str]:
    """Bắt lỗi gán nhầm file cho mã nguồn — loại lỗi khiến mọi trích dẫn sai
    nguồn một cách hệ thống mà nhìn mắt thường không phát hiện được."""
    ref = meta.get("url") or meta.get("doi")
    if not ref:
        return True, "khong co url/doi de doi chieu"
    if ref in raw_text:
        return True, ("url khop" if meta.get("url") else "doi khop")
    return False, f"KHONG thay '{ref[:60]}' trong PDF"



def ingest_one(src_id: str, meta: dict, verbose=True, report=False) -> CleanDoc:
    pdf_path = DOCS_DIR / meta["file"]
    if not pdf_path.exists():
        raise FileNotFoundError(f"{src_id}: khong thay {pdf_path}")

    rows, n_pages = extract_lines(pdf_path)
    raw_text = "\n".join(t for _, t, _ in rows)

    ok, detail = verify_identity(meta, raw_text)
    if not ok:
        raise ValueError(f"{src_id}: doi chieu danh tinh THAT BAI — {detail}")

    # T3 — cắt phần đuôi (trước T1, vì T1 xoá chính các liên kết dùng làm tín hiệu)
    nav_cut, nav_why = find_back_matter([t for _, t, _ in rows])
    dropped_nav = [t for _, t, _ in rows[nav_cut:]]
    rows = rows[:nav_cut]

    # T2 — header/footer chạy
    boiler = find_boilerplate(rows, n_pages)
    dropped_boiler = [t for _, t, _ in rows if t in boiler]
    rows = [(p, t, r) for p, t, r in rows if t not in boiler]

    # T1 — hình dạng dòng
    dropped_fmt = [t for _, t, _ in rows if any(x.search(t) for x in FORMAT_RE)]
    rows = [(p, t, r) for p, t, r in rows if not any(x.search(t) for x in FORMAT_RE)]

    # T4 — cắt khối bìa/tiêu đề đầu tài liệu
    body_i = find_body_start([t for _, t, _ in rows])
    dropped_front = [t for _, t, _ in rows[:body_i]]
    rows = rows[body_i:]

    # T5 — cắt phần đuôi còn sót (đối xứng T4, phải chạy sau T1+T2)
    body_e = find_body_end([t for _, t, _ in rows])
    dropped_tail = [t for _, t, _ in rows[body_e:]]
    rows = rows[:body_e]

    paras = reflow([(p, t) for p, t, _ in rows])
    chars_clean = sum(len(p.text) for p in paras)
    if chars_clean < MIN_CLEAN_CHARS:
        raise ValueError(
            f"{src_id}: chi con {chars_clean} ky tu sau khi lam sach. "
            f"PDF co the la ban quet anh chua OCR, hoac bo loc cat qua tay.")

    doc = CleanDoc(
        src_id=src_id, title=meta["title"], kind=meta["kind"], n_pages=n_pages,
        chars_raw=len(raw_text), chars_clean=chars_clean, n_paragraphs=len(paras),
        dropped={"nav": len(dropped_nav), "boilerplate": len(dropped_boiler),
                 "format": len(dropped_fmt), "front_matter": len(dropped_front),
                 "tail": len(dropped_tail)},
        paragraphs=[asdict(p) for p in paras],
    )
    if verbose:
        d = doc.dropped
        pct = 100 - doc.chars_clean * 100 // max(1, doc.chars_raw)
        print(f"  {src_id}  {n_pages:2}tr | {doc.chars_raw:6} -> {doc.chars_clean:6} "
              f"(-{pct:2}%) | {doc.n_paragraphs:3} doan | bo: T3={d['nav']:3} "
              f"T2={d['boilerplate']:3} T1={d['format']:3} T4={d['front_matter']:2} T5={d['tail']:3} | {nav_why}")
    if report:
        for name, items in (("T3 dieu huong", dropped_nav), ("T2 boilerplate", dropped_boiler),
                            ("T1 hinh dang", dropped_fmt), ("T4 bia/tieu de", dropped_front), ("T5 phan duoi", dropped_tail)):
            if items:
                print(f"       [{name}] {len(items)} dong, vi du:")
                for t in items[:3]:
                    print(f"          {t[:88]}")
    return doc



# Phép kiểm nghiệm thu

# Từ khoá chỉ xuất hiện trong các bài KHÁC bị in kèm ở khối "Bài nổi bật".
# KHÔNG dùng "Hồ Chí Minh" trần: SRC003 nhắc hợp lệ "sưu tập tư nhân ở TP Hồ Chí Minh"
# — đó là địa danh, không phải nội dung lạc đề tài.
# Đây là LƯỚI AN TOÀN độc lập với 4 tầng lọc, không phải cơ chế lọc.
OFFTOPIC = ["Chủ tịch Hồ Chí Minh", "giải phóng miền Nam", "thực dân Pháp",
            "kháng chiến", "Lý Thường Kiệt", "Chiếu dời đô", "Canh nông chi đồ"]


def check_offtopic(docs: dict) -> int:
    print("\n[KIEM 1] Noi dung lac de tai")
    bad = 0
    for sid, d in docs.items():
        hits = [k for k in OFFTOPIC if k in d.full_text()]
        if hits:
            print(f"  [LOI] {sid}: con {hits}")
            bad += 1
    if not bad:
        print("  Sach — khong tai lieu nao con noi dung lac de tai")
    return bad


def check_quotes(docs: dict) -> int:
    """Bài kiểm hồi quy: mọi câu trích nguyên văn trong rule_base.json phải còn
    tìm thấy được sau khi làm sạch. Câu nào mất = bộ lọc cắt quá tay."""
    print("\n[KIEM 2] Trich dan nguyen van trong rule_base.json")
    with open(RULE_BASE_JSON, encoding="utf-8") as f:
        items = json.load(f)["heritage_items"]
    # Gộp cả tiêu đề: T4 cắt dòng tiêu đề khỏi thân bài, nhưng tiêu đề vẫn là
    # danh tính hợp lệ của tài liệu và được lưu trong sources.json.
    texts = {sid: squash(nfc(d.title + " " + d.full_text())) for sid, d in docs.items()}
    total = ok = 0
    for it in items:
        note = it["source_note"] + " " + it["cultural_meaning"]
        cited = set(re.findall(r"SRC\d{3}", note)) | set(it["rule_sources"].values())
        for q in re.findall(r"'([^']{12,})'", note):
            total += 1
            frags = [squash(nfc(x)) for x in re.split(r"\.\.\.|…", q) if squash(x)]
            found = [s for s, t in texts.items() if all(fr in t for fr in frags)]
            if set(found) & cited:
                ok += 1
            else:
                print(f"  [MAT] {it['heritage_id']}: <<{q[:60]}>> | chi thay o {found or 'khong dau'}")
    print(f"  {ok}/{total} trich dan van tim thay dung nguon")
    return total - ok


def check_manifest(manifest: dict) -> int:
    print("\n[KIEM 3] rule_sources chi tro toi nguon rule_basis='allowed'")
    with open(RULE_BASE_JSON, encoding="utf-8") as f:
        items = json.load(f)["heritage_items"]
    bad = 0
    for it in items:
        for cat, v in it["rule_sources"].items():
            if not re.fullmatch(r"SRC\d{3}", v):
                print(f"  [LOI] {it['heritage_id']}.{cat} = {v}")
                bad += 1
            elif manifest[v]["rule_basis"] != "allowed":
                print(f"  [LOI] {it['heritage_id']}.{cat} = {v} "
                      f"(rule_basis={manifest[v]['rule_basis']})")
                bad += 1
    blob = json.dumps(items, ensure_ascii=False)
    for k, m in manifest.items():
        if m["rule_basis"] == "forbidden" and k in blob:
            print(f"  [LOI] {k} rule_basis=forbidden nhung xuat hien trong rule_base.json")
            bad += 1
    if not bad:
        print("  Hop le")
    return bad



def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--report", action="store_true", help="in chi tiet dong bi loai")
    args = ap.parse_args()

    manifest = load_manifest()
    print(f"Manifest: {len(manifest)} nguon\n[INGEST]")

    docs = {sid: ingest_one(sid, manifest[sid], report=args.report)
            for sid in sorted(manifest)}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for sid, d in docs.items():
        with open(OUT_DIR / f"{sid}.json", "w", encoding="utf-8") as f:
            json.dump(asdict(d), f, ensure_ascii=False, indent=2)
    print(f"\nDa ghi {len(docs)} tai lieu sach vao {OUT_DIR.relative_to(ROOT)}/")

    if args.no_verify:
        print("\n(bo qua phep kiem)")
        return 0

    errs = check_offtopic(docs) + check_quotes(docs) + check_manifest(manifest)
    print(f"\n{'=' * 60}\nTONG LOI: {errs}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
