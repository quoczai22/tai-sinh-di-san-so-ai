# -*- coding: utf-8 -*-
"""Dùng LLM có thị giác viết mô tả hoa văn tiếng Anh cho từng ảnh gốm.

CHẠY OFFLINE MỘT LẦN, kết quả ghi vào data/prompt_terms.json rồi commit. Pipeline
sinh ảnh KHÔNG gọi LLM — nó đọc file. Nhờ vậy giữ nguyên tính tất định: cùng một
hiện vật + seed + mức Intensity luôn ra cùng một ảnh (v6 mục 9, Test 5).

Hai ràng buộc bắt buộc, kiểm tự động và bắt LLM viết lại nếu vi phạm:

  1. <= 21 token, đo bằng CHÍNH tokenizer của SD1.5. CLIP cắt ở 77 token mà
     không báo lỗi, nên phải chừa chỗ cho phần còn lại của template.

  2. KHÔNG được nhắc hình dạng vật chứa (vase, jar, pot, bottle...). Đây không
     phải khắt khe vô cớ: giai đoạn 1 sinh HOA VĂN PHẲNG, và chỉ cần chữ "vase"
     lọt vào prompt là ControlNet kéo đầu ra về hình cái bình — đã đo, đầu ra
     thành ảnh chụp bình gốm trên bàn gỗ thay vì hoa văn.

Chạy:
    python scripts/07_describe_heritage.py --dry-run     # xem se lam gi (khong goi API)
    python scripts/07_describe_heritage.py               # goi LLM, chi ghi muc con thieu
    python scripts/07_describe_heritage.py --force       # viet lai tat ca
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from datetime import date
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if getattr(_s, "encoding", "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

HERITAGE_DIR = ROOT / "data" / "heritage"
TERMS_FILE = ROOT / "data" / "prompt_terms.json"
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")

MAX_TOKENS = 21
MAX_RETRY = 3

# Google go model cu kha thuong xuyen — gemini-2.0-flash da bi go giua chung.
# Doi bang GEMINI_MODEL trong .env; xem danh sach bang --list-models.
DEFAULT_MODEL = "gemini-3.7-flash"

# Từ chỉ hình dạng vật chứa — lọt vào prompt là hỏng giai đoạn 1.
BANNED = {"vase", "vases", "jar", "jars", "pot", "pots", "bottle", "bottles",
          "vessel", "vessels", "urn", "urns", "bowl", "bowls", "plate", "plates",
          "cup", "cups", "teapot", "censer", "ceramic object", "porcelain object",
          "photograph", "photo", "3d", "render"}

INSTRUCTION = """You are helping build a textile-pattern generator. You will see a photo of a
Vietnamese Bat Trang ceramic object.

Describe ONLY the SURFACE DECORATION — the motifs painted or carved on it.

HARD RULES:
1. NEVER mention the object's shape or type. Do not write vase, jar, pot, bottle,
   vessel, urn, bowl, plate, cup, teapot, censer, or "ceramic object". The output
   is a FLAT REPEATING PATTERN, not a picture of an object.
2. Maximum 12 words for the description.
3. Name the concrete motifs you actually see (e.g. cranes, lotus, peony, dragon,
   chrysanthemum, cloud scrolls, leaf borders) plus the colour scheme.
4. English only.

