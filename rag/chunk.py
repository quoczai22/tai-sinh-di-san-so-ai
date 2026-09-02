from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata as ud
from dataclasses import dataclass, asdict
from pathlib import Path

# Console Windows mặc định cp1252, không in được tiếng Việt.
for _stream in (sys.stdout, sys.stderr):
    if getattr(_stream, "encoding", "").lower().replace("-", "") != "utf8":
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "data" / "corpus"
SOURCES_JSON = ROOT / "data" / "sources.json"
RULE_BASE_JSON = ROOT / "data" / "rule_base.json"
OUT_FILE = ROOT / "data" / "chunks.jsonl"

# --- Tham số cắt chunk -----------------------------------------------------
# BGE-M3 nhận tới 8192 token nên các ngưỡng này rất thoải mái. Chọn nhỏ để mỗi
# chunk giữ một ý trọn vẹn — truy xuất trúng đích hơn là trả về cả trang.
TARGET_CHARS = 700    # kích thước mong muốn
MAX_CHARS = 1000      # vượt ngưỡng này thì buộc phải cắt
MIN_CHARS = 200       # dưới ngưỡng này thì gộp với chunk kế (trừ chunk cuối tài liệu)
OVERLAP_CHARS = 150   # phần chồng lấn giữa hai chunk liền nhau, cắt theo ranh giới câu

# --- Tham số locator -------------------------------------------------------
LOCATOR_MIN = 40      # ngắn quá thì không đủ đặc trưng để tìm lại
LOCATOR_MAX = 140     # dài quá thì không còn là "trích dẫn ngắn"

# Tiêu đề mục đánh số: "3. Băng hoa dây lá lật", "2.6. Bình vôi".
# Dạng đánh số là quy ước quốc tế, không phải từ vựng của một website.
SECTION_RE = re.compile(r"^(\d+(?:\.\d+)*)\.\s*(.{3,120})")

# Ngắt câu: dấu câu, theo sau là khoảng trắng rồi chữ hoa hoặc số.
SENT_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+(?=[A-ZĐÂÊÔƯĂÁÀẢÃẠÍÌỈĨỊÚÙỦŨỤÉÈẺẼẸÓÒỎÕỌÝỲỶỸỴ0-9])")


@dataclass
class Chunk:
    chunk_id: str
    src_id: str
    chunk_index: int
    text: str
    locator: str
    section: str | None
    page: int | None
    n_chars: int
    para_from: int
    para_to: int



def nfc(s: str) -> str:
    return ud.normalize("NFC", s)


def squash(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in SENT_SPLIT_RE.split(text)]
    return [p for p in parts if p]


def detect_section(paragraph: str) -> str | None:
    """Nhận tiêu đề mục đánh số ở đầu đoạn. Best-effort, có thể trả None.

    Ranh giới tiêu đề/thân bài: rag/ingest.py đã nối tiêu đề vào cùng đoạn với
    câu đầu thân bài ("2. Chữ Thọ trong ô hình lá đề Theo các tài liệu..."), nên
    phải tự tìm chỗ ngắt. Không thể dừng ở "từ viết hoa kế tiếp" — chính tiêu đề
    cũng chứa từ viết hoa ("Chữ Thọ"). Dấu hiệu đúng là từ viết hoa đi NGAY SAU
    một từ viết thường: đó là lúc câu thân bài bắt đầu.
    """
    m = SECTION_RE.match(paragraph.strip())
    if not m:
        return None
    words = m.group(2).split()
    title_words: list[str] = []
    for i, w in enumerate(words):
        if (i >= 2 and w[:1].isupper()
                and words[i - 1][:1].islower() and not words[i - 1].endswith(",")):
            break
        title_words.append(w)
        if w.endswith("."):          # tiêu đề tự kết thúc bằng dấu chấm
            break
    title = squash(" ".join(title_words)).rstrip(".")
    # Loại nhầm với câu bắt đầu bằng số ("13 tác phẩm gốm Bát Tràng lưu danh...")
    if not title or len(title) > 60 or title[:1].islower():
        return None
    return f"{m.group(1)}. {title}"


