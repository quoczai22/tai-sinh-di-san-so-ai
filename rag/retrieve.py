# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import os
import sys
import unicodedata as ud
from pathlib import Path

import numpy as np

# Console Windows mặc định cp1252, không in được tiếng Việt.
for _stream in (sys.stdout, sys.stderr):
    if getattr(_stream, "encoding", "").lower().replace("-", "") != "utf8":
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

ROOT = Path(__file__).resolve().parent.parent
CHUNKS_FILE = ROOT / "data" / "chunks.jsonl"
VECTORS_FILE = ROOT / "data" / "embeddings.npy"
META_FILE = ROOT / "data" / "embeddings_meta.json"
SOURCES_JSON = ROOT / "data" / "sources.json"
CORPUS_DIR = ROOT / "data" / "corpus"

TOP_K = 5
MIN_SIMILARITY = 0.35   # dưới ngưỡng này coi như không liên quan, không đưa vào Evidence
MAX_CONTEXT_CHARS = 3000

# Truy vấn kiểm định — dùng cho mốc Go/No-Go Ngày 5.
PROBES = [
    ("hoa sen tạo hình trên lư hương gốm thờ",       {"SRC001", "SRC006"}),
    ("bát quái tám quẻ trổ thủng trên nắp đỉnh thờ", {"SRC001"}),
    ("chữ Thọ trong ô hình lá đề",                   {"SRC003"}),
    ("ống nhổ và bình vôi gắn tục ăn trầu",          {"SRC004"}),
    ("men rạn là đặc trưng riêng của lò Bát Tràng",  {"SRC005", "SRC001", "SRC006"}),
    ("bộ tứ linh long ly quy phượng trên chân đèn",  {"SRC001", "SRC002"}),
    ("chữ Phật và chữ Vạn khắc nổi trên chân đèn",   {"SRC002"}),
    ("hoa cúc 12 cánh nhọn để mộc của Đỗ Xuân Vy",   {"SRC003"}),
]


LOCATOR_MAX = 200
SENT_SPLIT_RE = __import__("re").compile(
    r"(?<=[.!?…])\s+(?=[A-ZĐÂÊÔƯĂÁÀẢÃẠÍÌỈĨỊÚÙỦŨỤÉÈẺẼẸÓÒỎÕỌÝỲỶỸỴ0-9])")


def nfc(s: str) -> str:
    return ud.normalize("NFC", s)


def squash(s: str) -> str:
    return " ".join(s.split())


def _words(s: str) -> set[str]:
    return {w for w in squash(s.lower()).split() if len(w) >= 3}