Return STRICT JSON, nothing else:
{"name_en": "<3-5 words, e.g. 'Bat Trang crane and lotus'>",
 "base_description": "<<=12 words describing motifs and colours>>"}"""


def load_env() -> None:
    f = ROOT / ".env"
    if not f.exists():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def n_tokens(text: str) -> int:
    from generation.prompt_template import n_tokens as nt      # noqa: PLC0415
    return nt(text) - 2                                        # bỏ <bos>/<eos>


def violations(desc: str) -> list[str]:
    low = desc.lower()
    hit = [w for w in BANNED if w in low.split() or w in low]
    if n_tokens(desc) > MAX_TOKENS:
        hit.append(f"{n_tokens(desc)} token > {MAX_TOKENS}")
    return hit


# ── Hai nhà cung cấp, cùng một giao diện ────────────────────────────────────

def _gemini_client():
    """Nạp SDK Gemini. Hỗ trợ cả SDK mới (`google-genai`) lẫn SDK cũ
    (`google-generativeai`) — tuỳ máy đã cài cái nào."""
    key = os.environ["GEMINI_API_KEY"]
    try:
        from google import genai                               # noqa: PLC0415
        return "new", genai.Client(api_key=key)
    except ImportError:
        pass
    try:
        import google.generativeai as genai_old                 # noqa: PLC0415
        genai_old.configure(api_key=key)
        return "old", genai_old
    except ImportError:
        raise SystemExit(
            "Thieu SDK Gemini. Cai bang:\n"
            "  .\\venv\\Scripts\\pip install google-genai") from None


def list_models() -> list[str]:
    """Hỏi thẳng API xem model nào đang dùng được — Google gỡ model cũ khá thường
    xuyên (gemini-2.0-flash đã bị gỡ), nên đoán tên theo trí nhớ là hỏng."""
    kind, client = _gemini_client()
    if kind == "new":
        return [m.name.replace("models/", "") for m in client.models.list()
                if "generateContent" in (getattr(m, "supported_actions", None) or [])]
    return [m.name.replace("models/", "") for m in client.list_models()
            if "generateContent" in getattr(m, "supported_generation_methods", [])]


def find_working_model(skip: set[str] | None = None) -> str | None:
    """Dò model NÀO THẬT SỰ GỌI ĐƯỢC bằng một lời gọi văn bản cực ngắn.

    Chỉ liệt kê danh sách là không đủ: API vẫn trả về những model mà tài khoản
    không dùng được. Quan sát thực tế — `gemini-2.5-flash` có trong danh sách
    nhưng trả 404 "no longer available to new users", còn `gemini-flash-latest`
    trả 503. Phải thử mới biết.
    """
    kind, client = _gemini_client()
    if kind != "new":
        return None
    skip = skip or set()
    cands = [m for m in list_models()
             if "flash" in m and m not in skip
             and not any(x in m for x in ("image", "tts", "lite", "omni", "transcribe"))]
    cands.sort(key=lambda m: "preview" in m)          # bản ổn định trước
    for m in cands:
        try:
            client.models.generate_content(model=m, contents="ok")
            return m
        except Exception:
            continue
    return None


def _model_error(model_id: str, err: Exception) -> SystemExit:
    alt = find_working_model(skip={model_id})
    return SystemExit(
        f"Model {model_id!r} khong dung duoc.\n  {str(err)[:150]}\n\n"
        + (f"Da do va thay {alt!r} goi duoc. Dat vao .env roi chay lai:\n"
           f"  GEMINI_MODEL={alt}"
           if alt else
           "Khong do duoc model nao goi duoc. Xem `--list-models`."))


def call_gemini(img: Path, extra: str) -> str:
    kind, client = _gemini_client()
    model_id = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    mime = mimetypes.guess_type(img.name)[0] or "image/png"
    data = img.read_bytes()
    try:
        if kind == "new":
            from google.genai import types                     # noqa: PLC0415
            r = client.models.generate_content(
                model=model_id,
                contents=[types.Part.from_bytes(data=data, mime_type=mime),
                          INSTRUCTION + extra])
            return r.text
        model = client.GenerativeModel(model_id)
        r = model.generate_content([INSTRUCTION + extra,
                                    {"mime_type": mime, "data": data}])
        return r.text
    except Exception as e:
        if "not found" in str(e).lower() or "404" in str(e) or "NOT_FOUND" in str(e):
            raise _model_error(model_id, e) from None
        raise


def pick_provider() -> tuple[str, callable, str]:
    """CHỈ dùng Gemini. Không đọc OPENAI_API_KEY — máy có thể đang có sẵn key đó
    trong biến môi trường hệ thống, và dự án không được tiêu nhầm vào tài khoản
    khác với chủ ý của người dùng."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit(
            "Chua co GEMINI_API_KEY. Them dong sau vao .env roi chay lai:\n"
            "  GEMINI_API_KEY=...\n"
            f"Tuy chon: GEMINI_MODEL={DEFAULT_MODEL} (mac dinh)")
    return "gemini", call_gemini, os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)


