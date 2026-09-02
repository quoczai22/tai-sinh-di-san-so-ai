# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import os
import sys
import time
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
SOURCES_JSON = ROOT / "data" / "sources.json"
VECTORS_FILE = ROOT / "data" / "embeddings.npy"
META_FILE = ROOT / "data" / "embeddings_meta.json"

MODEL_ID = "BAAI/bge-m3"
EXPECTED_DIM = 1024      # phải khớp `vector(1024)` trong db/schema.sql
DEVICE = "cpu"           # spec mục 18 — không tranh VRAM với Stable Diffusion
BATCH_SIZE = 8

NORM_TOLERANCE = 1e-3    # sai số cho phép khi kiểm chuẩn hoá L2

# Truy vấn thử: mỗi câu gắn với một heritage_id trong rule_base, và nguồn kỳ vọng lấy từ
# chính `rule_sources` / `source_note` của mục đó. Dấu "—" nghĩa là câu truy vấn không
# ứng với heritage_id nào — nó vẫn kiểm được corpus vì tài liệu có mô tả nội dung này,
# dù họa tiết không (hoặc không còn) nằm trong dataset. Xem QĐ-03 trong docs/rule_base_sources.md.
PROBES = [
    ("hoa sen tạo hình trên lư hương gốm thờ",        {"SRC001", "SRC006"}, "BT001"),
    ("bát quái tám quẻ trổ thủng trên nắp đỉnh thờ",  {"SRC001"},           "BT006"),
    ("chữ Thọ trong ô hình lá đề",                    {"SRC003"},           "BT005"),
    ("ống nhổ và bình vôi gắn tục ăn trầu",           {"SRC004"},           "BT013"),
    ("men rạn là đặc trưng riêng của lò Bát Tràng",   {"SRC005", "SRC001", "SRC006"}, "—"),
    ("bộ tứ linh long ly quy phượng trên chân đèn",   {"SRC001", "SRC002"}, "—"),
]



def setup_hf_home() -> str | None:
    """Đặt HF_HOME từ .env TRƯỚC khi import thư viện Hugging Face."""
    if os.environ.get("HF_HOME"):
        return os.environ["HF_HOME"]
    env_file = ROOT / ".env"
    if not env_file.exists():
        return None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("HF_HOME=") and not line.startswith("#"):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                os.environ["HF_HOME"] = value
                return value
    return None


def load_model():
    """Import và nạp model. Import bị hoãn tới đây để HF_HOME kịp có hiệu lực."""
    from sentence_transformers import SentenceTransformer   # noqa: PLC0415

    cache = Path(os.environ.get("HF_HOME", "")) / "hub" / f"models--{MODEL_ID.replace('/', '--')}"
    if not cache.exists():
        print(f"  Chua co trong cache — se tai ~2,2 GB tu Hugging Face.")
        print(f"  Dich: {cache.parent}")
    t = time.time()
    model = SentenceTransformer(MODEL_ID, device=DEVICE)
    print(f"  Nap model xong sau {time.time() - t:.1f}s | device={DEVICE}")
    return model


def load_chunks() -> list[dict]:
    if not CHUNKS_FILE.exists():
        raise FileNotFoundError(
            f"Khong thay {CHUNKS_FILE}. Chay `python -m rag.chunk` truoc.")
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]



# Phép kiểm nghiệm thu

def check_shape(vectors: np.ndarray, n_chunks: int) -> int:
    print("\n[KIEM 1] Hinh dang ma tran vector")
    bad = 0
    if vectors.shape[1] != EXPECTED_DIM:
        print(f"  [LOI] Chieu = {vectors.shape[1]}, mong doi {EXPECTED_DIM}. "
              f"Con so nay phai khop `vector(1024)` trong db/schema.sql.")
        bad += 1
    if vectors.shape[0] != n_chunks:
        print(f"  [LOI] {vectors.shape[0]} vector nhung co {n_chunks} chunk")
        bad += 1
    if vectors.dtype != np.float32:
        print(f"  [LOI] dtype = {vectors.dtype}, mong doi float32")
        bad += 1
    if not bad:
        print(f"  {vectors.shape[0]} x {vectors.shape[1]} float32 — dung nhu mong doi")
    return bad


def check_numeric(vectors: np.ndarray) -> int:
    print("\n[KIEM 2] Gia tri hop le va da chuan hoa L2")
    bad = 0
    n_nan = int(np.isnan(vectors).sum())
    n_inf = int(np.isinf(vectors).sum())
    if n_nan or n_inf:
        print(f"  [LOI] {n_nan} gia tri NaN, {n_inf} gia tri Inf")
        bad += 1
    norms = np.linalg.norm(vectors, axis=1)
    off = np.abs(norms - 1.0) > NORM_TOLERANCE
    if off.any():
        print(f"  [LOI] {int(off.sum())}/{len(norms)} vector chua chuan hoa "
              f"(min {norms.min():.4f}, max {norms.max():.4f}). "
              f"Tich vo huong se KHONG bang cosine.")
        bad += 1
    if not bad:
        print(f"  Khong NaN/Inf | chuan L2 trong khoang "
              f"[{norms.min():.5f}, {norms.max():.5f}]")
    return bad