def pick_locator(text: str) -> str:
    """Chọn một đoạn trích NGUYÊN VĂN từ chunk để làm định vị nguồn.

    Ưu tiên câu trọn vẹn có độ dài vừa phải. Nếu không có câu nào lọt khoảng,
    cắt theo ranh giới từ để không bao giờ tạo ra chuỗi không tồn tại trong nguồn.
    """
    for sent in split_sentences(text):
        if LOCATOR_MIN <= len(sent) <= LOCATOR_MAX:
            return sent
    # Không có câu vừa khoảng: cắt từ đầu chunk theo ranh giới từ.
    if len(text) <= LOCATOR_MAX:
        return text
    cut = text[:LOCATOR_MAX]
    space = cut.rfind(" ")
    return cut[:space] if space > LOCATOR_MIN else cut


def split_by_words(text: str, limit: int) -> list[str]:
    """Câu đơn dài hơn `limit` thì cắt theo ranh giới TỪ.

    Không bao giờ cắt giữa từ: chunk phải luôn là chuỗi con hợp lệ của nguồn
    để phép kiểm truy ngược và locator còn ý nghĩa.
    """
    out, buf = [], ""
    for word in text.split(" "):
        if buf and len(buf) + 1 + len(word) > limit:
            out.append(buf)
            buf = word
        else:
            buf = f"{buf} {word}" if buf else word
    if buf:
        out.append(buf)
    return out


def tail_overlap(text: str) -> str:
    """Lấy phần đuôi ~OVERLAP_CHARS, cắt theo ranh giới câu."""
    sents = split_sentences(text)
    out: list[str] = []
    total = 0
    for s in reversed(sents):
        if total + len(s) > OVERLAP_CHARS and out:
            break
        out.insert(0, s)
        total += len(s) + 1
    tail = " ".join(out)
    # Chặn trên cứng: một câu đuôi dài vài trăm ký tự sẽ được lấy trọn vì vòng
    # lặp luôn nhận ít nhất một câu. Cắt bớt theo ranh giới TỪ, giữ phần cuối.
    if len(tail) > OVERLAP_CHARS:
        tail = " ".join(split_by_words(tail, OVERLAP_CHARS)[-1:])
    return tail



def split_long_paragraph(text: str) -> list[str]:
    """Cắt đoạn theo câu, gom lại quanh TARGET_CHARS.

    Câu đơn dài hơn MAX_CHARS được cắt tiếp theo từ — nếu không, một câu dài
    sẽ tự nó thành một chunk vượt ngưỡng.
    """
    pieces: list[str] = []
    buf = ""
    for sent in split_sentences(text):
        for part in (split_by_words(sent, TARGET_CHARS)
                     if len(sent) > TARGET_CHARS else [sent]):
            if buf and len(buf) + 1 + len(part) > TARGET_CHARS:
                pieces.append(buf)
                buf = part
            else:
                buf = f"{buf} {part}" if buf else part
    if buf:
        pieces.append(buf)
    return pieces or [text]


def chunk_document(doc: dict, meta: dict) -> list[Chunk]:
    src_id = doc["src_id"]
    use_page = bool(meta.get("has_canonical_pages"))
    paras = doc["paragraphs"]

    # Gom đoạn thành nhóm quanh TARGET_CHARS, tôn trọng ranh giới đoạn.
    groups: list[dict] = []
    cur = {"texts": [], "chars": 0, "from": 0, "to": 0, "page": None, "section": None}
    section = None

    for i, p in enumerate(paras):
        text = squash(nfc(p["text"]))
        if not text:
            continue
        sec = detect_section(text)
        if sec:
            section = sec

        for piece in (split_long_paragraph(text) if len(text) > TARGET_CHARS else [text]):
            if cur["texts"] and cur["chars"] + len(piece) > TARGET_CHARS:
                groups.append(cur)
                cur = {"texts": [], "chars": 0, "from": i, "to": i,
                       "page": p["page"], "section": section}
            if not cur["texts"]:
                cur.update(**{"from": i, "page": p["page"], "section": section})
            cur["texts"].append(piece)
            cur["chars"] += len(piece) + 1
            cur["to"] = i
    if cur["texts"]:
        groups.append(cur)

    # Gộp nhóm quá ngắn vào nhóm liền trước (trừ khi nó là nhóm duy nhất).
    merged: list[dict] = []
    for g in groups:
        if merged and g["chars"] < MIN_CHARS and merged[-1]["chars"] + g["chars"] <= MAX_CHARS:
            merged[-1]["texts"].extend(g["texts"])
            merged[-1]["chars"] += g["chars"]
            merged[-1]["to"] = g["to"]
        else:
            merged.append(g)

    chunks: list[Chunk] = []
    prev_text = ""
    for idx, g in enumerate(merged):
        body = squash(" ".join(g["texts"]))
        # Chồng lấn: nối phần đuôi của chunk trước để câu không bị mất ngữ cảnh.
        overlap = tail_overlap(prev_text) if idx > 0 else ""
        text = squash(f"{overlap} {body}") if overlap else body
        chunks.append(Chunk(
            chunk_id=f"{src_id}#{idx:03d}",
            src_id=src_id,
            chunk_index=idx,
            text=text,
            locator=pick_locator(body),   # locator lấy từ THÂN chunk, không lấy từ phần chồng lấn
            section=g["section"],
            page=g["page"] if use_page else None,
            n_chars=len(text),
            para_from=g["from"],
            para_to=g["to"],
        ))
        prev_text = body
    return chunks