def parse_json(raw: str) -> dict:
    """LLM hay bọc JSON trong ```json ... ``` dù đã bảo đừng."""
    t = raw.strip()
    if t.startswith("```"):
        t = t.split("```")[1]
        t = t[4:] if t.lower().startswith("json") else t
    return json.loads(t.strip())


def describe(img: Path, call) -> dict:
    extra = ""
    for attempt in range(1, MAX_RETRY + 1):
        try:
            d = parse_json(call(img, extra))
            bad = violations(d["base_description"])
            if not bad:
                return d
            print(f"      lan {attempt}: vi pham {bad} — yeu cau viet lai")
            extra = (f"\n\nYour previous answer violated the rules ({', '.join(bad)}). "
                     f"Previous: {d['base_description']!r}. Rewrite it: shorter, and "
                     f"with NO object-shape words at all.")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"      lan {attempt}: khong doc duoc JSON ({e})")
            extra = "\n\nReturn ONLY raw JSON, no markdown fences, no explanation."
    raise RuntimeError(f"{img.name}: LLM khong dat rang buoc sau {MAX_RETRY} lan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="viet lai ca muc da co")
    ap.add_argument("--list-models", action="store_true",
                    help="hoi API xem model nao dang dung duoc")
    args = ap.parse_args()

    load_env()
    if args.list_models:
        for m in list_models():
            print(f"  {m}")
        return 0
    imgs = sorted(f for f in HERITAGE_DIR.glob("*") if f.suffix.lower() in IMG_EXT)
    if not imgs:
        raise SystemExit(f"Khong co anh nao trong {HERITAGE_DIR}")

    data = json.loads(TERMS_FILE.read_text(encoding="utf-8")) if TERMS_FILE.exists() \
        else {"_meta": {}, "terms": {}}
    terms = data.setdefault("terms", {})

    todo = [f for f in imgs
            if args.force or f.stem not in terms
            or terms[f.stem].get("source") != "llm_vision"]
    print(f"{len(imgs)} anh | {len(todo)} can mo ta"
          f"{' (--force: viet lai tat ca)' if args.force else ''}")
    for f in todo:
        print(f"  - {f.name}")

    if args.dry_run:
        print("\n(--dry-run: khong goi API, khong ghi file)")
        return 0
    if not todo:
        print("\nKhong co gi de lam. Dung --force neu muon viet lai.")
        return 0

    name, call, model_id = pick_provider()
    print(f"\nDung {name} / {model_id}\n")

    changed = 0
    for f in todo:
        print(f"  {f.name}")
        try:
            d = describe(f, call)
        except RuntimeError as e:
            print(f"      BO QUA: {e}")
            continue
        old = terms.get(f.stem, {}).get("base_description")
        terms[f.stem] = {
            "name_en": d["name_en"],
            "base_description": d["base_description"],
            "source": "llm_vision", "llm_model": f"{name}/{model_id}",
            "generated_on": date.today().isoformat(), "reviewed_by_human": False,
        }
        changed += 1
        print(f"      name_en : {d['name_en']}")
        print(f"      mo ta   : {d['base_description']}  "
              f"({n_tokens(d['base_description'])} token)")
        if old:
            print(f"      thay cho: {old}")

    data["_meta"].update({
        "status": ("Mo ta do LLM co thi giac sinh, CHUA duoc nguoi ra soat. "
                   "Dat reviewed_by_human=true sau khi kiem tra tung muc."),
        "constraints": f"<= {MAX_TOKENS} token; cam moi tu chi hinh dang vat chua",
        "note": "Khoa la ten file trong data/heritage/ (khong co duoi).",
    })
    TERMS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDa ghi {changed} muc vao {TERMS_FILE.relative_to(ROOT)}")
    print("CAN LAM: doc lai tung mo ta, dung thi dat reviewed_by_human = true.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
