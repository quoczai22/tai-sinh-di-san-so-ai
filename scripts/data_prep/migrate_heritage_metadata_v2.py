# -*- coding: utf-8 -*-
"""Chuyển data/heritage/metadata.json sang schema 2.0 (Provenance & Copyright).

Chạy MỘT LẦN (đã chạy ngày 2026-11-18, kết quả đã commit). Giữ lại để minh
chứng cách dữ liệu được chuyển đổi — không có số liệu nào được điền tay mà
không ghi rõ nguồn gốc của nó.

Việc script làm:
  1. Gộp URL nguồn từ data/metadata.json (tệp không được mã nào đọc) vào tệp chuẩn.
  2. Băm SHA-256 + đo kích thước ảnh để làm "phiên bản dữ liệu gốc".
  3. Ghi trạng thái quyền, cách ghi công, cờ rà soát cho từng hiện vật.
  4. Đánh dấu 3 hiện vật ngừng sử dụng (retired) theo kết quả tiêu chí tuyển ảnh v2.
  5. Lưu trữ (KHÔNG xoá) data/metadata.json và data/heritage/items.json.

    python scripts/data_prep/migrate_heritage_metadata_v2.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from provenance.hashing import sha256_file  # noqa: E402

TODAY = "2026-11-18"
FIRST_SEEN = "2026-09-06"   # ngày sớm nhất ảnh xuất hiện trong evaluation/variants.csv

# Đo bằng cụm 8 từ liên tiếp giữa team_description và văn bản nhóm chép kèm từng
# URL trong tệp Drive "Nguồn ảnh.docx" (đo ngày 2026-11-18).
DESC_OVERLAP = {
    "BT_Hac_XP": "116/121", "HSBT_XP-300x300": "121/121", "BHV_UU_XP1-600x600": "114/114",
    "MB_2C_XP_31": "86/129", "BT010_2": "169/169",
    "binh-hoa-su-trang-ap-noi-hoa-sen-dat-vang-24k-bat-trang-cao-cap-anh-dai-dien": "163/163",
}

RETIRE = {
    "HSBT_XP-300x300": "C1 không đạt: ảnh gốc 300×300 px, vùng hiện vật 138×242 px phải phóng to ×1,98 khi letterbox 512.",
    "BT010_2": "C1 không đạt: ảnh gốc 324×617 px (cạnh ngắn < 512), JPEG 32 KB nén nặng.",
    "binh-hoa-su-trang-ap-noi-hoa-sen-dat-vang-24k-bat-trang-cao-cap-anh-dai-dien":
        "C4: sản phẩm thương mại đương đại của xưởng (rủi ro bản quyền tác giả cao hơn hiện vật cổ); "
        "C2 thấp nhất bộ (72% mốc); hoa văn V1/V2 ra mảnh ghép của thân bình.",
}

VISUAL_SUMMARY = {
    "BT_Hac_XP": "Bình dáng tỏi, men lam trên nền trắng: chim cổ dài giữa sen và lá, điểm chỉ vàng.",
    "BHV_UU_XP1-600x600": "Bình men nền vàng, men rạn: đôi chim công, hoa mẫu đơn hồng, sóng nước xanh ở chân.",
    "MB_2C_XP_31": "Bình nền vàng men rạn: thuyền buồm lớn trên sóng nước, viền hoa ở vai và chân.",
    "HSBT_XP-300x300": "Bình trắng vẽ sen mực đen kiểu thuỷ mặc.",
    "BT010_2": "Bình hồ lô men lam: hoa dây (cúc) phủ kín thân.",
    "binh-hoa-su-trang-ap-noi-hoa-sen-dat-vang-24k-bat-trang-cao-cap-anh-dai-dien":
        "Bình sứ trắng hình trụ, hoa sen đắp nổi viền vàng.",
}

FLAGS = {
    "BT_Hac_XP": [{"field": "prompt_terms.name_en",
                   "issue": "Mô tả cho mô hình ghi 'peacock' (chim công); đường dẫn nguồn ghi 'bach-hac' (bạch hạc) và ảnh cho thấy chim cổ dài, mỏ dài.",
                   "action": "Chuyên gia/nhóm xác nhận loài chim; nếu là hạc, tạo prompt_terms phiên bản mới và chạy lại thí nghiệm (không sửa đè bản cũ).",
                   "status": "open", "opened_on": TODAY}],
}


def slug_title(url: str) -> str:
    slug = urlparse(url).path.rstrip("/").split("/")[-1].replace(".html", "")
    return slug.replace("-", " ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    meta_path = ROOT / "data" / "heritage" / "metadata.json"
    old = json.loads(meta_path.read_text(encoding="utf-8"))
    if old.get("_meta", {}).get("schema_version", "").startswith("2."):
        print("metadata.json đã ở schema 2.x — bỏ qua.")
        return 0
    urls_path = ROOT / "data" / "metadata.json"
    urls = json.loads(urls_path.read_text(encoding="utf-8"))["items"]

    items = {}
    for index, (hid, it) in enumerate(old["items"].items(), start=1):
        img = ROOT / it["image_path"]
        with Image.open(img) as im:
            size, mode = list(im.size), im.mode
        url = (urls.get(hid, {}).get("image_source_url") or "").strip() or None
        domain = urlparse(url).netloc if url else None
        status = "retired" if hid in RETIRE else "active"
        items[hid] = {
            **{k: it[k] for k in ("heritage_id", "name", "image_path", "license", "license_note",
                                  "conditioning_mode")},
            "code": f"HV{index:02d}",
            "status": status,
            **({"retired_on": TODAY, "retired_reason": RETIRE[hid]} if status == "retired" else {}),
            "visual_summary": VISUAL_SUMMARY[hid],
            "visual_summary_origin": "Nhóm biên soạn từ quan sát ảnh, Claude hỗ trợ soạn câu chữ (bản nháp — cần nhóm rà soát).",
            "team_description": it.get("team_description", ""),
            "provenance": {
                "source_title": slug_title(url) if url else None,
                "source_title_note": "Suy từ đường dẫn trang sản phẩm (chưa đối chiếu tiêu đề hiển thị trên trang).",
                "source_url": url,
                "source_type": "commercial_product_page",
                "holder": f"{domain} (website bán gốm — pháp nhân chưa xác minh)" if domain else None,
                "holder_type": "commercial_seller",
                "author": None,
                "author_note": "Trang bán hàng không ghi người chụp; chưa liên hệ đơn vị đăng ảnh.",
                "rights_status": "unverified",
                "license": None,
                "attribution": (f"Ảnh: {domain} ({url}). Quyền sử dụng chưa được xác minh; chỉ dùng phi thương mại "
                                "cho nghiên cứu và trình diễn trong cuộc thi.") if url else None,
                "collected_on": None,
                "collected_before": FIRST_SEEN,
                "collected_note": "Không có nhật ký ngày tải ảnh; ngày sớm nhất ảnh được dùng là 2026-09-06 (evaluation/variants.csv).",
                "data_version": f"orig-sha256:{sha256_file(img)[:12]}",
                "image_sha256": sha256_file(img),
                "image_bytes": img.stat().st_size,
                "image_size": size,
                "image_mode": mode,
                "derived_from": None,
                "dating": None,
                "dating_source": None,
                "dating_note": "Trang nguồn là trang bán hàng, không công bố niên đại — không suy đoán.",
                "description_origin": "source_page_text",
                "description_note": (f"team_description trùng {DESC_OVERLAP[hid]} cụm 8 từ với văn bản nhóm chép kèm URL "
                                     "trong tệp 'Nguồn ảnh.docx' → coi là trích từ trang nguồn; chỉ hiển thị kèm ghi nguồn."),
                "permission_request": {"status": "not_sent", "sent_on": None, "channel": None, "response": None},
                "review_flags": FLAGS.get(hid, []),
            },
        }

    new = {
        "_meta": {
            "schema_version": "2.0",
            "data_version": TODAY,
            "purpose": "Heritage Registry — nguồn dữ liệu DUY NHẤT cho hiện vật (tên, ảnh, nguồn, quyền, ghi công, phiên bản).",
            "status_enum": {"active": "đang dùng", "retired": "ngừng dùng, giữ để lưu minh chứng", "pending_ingest": "chờ tiếp nhận"},
            "rights_status_enum": ["unverified", "permission_requested", "permission_granted", "open_license",
                                   "public_domain", "own_work", "permission_denied"],
            "note": "team_description của 6 hiện vật cũ là văn bản trích từ trang nguồn, KHÔNG phải mô tả học thuật; UI phải hiển thị kèm ghi nguồn.",
            "history": [
                {"date": "2026-09-06", "event": "Schema 1.0: 6 hiện vật, license 'unverified', URL nằm ở tệp phụ data/metadata.json."},
                {"date": TODAY, "event": "Schema 2.0: gộp URL, thêm khối provenance, SHA-256, retire 3 hiện vật theo tiêu chí tuyển ảnh v2."},
            ],
        },
        "items": items,
    }
    if args.dry_run:
        print(json.dumps(new, ensure_ascii=False, indent=2)[:3000])
        return 0
    archive = ROOT / "data" / "archive" / "2026-09_schema1"
    archive.mkdir(parents=True, exist_ok=True)
    shutil.copy2(meta_path, archive / "heritage_metadata_v1.json")
    for src in (urls_path, ROOT / "data" / "heritage" / "items.json"):
        if src.exists():
            shutil.move(str(src), archive / src.name.replace(".json", "_v1.json"))
    meta_path.write_text(json.dumps(new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Đã ghi {meta_path.relative_to(ROOT)}; bản cũ lưu ở {archive.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