def check_retrieval(model, vectors: np.ndarray, chunks: list[dict]) -> int:
    """Bài kiểm chất lượng truy xuất — quan trọng nhất trong nhóm này.

    Ba phép kiểm trên chỉ xác nhận ma trận đúng hình dạng. Phép này xác nhận
    embedding thực sự nắm được ngữ nghĩa tiếng Việt trên corpus của dự án.
    """
    print("\n[KIEM 3] Truy xuat ngu nghia tren truy van thu")
    q_vecs = model.encode([p[0] for p in PROBES], normalize_embeddings=True,
                          batch_size=BATCH_SIZE, show_progress_bar=False)
    q_vecs = np.asarray(q_vecs, dtype=np.float32)
    bad = 0
    for (query, expected, hid), qv in zip(PROBES, q_vecs):
        sims = vectors @ qv
        top = np.argsort(-sims)[:3]
        got = chunks[int(top[0])]["src_id"]
        top3 = {chunks[int(i)]["src_id"] for i in top}
        ok = got in expected
        if not ok:
            bad += 1
        mark = "OK " if ok else "SAI"
        print(f"  [{mark}] {hid:6} \"{query[:44]}\"")
        print(f"         top1={got} (sim {sims[top[0]]:.3f}) | top3={sorted(top3)} "
              f"| mong doi {sorted(expected)}")
        if not ok:
            print(f"         chunk: {chunks[int(top[0])]['locator'][:78]}")
    print(f"  {len(PROBES) - bad}/{len(PROBES)} truy van tra ve dung nguon")
    return bad


def check_deterministic(model) -> int:
    print("\n[KIEM 4] Tai lap — nhung cung mot cau hai lan")
    s = "Hoa sen trên gốm thờ Bát Tràng thế kỷ 18"
    a = model.encode([s], normalize_embeddings=True, show_progress_bar=False)
    b = model.encode([s], normalize_embeddings=True, show_progress_bar=False)
    delta = float(np.abs(np.asarray(a) - np.asarray(b)).max())
    if delta > 1e-5:
        print(f"  [LOI] Sai lech toi da {delta:.2e} — khong tai lap duoc")
        return 1
    print(f"  Sai lech toi da {delta:.2e} — tai lap duoc")
    return 0



def probe_only(model, vectors: np.ndarray, chunks: list[dict]) -> int:
    return check_retrieval(model, vectors, chunks)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--probe", action="store_true",
                    help="chi chay truy van thu tren vector da co")
    args = ap.parse_args()

    hf_home = setup_hf_home()
    print(f"HF_HOME: {hf_home or '(khong dat — se dung mac dinh cua he dieu hanh)'}")

    chunks = load_chunks()
    print(f"Chunk: {len(chunks)} tu {CHUNKS_FILE.relative_to(ROOT)}\n[MODEL]")
    model = load_model()

    if args.probe:
        if not VECTORS_FILE.exists():
            print(f"Khong thay {VECTORS_FILE}. Chay `python -m rag.embed` truoc.")
            return 1
        vectors = np.load(VECTORS_FILE)
        return 1 if probe_only(model, vectors, chunks) else 0

    print("\n[NHUNG]")
    texts = [c["text"] for c in chunks]
    t = time.time()
    vectors = model.encode(texts, batch_size=BATCH_SIZE,
                           normalize_embeddings=True, show_progress_bar=True)
    vectors = np.asarray(vectors, dtype=np.float32)
    elapsed = time.time() - t
    print(f"  {len(texts)} chunk trong {elapsed:.1f}s "
          f"({len(texts) / max(elapsed, 1e-9):.1f} chunk/giay)")

    np.save(VECTORS_FILE, vectors)
    meta = {
        "model_id": MODEL_ID,
        "dim": int(vectors.shape[1]),
        "n_vectors": int(vectors.shape[0]),
        "dtype": str(vectors.dtype),
        "normalized": True,
        "device": DEVICE,
        "batch_size": BATCH_SIZE,
        "source_file": CHUNKS_FILE.name,
        "chunk_ids": [c["chunk_id"] for c in chunks],
        "note": ("Vector da chuan hoa L2 nen tich vo huong chinh la cosine. "
                 "Thu tu hang KHOP voi thu tu dong trong chunks.jsonl va voi "
                 "danh sach chunk_ids o day."),
    }
    META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    size_mb = VECTORS_FILE.stat().st_size / 1024 / 1024
    print(f"  Da ghi {VECTORS_FILE.relative_to(ROOT)} ({size_mb:.2f} MB) "
          f"va {META_FILE.relative_to(ROOT)}")

    if args.no_verify:
        print("\n(bo qua phep kiem)")
        return 0

    errs = (check_shape(vectors, len(chunks))
            + check_numeric(vectors)
            + check_retrieval(model, vectors, chunks)
            + check_deterministic(model))
    print(f"\n{'=' * 60}\nTONG LOI: {errs}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