def best_locator(chunk_text: str, query: str, fallback: str) -> str:
    """Chọn câu trong chunk khớp truy vấn nhất, làm định vị trích dẫn.

    rag/chunk.py chốt sẵn một locator lúc cắt chunk, nhưng nó chỉ là "câu đầu
    tiên có độ dài vừa phải" — thường không phải câu đã khiến chunk được truy
    xuất. Ví dụ truy vấn về hoa sen trả về chunk đúng, nhưng locator lại là câu
    'Do vậy mà đề tài trang trí... trở nên sinh động', vô nghĩa với người đọc
    Cultural Passport.

    Chọn lại theo truy vấn nên trích dẫn hiển thị đúng câu đã khớp. Kết quả luôn
    là chuỗi con của chunk, tức vẫn nguyên văn so với tài liệu nguồn.
    """
    qw = _words(query)
    if not qw:
        return fallback
    best, best_score = None, 0
    for sent in SENT_SPLIT_RE.split(chunk_text):
        sent = squash(sent)
        if len(sent) < 30:
            continue
        score = len(qw & _words(sent))
        if score > best_score:
            best, best_score = sent, score
    if best is None:
        return fallback
    if len(best) <= LOCATOR_MAX:
        return best
    # Câu quá dài: lấy cửa sổ quanh từ khoá khớp đầu tiên, cắt theo ranh giới từ.
    low = best.lower()
    pos = min((low.find(w) for w in qw if low.find(w) >= 0), default=0)
    start = max(0, pos - LOCATOR_MAX // 3)
    window = best[start:start + LOCATOR_MAX]
    if start > 0:
        window = window[window.find(" ") + 1:]
    if start + LOCATOR_MAX < len(best):
        window = window[:window.rfind(" ")]
    return window


class Retriever:
    """Evidence retrieval bằng vector search thật (spec mục 8.1).

    Metadata cấp tài liệu KHÔNG nằm trong chunk mà được nối vào lúc truy xuất
    từ data/sources.json (spec mục 19.1) — sửa tên tác giả không phải nhúng lại.
    """

    def __init__(self) -> None:
        self.chunks = [json.loads(l) for l in
                       CHUNKS_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.vectors = np.load(VECTORS_FILE)
        self.meta = json.loads(META_FILE.read_text(encoding="utf-8"))
        self.sources = json.loads(SOURCES_JSON.read_text(encoding="utf-8"))["sources"]
        self._model = None
        self._assert_aligned()

    def _assert_aligned(self) -> None:
        """Hàng thứ i của ma trận phải ứng với chunk thứ i. Lệch một hàng là
        mọi trích dẫn gán sai nguồn mà không có dấu hiệu nào lộ ra."""
        if len(self.chunks) != self.vectors.shape[0]:
            raise ValueError(f"{len(self.chunks)} chunk nhung {self.vectors.shape[0]} vector")
        ids_meta = self.meta.get("chunk_ids", [])
        ids_file = [c["chunk_id"] for c in self.chunks]
        if ids_meta != ids_file:
            raise ValueError("Thu tu chunk_id trong embeddings_meta.json khong khop chunks.jsonl. "
                             "Chay lai `python -m rag.embed`.")

    @property
    def model(self):
        """Nạp model lười — chỉ khi thật sự cần nhúng truy vấn."""
        if self._model is None:
            if not os.environ.get("HF_HOME"):
                for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith("HF_HOME="):
                        os.environ["HF_HOME"] = line.split("=", 1)[1].strip().strip('"')
            from sentence_transformers import SentenceTransformer   # noqa: PLC0415
            self._model = SentenceTransformer(self.meta["model_id"], device="cpu")
        return self._model

    def search(self, query: str, k: int = TOP_K,
               min_sim: float = MIN_SIMILARITY) -> list[dict]:
        qv = self.model.encode([query], normalize_embeddings=True,
                               show_progress_bar=False)
        qv = np.asarray(qv, dtype=np.float32)[0]
        # Vector đã chuẩn hoá L2 nên tích vô hướng chính là cosine.
        sims = self.vectors @ qv
        order = np.argsort(-sims)[:k]
        return [{**self.chunks[int(i)], "similarity": round(float(sims[i]), 4)}
                for i in order if sims[i] >= min_sim]

    def build_evidence(self, query: str, k: int = TOP_K,
                       min_sim: float = MIN_SIMILARITY) -> dict:
        """Trả Evidence CÓ CẤU TRÚC theo spec mục 8.3 — không phải văn bản tự do."""
        hits = self.search(query, k, min_sim)

        context, used = [], 0
        for h in hits:
            if used + len(h["text"]) > MAX_CONTEXT_CHARS:
                break
            context.append(h["text"])
            used += len(h["text"])

        # Gom theo tài liệu, giữ chunk điểm cao nhất của mỗi nguồn làm đại diện.
        seen: dict[str, dict] = {}
        for h in hits:
            sid = h["src_id"]
            if sid in seen:
                continue
            m = self.sources.get(sid, {})
            seen[sid] = {
                "document": sid,
                "title": m.get("title"),
                "author": m.get("author"),
                "year": m.get("year"),
                "url": m.get("url"),
                "doi": m.get("doi"),
                "locator": best_locator(h["text"], query, h["locator"]),
                "section": h.get("section"),
                # page CHỈ điền khi nguồn có phân trang chính danh (spec mục 8.3.1).
                "page": h.get("page") if m.get("has_canonical_pages") else None,
                "similarity": h["similarity"],
                # Cho tầng trên biết nguồn này có được dùng làm căn cứ rule hay không.
                "rule_basis": m.get("rule_basis"),
            }
        return {"query": query, "context": " ".join(context), "sources": list(seen.values())}


def format_evidence(ev: dict) -> str:
    out = [f'Truy van : "{ev["query"]}"',
           f'Context  : {len(ev["context"])} ky tu tu {len(ev["sources"])} nguon', ""]
    for s in ev["sources"]:
        who = " · ".join(str(x) for x in (s["author"], s["year"]) if x)
        out.append(f'  [{s["similarity"]:.3f}] {s["document"]}' + (f' — {who}' if who else ""))
        out.append(f'          "{s["locator"][:96]}"')
        extra = [f'section={s["section"]}' if s["section"] else "",
                 f'page={s["page"]}' if s["page"] is not None else "",
                 f'rule_basis={s["rule_basis"]}' if s["rule_basis"] != "allowed" else ""]
        extra = [e for e in extra if e]
        if extra:
            out.append(f'          {" | ".join(extra)}')
    return "\n".join(out)


def check_alignment(r: Retriever) -> int:
    print("\n[KIEM 1] Vector khop chunk")
    print(f"  {len(r.chunks)} chunk | {r.vectors.shape[0]} x {r.vectors.shape[1]} vector | "
          f"thu tu chunk_id khop")
    return 0


def check_locators(r: Retriever) -> int:
    """Ràng buộc bắt buộc spec mục 8.3.1: locator phải xuất hiện nguyên văn
    trong tài liệu nguồn. Kiểm lại tại tầng truy xuất, không tin bước trước."""
    print("\n[KIEM 2] locator nguyen van trong tai lieu nguon")
    corpus = {}
    for f in sorted(CORPUS_DIR.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        corpus[d["src_id"]] = squash(nfc(" ".join(p["text"] for p in d["paragraphs"])))
    bad = [c["chunk_id"] for c in r.chunks
           if squash(nfc(c["locator"])) not in corpus.get(c["src_id"], "")]
    for cid in bad[:3]:
        print(f"  [LOI] chunk {cid}")
    # Kiểm cả locator được CHỌN LẠI lúc truy xuất — đó mới là chuỗi hiển thị
    # trên Cultural Passport, và spec 8.3.1 bắt buộc nó phải nguyên văn.
    n_dyn = 0
    for query, _ in PROBES:
        for s_ in r.build_evidence(query, k=3)["sources"]:
            n_dyn += 1
            if squash(nfc(s_["locator"])) not in corpus.get(s_["document"], ""):
                print(f"  [LOI] locator dong: {s_['locator'][:66]}")
                bad.append(s_["document"])
    print(f"  {len(r.chunks) - len([b for b in bad if '#' in str(b)])}/{len(r.chunks)} "
          f"locator co san | {n_dyn} locator chon luc truy xuat deu hop le")
    return len(bad)


def check_page_rule(r: Retriever) -> int:
    """`page` chỉ được xuất hiện với nguồn has_canonical_pages=true."""
    print("\n[KIEM 3] Truong page dung quy tac spec 8.3.1")
    bad = 0
    for query, _ in PROBES:
        for s in r.build_evidence(query)["sources"]:
            allowed = r.sources.get(s["document"], {}).get("has_canonical_pages", False)
            if s["page"] is not None and not allowed:
                print(f"  [LOI] {s['document']} co page={s['page']} nhung "
                      f"has_canonical_pages=false")
                bad += 1
    if not bad:
        canon = [k for k, m in r.sources.items() if m.get("has_canonical_pages")]
        print(f"  Dung — chi {canon} duoc phep dien page")
    return bad


def check_probes(r: Retriever) -> int:
    """Mốc Go/No-Go Ngày 5: Evidence retrieval phải hoạt động ổn định."""
    print("\n[KIEM 4] Truy xuat ngu nghia (moc Go/No-Go Ngay 5)")
    bad = 0
    for query, expected in PROBES:
        ev = r.build_evidence(query, k=3)
        if not ev["sources"]:
            print(f"  [SAI] \"{query[:46]}\" -> khong nguon nao vuot nguong")
            bad += 1
            continue
        top = ev["sources"][0]["document"]
        ok = top in expected
        bad += 0 if ok else 1
        print(f"  [{'OK ' if ok else 'SAI'}] \"{query[:46]}\"")
        print(f"         top1={top} ({ev['sources'][0]['similarity']:.3f}) | "
              f"mong doi {sorted(expected)}")
    print(f"  {len(PROBES) - bad}/{len(PROBES)} truy van tra ve dung nguon")
    return bad


def check_schema(r: Retriever) -> int:
    """Evidence phải đủ trường theo spec mục 8.3."""
    print("\n[KIEM 5] Evidence du truong theo spec 8.3")
    need = {"document", "title", "author", "year", "url", "doi",
            "locator", "section", "page", "similarity", "rule_basis"}
    ev = r.build_evidence(PROBES[0][0])
    bad = 0
    if not {"query", "context", "sources"} <= set(ev):
        print("  [LOI] thieu khoa cap cao nhat")
        bad += 1
    for s in ev["sources"]:
        missing = need - set(s)
        if missing:
            print(f"  [LOI] {s['document']} thieu {sorted(missing)}")
            bad += 1
    if not bad:
        print(f"  Du {len(need)} truong moi nguon")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?", help="cau truy van; bo trong de chay phep kiem")
    ap.add_argument("-k", type=int, default=TOP_K)
    ap.add_argument("--json", action="store_true", help="in Evidence dang JSON")
    args = ap.parse_args()

    for f in (CHUNKS_FILE, VECTORS_FILE, META_FILE):
        if not f.exists():
            print(f"Khong thay {f}. Chay `python -m rag.chunk` roi `python -m rag.embed`.")
            return 1

    r = Retriever()

    if args.query:
        ev = r.build_evidence(args.query, k=args.k)
        print(json.dumps(ev, ensure_ascii=False, indent=2) if args.json
              else format_evidence(ev))
        return 0

    print(f"Model: {r.meta['model_id']} | {r.meta['n_vectors']} vector x {r.meta['dim']} chieu")
    errs = (check_alignment(r) + check_locators(r) + check_page_rule(r)
            + check_probes(r) + check_schema(r))
    print(f"\n{'=' * 60}\nTONG LOI: {errs}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
