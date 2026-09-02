# -*- coding: utf-8 -*-
"""
scripts/06_push_to_supabase.py

Nạp toàn bộ artifact của pipeline RAG lên Supabase để DevOps kiểm tra dữ liệu
đã có trên DB hay chưa.

LƯU Ý: script đọc CỘT THẬT trên Supabase qua OpenAPI của PostgREST, không tin
db/schema.sql trong repo — bản trong repo đã cũ hơn schema đang chạy.

Idempotent: dùng upsert nên chạy lại nhiều lần vẫn ra cùng kết quả.

Chạy:
    python scripts/06_push_to_supabase.py            # nap + kiem tra
    python scripts/06_push_to_supabase.py --verify   # chi kiem tra, khong ghi
    python scripts/06_push_to_supabase.py --schema   # chi in cot that tren DB
    python scripts/06_push_to_supabase.py --prune    # xoa dong DB khong con trong file
    python scripts/06_push_to_supabase.py --clear    # xoa sach du lieu da nap
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

for _s in (sys.stdout, sys.stderr):
    if getattr(_s, "encoding", "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BATCH = 20


def load_env() -> None:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def client():
    load_env()
    from supabase import create_client                      # noqa: PLC0415
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise SystemExit("Thieu SUPABASE_URL hoac SUPABASE_SERVICE_ROLE_KEY trong .env")
    return create_client(url, key)


def live_schema() -> dict[str, set[str]]:
    """Đọc cột thật qua OpenAPI của PostgREST. Chỉ ghi những cột DB thực sự có,
    tránh vỡ khi db/schema.sql trong repo lệch với schema đang chạy."""
    import httpx                                            # noqa: PLC0415
    load_env()
    u = os.environ["SUPABASE_URL"].rstrip("/")
    k = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    r = httpx.get(f"{u}/rest/v1/",
                  headers={"apikey": k, "Authorization": f"Bearer {k}"}, timeout=30)
    r.raise_for_status()
    return {t: set(d.get("properties", {}))
            for t, d in r.json().get("definitions", {}).items()}


def fit(rows: list[dict], cols: set[str]) -> tuple[list[dict], set[str]]:
    """Lọc bỏ khoá không có cột tương ứng, trả về cả danh sách khoá bị bỏ."""
    dropped = {k for row in rows for k in row} - cols
    return [{k: v for k, v in row.items() if k in cols} for row in rows], dropped


def first_quote(text: str) -> str | None:
    """Lấy câu trích nguyên văn đầu tiên trong source_note làm locator.

    source_note đặt mọi trích dẫn trong dấu nháy đơn, và toàn bộ 52 câu đã được
    kiểm chứng khớp nguyên văn tài liệu nguồn — nên dùng trực tiếp làm locator
    theo spec muc 8.3.1.
    """
    m = re.search(r"'([^']{20,})'", text or "")
    return m.group(1) if m else None


def load_local() -> dict:
    sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))["sources"]
    rule_base = json.loads((DATA / "rule_base.json").read_text(encoding="utf-8"))["heritage_items"]
    chunks = [json.loads(l) for l in
              (DATA / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    vectors = np.load(DATA / "embeddings.npy")
    corpus = {}
    for f in sorted((DATA / "corpus").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        corpus[d["src_id"]] = d
    if len(chunks) != vectors.shape[0]:
        raise SystemExit(f"{len(chunks)} chunk nhung {vectors.shape[0]} vector")
    return {"sources": sources, "rule_base": rule_base, "chunks": chunks,
            "vectors": vectors, "corpus": corpus}


def build_rows(L: dict) -> dict[str, list[dict]]:
    src_rows = [{"source_id": sid, **{k: m.get(k) for k in
                 ("title", "author", "year", "published", "publisher", "url", "doi",
                  "pages", "kind", "tier", "has_canonical_pages", "encoding",
                  "notes", "rule_basis")}}
                for sid, m in sorted(L["sources"].items())]

    doc_rows = [{"document_id": sid, "source_id": sid, "title": d.get("title"),
                 "content_path": f"data/documents/{L['sources'][sid]['file']}"}
                for sid, d in sorted(L["corpus"].items())]

    her_rows = [{"heritage_id": it["heritage_id"], "name": it["name"],
                 "origin": it["origin"], "region": it["region"],
                 "cultural_meaning": it["cultural_meaning"],
                 "image_path": None, "license": None}
                for it in L["rule_base"]]

    rule_rows = []
    for it in L["rule_base"]:
        hid, note, loc = it["heritage_id"], it["source_note"], first_quote(it["source_note"])
        for rule_type in ("preserve", "modifiable", "restricted"):
            for cat in it[rule_type]:
                sid = it["rule_sources"].get(cat)
                rule_rows.append({
                    "rule_id": f"{hid}:{cat}", "heritage_id": hid, "category": cat,
                    "rule_type": rule_type, "source_id": sid,
                    # source_note/locator chỉ gắn cho rule CÓ nguồn — với rule
                    # modifiable không nguồn thì để trống, không nhồi cho đủ.
                    "source_note": note if sid else None,
                    "locator": loc if sid else None})

    chunk_rows = [{"chunk_id": ch["chunk_id"], "document_id": ch["src_id"],
                   "src_id": ch["src_id"], "chunk_index": ch["chunk_index"],
                   "chunk_text": ch["text"], "locator": ch["locator"],
                   "section": ch["section"], "page": ch["page"],
                   "embedding": L["vectors"][i].tolist()}
                  for i, ch in enumerate(L["chunks"])]

    return {"sources": src_rows, "documents": doc_rows, "heritage_items": her_rows,
            "rule_entries": rule_rows, "document_chunks": chunk_rows}


def prune(c, rows: dict) -> int:
    """Xoá dòng còn trên DB nhưng không còn trong artifact local.

    Cần thiết vì push() dùng upsert — upsert ghi đè và thêm mới, KHÔNG xoá. Rút một
    heritage khỏi rule_base.json rồi chỉ chạy push thì dòng cũ nằm lại trên DB im lặng.

    Thứ tự bắt buộc: bảng con trước bảng cha, nếu không sẽ vi phạm khoá ngoại.
    """
    print("[DON]")
    order = [("rule_entries", "rule_id"), ("document_chunks", "chunk_id"),
             ("documents", "document_id"), ("heritage_items", "heritage_id"),
             ("sources", "source_id")]
    total = 0
    for table, key in order:
        want = {r[key] for r in rows[table]}
        have = set()
        start = 0
        while True:                       # PostgREST trả tối đa 1000 dòng mỗi lần
            page = c.table(table).select(key).range(start, start + 999).execute().data
            have |= {r[key] for r in page}
            if len(page) < 1000:
                break
            start += 1000
        extra = sorted(have - want)
        if not extra:
            print(f"  {table:17} khong co dong du")
            continue
        for i in range(0, len(extra), BATCH):
            c.table(table).delete().in_(key, extra[i:i + BATCH]).execute()
        total += len(extra)
        shown = ", ".join(extra[:6]) + (" ..." if len(extra) > 6 else "")
        print(f"  {table:17} xoa {len(extra):4} dong: {shown}")
    print(f"  Tong cong xoa {total} dong")
    return total


def push(c, rows: dict, schema: dict) -> dict[str, set[str]]:
    print("[NAP]")
    dropped_all: dict[str, set[str]] = {}
    for table in ("sources", "documents", "heritage_items", "rule_entries", "document_chunks"):
        data, dropped = fit(rows[table], schema.get(table, set()))
        if dropped:
            dropped_all[table] = dropped
        key = {"sources": "source_id", "documents": "document_id",
               "heritage_items": "heritage_id", "rule_entries": "rule_id",
               "document_chunks": "chunk_id"}[table]
        for i in range(0, len(data), BATCH):
            c.table(table).upsert(data[i:i + BATCH], on_conflict=key).execute()
            if table == "document_chunks":
                print(f"\r  {table:17} {min(i + BATCH, len(data)):4}/{len(data)}",
                      end="", flush=True)
        print(f"\r  {table:17} {len(data):4}" + " " * 8)
    return dropped_all


def verify(c, L: dict, rows: dict) -> int:
    print("\n[KIEM TRA]")
    bad = 0

    print("  So dong tren DB:")
    for t in ("sources", "documents", "heritage_items", "rule_entries", "document_chunks"):
        got = c.table(t).select("*", count="exact").limit(1).execute().count
        want = len(rows[t])
        ok = got == want
        bad += 0 if ok else 1
        print(f"    {t:18} {got:4} / {want:4} {'OK' if ok else '<-- LECH'}")

    print("\n  get_rule_base('BT001') so voi rule_base.json:")
    bt1 = next(i for i in L["rule_base"] if i["heritage_id"] == "BT001")
    got = c.rpc("get_rule_base", {"p_heritage_id": "BT001"}).execute().data
    for key in ("preserve", "modifiable", "restricted"):
        same = sorted(got.get(key) or []) == sorted(bt1[key])
        bad += 0 if same else 1
        print(f"    {key:12} {'OK' if same else 'LECH'}  DB={sorted(got.get(key) or [])}")
    ns = got.get("source_notes") or {}
    print(f"    source_notes {'CO' if ns else 'RONG'} ({len(ns)} muc)")

    print("\n  Vector round-trip: SQL tren Supabase vs numpy tai cho")
    sys.path.insert(0, str(ROOT))
    from rag.retrieve import Retriever                        # noqa: PLC0415
    r = Retriever()
    for q in ["chữ Thọ trong ô hình lá đề",
              "ống nhổ và bình vôi gắn tục ăn trầu",
              "bát quái tám quẻ trổ thủng trên nắp đỉnh thờ"]:
        qv = np.asarray(r.model.encode([q], normalize_embeddings=True,
                                       show_progress_bar=False), dtype=np.float32)[0]
        local = r.chunks[int(np.argmax(r.vectors @ qv))]["chunk_id"]
        remote = c.rpc("match_document_chunks",
                       {"query_embedding": qv.tolist(), "match_count": 1}).execute().data
        rid = remote[0]["chunk_id"] if remote else None
        ok = rid == local
        bad += 0 if ok else 1
        print(f"    \"{q[:40]}\"")
        print(f"      numpy={local}  supabase={rid}  {'OK' if ok else '<-- LECH'}")
    return bad


def clear(c) -> None:
    for t in ("document_chunks", "documents", "rule_entries", "heritage_items", "sources"):
        c.table(t).delete().neq("created_at", "1970-01-01").execute()
        print(f"  da xoa {t}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--schema", action="store_true")
    ap.add_argument("--prune", action="store_true",
                    help="xoa dong con tren DB nhung khong con trong file local")
    ap.add_argument("--clear", action="store_true")
    args = ap.parse_args()

    c = client()
    schema = live_schema()

    if args.schema:
        for t in sorted(schema):
            print(f"  {t} ({len(schema[t])}): {', '.join(sorted(schema[t]))}")
        return 0
    if args.clear:
        print("[XOA]")
        clear(c)
        return 0

    L = load_local()
    rows = build_rows(L)
    print(f"Local: {len(L['sources'])} nguon | {len(L['corpus'])} tai lieu | "
          f"{len(L['rule_base'])} heritage | {len(L['chunks'])} chunk | "
          f"vector {L['vectors'].shape}\n")

    dropped = {}
    if not args.verify:
        # Dọn trước rồi mới nạp: nếu nạp trước, dòng dư vẫn đếm vào số dòng lúc kiểm tra.
        prune(c, rows)
        if not args.prune:                    # --prune = chi don, khong nap
            dropped = push(c, rows, schema)
    errs = verify(c, L, rows)

    if dropped:
        print("\n[TRUONG BI BO — khong co cot tuong ung tren DB]")
        for t, cols in dropped.items():
            print(f"  {t}: {', '.join(sorted(cols))}")
    else:
        print("\n[TRUONG BI BO] Khong co — schema tren Supabase chua du moi truong.")

    print(f"\n{'=' * 62}\nTONG LOI: {errs}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