# Phép kiểm nghiệm thu

def check_locators(chunks: list[Chunk], corpus: dict) -> int:
    """Ràng buộc bắt buộc của spec mục 8.3.1: locator phải xuất hiện NGUYÊN VĂN
    trong tài liệu nguồn sau khi chuẩn hoá NFC."""
    print("\n[KIEM 1] locator xuat hien nguyen van trong tai lieu nguon")
    bad = 0
    for c in chunks:
        if squash(nfc(c.locator)) not in corpus[c.src_id]:
            print(f"  [LOI] {c.chunk_id}: <<{c.locator[:70]}>>")
            bad += 1
    print(f"  {len(chunks) - bad}/{len(chunks)} locator hop le")
    return bad


def check_traceable(chunks: list[Chunk], corpus: dict) -> int:
    """Thân chunk phải truy ngược được về corpus — bắt nội dung bị biến dạng."""
    print("\n[KIEM 2] Noi dung chunk truy nguoc duoc ve corpus")
    W, total, ok = 60, 0, 0
    bad_ids = set()
    for c in chunks:
        t = squash(nfc(c.text))
        for i in range(0, max(1, len(t) - W), W):
            w = t[i:i + W]
            if len(w) < W:
                continue
            total += 1
            if w in corpus[c.src_id]:
                ok += 1
            else:
                bad_ids.add(c.chunk_id)
    for cid in list(bad_ids)[:3]:
        print(f"  [LECH] {cid}")
    print(f"  {ok}/{total} cua so khop ({ok * 100 // max(1, total)}%)")
    # Chồng lấn nối hai đoạn không liền kề nên vài cửa sổ lệch là bình thường.
    return 1 if total and ok * 100 // total < 90 else 0


def check_quotes(chunks: list[Chunk], titles: dict[str, str]) -> int:
    """Bài kiểm hồi quy: 52 câu trích trong rule_base.json phải còn tìm thấy
    được sau khi cắt chunk. Câu nào mất nghĩa là chunk cắt vào giữa nó."""
    print("\n[KIEM 3] Trich dan rule_base.json con tim thay sau khi cat chunk")
    with open(RULE_BASE_JSON, encoding="utf-8") as f:
        items = json.load(f)["heritage_items"]
    # Gộp cả tiêu đề tài liệu: rag/ingest.py cắt dòng tiêu đề khỏi thân bài,
    # nhưng tiêu đề vẫn là danh tính hợp lệ và được lưu trong data/sources.json.
    by_src: dict[str, str] = {s: squash(nfc(t)) for s, t in titles.items()}
    for c in chunks:
        by_src[c.src_id] = by_src.get(c.src_id, "") + " " + squash(nfc(c.text))
    total = ok = 0
    for it in items:
        note = it["source_note"] + " " + it["cultural_meaning"]
        cited = set(re.findall(r"SRC\d{3}", note)) | set(it["rule_sources"].values())
        for q in re.findall(r"'([^']{12,})'", note):
            total += 1
            frags = [squash(nfc(x)) for x in re.split(r"\.\.\.|…", q) if squash(x)]
            found = [s for s, t in by_src.items() if all(fr in t for fr in frags)]
            if set(found) & cited:
                ok += 1
            else:
                print(f"  [MAT] {it['heritage_id']}: <<{q[:58]}>>")
    print(f"  {ok}/{total} trich dan van tim thay dung nguon")
    return total - ok


def check_sizes(chunks: list[Chunk]) -> int:
    print("\n[KIEM 4] Kich thuoc chunk")
    over = [c for c in chunks if c.n_chars > MAX_CHARS + OVERLAP_CHARS]
    tiny = [c for c in chunks if c.n_chars < MIN_CHARS]
    for c in over[:3]:
        print(f"  [QUA DAI] {c.chunk_id}: {c.n_chars} ky tu")
    for c in tiny[:3]:
        print(f"  [QUA NGAN] {c.chunk_id}: {c.n_chars} ky tu")
    if not over and not tiny:
        print(f"  Tat ca {len(chunks)} chunk nam trong khoang cho phep")
    return len(over) + len(tiny)


def check_coverage(chunks: list[Chunk], corpus: dict) -> int:
    """Mọi đoạn của corpus phải nằm trong ít nhất một chunk — bắt mất nội dung."""
    print("\n[KIEM 5] Do phu: moi doan corpus deu vao chunk")
    bad = 0
    for f in sorted(CORPUS_DIR.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        sid = d["src_id"]
        joined = " ".join(squash(nfc(c.text)) for c in chunks if c.src_id == sid)
        missing = [i for i, p in enumerate(d["paragraphs"])
                   if squash(nfc(p["text"]))[:80] not in joined]
        if missing:
            print(f"  [LOI] {sid}: {len(missing)} doan khong vao chunk nao {missing[:5]}")
            bad += 1
    if not bad:
        print("  Day du — khong doan nao bi bo sot")
    return bad



def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()

    with open(SOURCES_JSON, encoding="utf-8") as f:
        manifest = json.load(f)["sources"]

    files = sorted(CORPUS_DIR.glob("*.json"))
    if not files:
        print(f"Khong thay file nao trong {CORPUS_DIR}. Chay `python -m rag.ingest` truoc.")
        return 1

    print(f"Corpus: {len(files)} tai lieu\n[CHUNK]")
    all_chunks: list[Chunk] = []
    corpus_text: dict[str, str] = {}

    for f in files:
        doc = json.loads(f.read_text(encoding="utf-8"))
        sid = doc["src_id"]
        corpus_text[sid] = squash(nfc(" ".join(p["text"] for p in doc["paragraphs"])))
        cs = chunk_document(doc, manifest.get(sid, {}))
        all_chunks.extend(cs)
        lens = [c.n_chars for c in cs] or [0]
        n_sec = sum(1 for c in cs if c.section)
        n_page = sum(1 for c in cs if c.page is not None)
        print(f"  {sid}  {doc['n_paragraphs']:3} doan -> {len(cs):3} chunk | "
              f"TB {sum(lens)//len(lens):4} ky tu (min {min(lens):3}, max {max(lens):4}) | "
              f"section={n_sec:2} page={n_page:2}")

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
    total_chars = sum(c.n_chars for c in all_chunks)
    print(f"\nDa ghi {len(all_chunks)} chunk ({total_chars} ky tu) vao "
          f"{OUT_FILE.relative_to(ROOT)}")

    if args.stats:
        print("\n[PHAN BO DO DAI]")
        buckets = [0] * 6
        for c in all_chunks:
            buckets[min(5, c.n_chars // 200)] += 1
        for i, n in enumerate(buckets):
            lo, hi = i * 200, (i + 1) * 200
            label = f"{lo:4}-{hi:4}" if i < 5 else "1000+   "
            print(f"  {label} : {'#' * n} {n}")

    if args.no_verify:
        print("\n(bo qua phep kiem)")
        return 0

    errs = (check_locators(all_chunks, corpus_text)
            + check_traceable(all_chunks, corpus_text)
            + check_quotes(all_chunks, {s: m.get('title', '') for s, m in manifest.items()})
            + check_sizes(all_chunks)
            + check_coverage(all_chunks, corpus_text))
    print(f"\n{'=' * 60}\nTONG LOI: {errs}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
